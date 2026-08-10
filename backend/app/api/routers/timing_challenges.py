from __future__ import annotations

import uuid
from contextlib import closing

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app.adapters.db.mysql.database import SessionLocal, get_db
from app.llm.config import LlmGatewaySettings, get_llm_gateway_settings
from app.timing.agent import TimingAnalysisAgent, TimingAnalysisAgentError
from app.timing.analysis import TimingAnalysisError
from app.timing.cache import TimingChallengeCache, get_redis_client
from app.timing.challenge_repository import (
    TIMING_CHAPTER_KEY,
    StoredTimingChallenge,
    TimingChallengeRepository,
    cache_payload,
    cached_challenge_to_stored,
    public_challenge,
)


router = APIRouter()
SESSION_COOKIE_NAME = "timing_session_id"
DEFAULT_TOPIC = "timing-analysis DAG practice"

# Kept as a compatibility alias for existing tests and callers.
_public_challenge = public_challenge


class GenerateTimingChallengeRequest(BaseModel):
    topic: str = Field(default=DEFAULT_TOPIC, min_length=1, max_length=200)


class ValidateTimingChallengeRequest(BaseModel):
    question_id: str = Field(min_length=1, max_length=64)
    answers: dict[str, float] | None = None
    path: list[str] | None = None
    total_delay: float | None = None


def _cache() -> TimingChallengeCache:
    return TimingChallengeCache(get_redis_client())


def _session_id(request: Request, response: Response) -> str:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id or len(session_id) > 64:
        session_id = uuid.uuid4().hex
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_id,
        max_age=TimingChallengeCache.ASSIGNMENT_TTL_SECONDS,
        httponly=True,
        samesite="lax",
    )
    return session_id


def _load_stored_challenge(
    cache: TimingChallengeCache,
    repository: TimingChallengeRepository,
    challenge_id: str,
) -> StoredTimingChallenge | None:
    cached_payload = cache.get_challenge(challenge_id)
    if cached_payload is not None:
        try:
            return cached_challenge_to_stored(cached_payload)
        except (KeyError, TypeError, ValueError, TimingAnalysisError):
            # Invalid cache entries are replaced from SQLite below.
            pass

    stored = repository.get(challenge_id)
    if stored is not None:
        cache.set_challenge(challenge_id, cache_payload(stored))
    return stored


def _recover_current_from_sqlite(cache: TimingChallengeCache, repository: TimingChallengeRepository) -> str | None:
    current = repository.get_current_record(TIMING_CHAPTER_KEY)
    if current is None:
        return None
    ready_ids = [
        record.challenge_id
        for record in repository.list_records(TIMING_CHAPTER_KEY, include_retired=False)
        if record.challenge_id != current.challenge_id
    ]
    cache.replace_chapter_state(TIMING_CHAPTER_KEY, current.challenge_id, ready_ids)
    return current.challenge_id


async def process_timing_generation_jobs(chapter_key: str, settings: LlmGatewaySettings) -> None:
    """Drain persisted generation jobs under one Redis lock; player requests never await this work."""

    cache = _cache()
    owner_token = uuid.uuid4().hex
    try:
        if not cache.try_acquire_generation_lock(chapter_key, owner_token):
            return
    except RedisError:
        return

    try:
        while True:
            with closing(SessionLocal()) as db:
                repository = TimingChallengeRepository(db)
                job = repository.claim_next_generation_job(chapter_key)
                if job is None:
                    return
                try:
                    generated = await TimingAnalysisAgent(settings).generate(topic=job.topic, model=job.model)
                    stored = repository.save_generated(generated, chapter_key, job.topic)
                    cache.set_challenge(stored.generated.challenge_id, cache_payload(stored))
                    previous_id, current_id = cache.enqueue_and_advance_current(
                        chapter_key,
                        stored.generated.challenge_id,
                    )
                    repository.mark_current(chapter_key, current_id, previous_id)
                    repository.complete_generation_job(job.job_id, stored.generated.challenge_id)
                except (TimingAnalysisAgentError, TimingAnalysisError, RedisError, OSError, ValueError) as error:
                    repository.fail_generation_job(job.job_id, str(error))
                except Exception as error:
                    repository.fail_generation_job(job.job_id, f"Unexpected generation error: {error}")
    finally:
        try:
            cache.release_generation_lock(chapter_key, owner_token)
        except RedisError:
            pass


@router.get("/challenges/current")
async def get_current_timing_challenge(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    settings: LlmGatewaySettings = Depends(get_llm_gateway_settings),
    db: Session = Depends(get_db),
):
    """Return one stable 15-minute assignment and enqueue the next challenge in the background."""

    repository = TimingChallengeRepository(db)
    cache = _cache()
    session_id = _session_id(request, response)
    try:
        assigned_id = cache.get_assignment(session_id, TIMING_CHAPTER_KEY)
        if assigned_id is not None:
            stored = _load_stored_challenge(cache, repository, assigned_id)
            if stored is not None:
                cache.set_assignment(session_id, TIMING_CHAPTER_KEY, assigned_id)
                return public_challenge(stored)

        current_id = cache.get_current_challenge_id(TIMING_CHAPTER_KEY)
        if current_id is None:
            current_id = _recover_current_from_sqlite(cache, repository)
        if current_id is None:
            raise HTTPException(status_code=503, detail="Timing challenge pool is initializing")

        stored = _load_stored_challenge(cache, repository, current_id)
        if stored is None:
            raise HTTPException(status_code=503, detail="Timing challenge cache recovery failed")

        cache.set_assignment(session_id, TIMING_CHAPTER_KEY, current_id)
        job_id = repository.enqueue_generation_job(TIMING_CHAPTER_KEY, DEFAULT_TOPIC, settings.default_model)
        background_tasks.add_task(process_timing_generation_jobs, TIMING_CHAPTER_KEY, settings)
        payload = public_challenge(stored)
        payload["generation_job_id"] = job_id
        return payload
    except RedisError as error:
        raise HTTPException(status_code=503, detail="Timing challenge cache is unavailable") from error


@router.post("/challenges/generate", status_code=status.HTTP_202_ACCEPTED)
async def enqueue_timing_challenge_generation(
    request: GenerateTimingChallengeRequest,
    background_tasks: BackgroundTasks,
    settings: LlmGatewaySettings = Depends(get_llm_gateway_settings),
    db: Session = Depends(get_db),
):
    """Queue generation for administrative callers without holding the HTTP request open."""

    job_id = TimingChallengeRepository(db).enqueue_generation_job(
        TIMING_CHAPTER_KEY,
        request.topic,
        settings.default_model,
    )
    background_tasks.add_task(process_timing_generation_jobs, TIMING_CHAPTER_KEY, settings)
    return {"job_id": job_id, "status": "queued"}


@router.get("/challenges/{challenge_id}")
def get_timing_challenge(challenge_id: str, db: Session = Depends(get_db)):
    try:
        stored = _load_stored_challenge(_cache(), TimingChallengeRepository(db), challenge_id)
    except RedisError as error:
        raise HTTPException(status_code=503, detail="Timing challenge cache is unavailable") from error
    if stored is None:
        raise HTTPException(status_code=404, detail="Timing challenge not found")
    return public_challenge(stored)


@router.post("/challenges/{challenge_id}/validate")
def validate_timing_challenge(
    challenge_id: str,
    payload: ValidateTimingChallengeRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    repository = TimingChallengeRepository(db)
    try:
        stored = _load_stored_challenge(_cache(), repository, challenge_id)
    except RedisError as error:
        raise HTTPException(status_code=503, detail="Timing challenge cache is unavailable") from error
    if stored is None:
        raise HTTPException(status_code=404, detail="Timing challenge not found")

    question = next((item for item in stored.generated.questions if item["id"] == payload.question_id), None)
    if question is None:
        raise HTTPException(status_code=400, detail="question_id does not belong to this challenge")

    if question["type"] == "path_delay":
        if payload.total_delay is None:
            raise HTTPException(status_code=400, detail="total_delay is required for a path_delay question")
        try:
            expected_delay = stored.analysis.path_delay(question["path"])
        except TimingAnalysisError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        result = {
            "correct": abs(payload.total_delay - expected_delay) <= 1e-6,
            "question_type": question["type"],
        }
    elif question["type"] == "shortest_path":
        if payload.path is None:
            raise HTTPException(status_code=400, detail="path is required for a shortest_path question")
        try:
            expected_path = stored.analysis.shortest_path(question["source_node_id"], question["target_node_id"])
        except TimingAnalysisError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        result = {"correct": payload.path == expected_path, "question_type": question["type"]}
    else:
        if payload.answers is None:
            raise HTTPException(status_code=400, detail="answers is required for a calculation question")
        metric = {
            "arrival_time": stored.analysis.arrival,
            "required_time": stored.analysis.required,
            "slack": stored.analysis.slack,
        }[question["type"]]
        results = []
        for node_id in question["target_node_ids"]:
            if node_id not in payload.answers:
                results.append({"node_id": node_id, "correct": False, "reason": "missing"})
                continue
            results.append({"node_id": node_id, "correct": abs(payload.answers[node_id] - metric[node_id]) <= 1e-6})
        result = {
            "correct": all(item["correct"] for item in results),
            "question_type": question["type"],
            "results": results,
        }

    player_id = _session_id(request, response)
    repository.record_attempt(
        player_id=player_id,
        challenge_id=challenge_id,
        question_id=payload.question_id,
        answer_payload=payload.model_dump(exclude_none=True),
        result_payload=result,
    )
    return result
