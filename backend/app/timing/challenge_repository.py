from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.adapters.db.mysql.database import SessionLocal
from app.adapters.db.mysql.models import TimingChallenge, TimingChallengeAttempt, TimingGenerationJob
from app.timing.agent import GeneratedTimingChallenge, TimingAnalysisAgent, TimingAnalysisAgentError
from app.timing.analysis import TimingAnalysisEngine, TimingAnalysisError, TimingAnalysisResult
from app.timing.dag_text import TimingDagParseError, parse_timing_dag_text
from app.timing.presentation import build_timing_graph_view
from app.timing.cache import TimingChallengeCache, get_redis_client


TIMING_CHAPTER_KEY = "chapter-5"
INITIAL_DAG_TEXT = """START-A
A-B
A-C
A-D
B-E
B-F
C-E
D-F
E-G
F-G
G-H
G-I
G-J
H-K
I-K
J-L
K-M
L-M
H-M
M-N
N-END
A:2
B:3
C:4
D:2
E:3
F:4
G:2
H:3
I:4
J:2
K:3
L:4
M:2
N:3
"""


@dataclass(frozen=True)
class StoredTimingChallenge:
    generated: GeneratedTimingChallenge
    analysis: TimingAnalysisResult


def public_challenge(challenge: StoredTimingChallenge) -> dict[str, Any]:
    generated = challenge.generated
    return {
        "challenge_id": generated.challenge_id,
        "model": generated.model,
        "dag_file": generated.dag_file.name,
        "dag": build_timing_graph_view(generated.dag),
        "questions": generated.questions,
    }


def cache_payload(challenge: StoredTimingChallenge) -> dict[str, Any]:
    generated = challenge.generated
    return {
        "challenge_id": generated.challenge_id,
        "model": generated.model,
        "dag_file": generated.dag_file.name,
        "dag_text": generated.dag_file.read_text(encoding="utf-8") if generated.dag_file.exists() else _dag_to_text(generated),
        "clock_period": generated.dag.clock_period,
        "questions": generated.questions,
    }


def cached_challenge_to_stored(payload: dict[str, Any]) -> StoredTimingChallenge:
    clock_period = payload.get("clock_period")
    dag = parse_timing_dag_text(
        payload["dag_text"],
        clock_period=float(clock_period) if clock_period is not None else None,
    )
    generated = GeneratedTimingChallenge(
        challenge_id=payload["challenge_id"],
        dag=dag,
        dag_file=Path(payload["dag_file"]),
        questions=payload["questions"],
        model=payload["model"],
    )
    return StoredTimingChallenge(generated=generated, analysis=TimingAnalysisEngine().analyze(dag))


class TimingChallengeRepository:
    def __init__(self, db: Session, storage_dir: Path | None = None):
        self.db = db
        self.storage_dir = storage_dir or Path(__file__).resolve().parents[2] / "generated_timing_dags"

    def get(self, challenge_id: str) -> StoredTimingChallenge | None:
        record = self.db.query(TimingChallenge).filter(TimingChallenge.challenge_id == challenge_id).first()
        return self._to_stored(record) if record else None

    def list_records(self, chapter_key: str, *, include_retired: bool = True) -> list[TimingChallenge]:
        query = self.db.query(TimingChallenge).filter(TimingChallenge.chapter_key == chapter_key)
        if not include_retired:
            query = query.filter(TimingChallenge.status == "ready")
        return query.order_by(TimingChallenge.created_at, TimingChallenge.challenge_id).all()

    def get_current_record(self, chapter_key: str) -> TimingChallenge | None:
        return (
            self.db.query(TimingChallenge)
            .filter(TimingChallenge.chapter_key == chapter_key, TimingChallenge.is_current.is_(True))
            .first()
        )

    def save_generated(self, generated: GeneratedTimingChallenge, chapter_key: str, topic: str) -> StoredTimingChallenge:
        existing = self.db.query(TimingChallenge).filter(TimingChallenge.challenge_id == generated.challenge_id).first()
        if existing:
            return self._to_stored(existing)

        dag_text = generated.dag_file.read_text(encoding="utf-8") if generated.dag_file.exists() else _dag_to_text(generated)
        record = TimingChallenge(
            challenge_id=generated.challenge_id,
            chapter_key=chapter_key,
            topic=topic,
            model=generated.model,
            dag_file_name=generated.dag_file.name,
            dag_text=dag_text,
            # The existing SQLite column is non-null; zero represents absent optional metadata.
            clock_period=generated.dag.clock_period or 0.0,
            dag_payload=generated.dag.to_dict(),
            questions_payload=generated.questions,
            status="ready",
            is_current=False,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return self._to_stored(record)

    def mark_current(self, chapter_key: str, challenge_id: str, previous_challenge_id: str | None = None) -> None:
        if previous_challenge_id and previous_challenge_id != challenge_id:
            previous = (
                self.db.query(TimingChallenge)
                .filter(
                    TimingChallenge.chapter_key == chapter_key,
                    TimingChallenge.challenge_id == previous_challenge_id,
                )
                .first()
            )
            if previous:
                previous.is_current = False
                previous.status = "retired"

        self.db.query(TimingChallenge).filter(
            TimingChallenge.chapter_key == chapter_key,
            TimingChallenge.challenge_id != challenge_id,
            TimingChallenge.is_current.is_(True),
        ).update({TimingChallenge.is_current: False}, synchronize_session=False)
        current = (
            self.db.query(TimingChallenge)
            .filter(TimingChallenge.chapter_key == chapter_key, TimingChallenge.challenge_id == challenge_id)
            .first()
        )
        if current is None:
            raise KeyError(f"Unknown timing challenge: {challenge_id}")
        current.status = "ready"
        current.is_current = True
        current.published_at = _utcnow()
        self.db.commit()

    def enqueue_generation_job(self, chapter_key: str, topic: str, model: str) -> str:
        job = TimingGenerationJob(
            job_id=uuid.uuid4().hex,
            chapter_key=chapter_key,
            topic=topic,
            model=model,
            status="queued",
        )
        self.db.add(job)
        self.db.commit()
        return job.job_id

    def claim_next_generation_job(self, chapter_key: str) -> TimingGenerationJob | None:
        job = (
            self.db.query(TimingGenerationJob)
            .filter(TimingGenerationJob.chapter_key == chapter_key, TimingGenerationJob.status == "queued")
            .order_by(TimingGenerationJob.requested_at, TimingGenerationJob.job_id)
            .first()
        )
        if job is None:
            return None
        job.status = "running"
        job.started_at = _utcnow()
        self.db.commit()
        self.db.refresh(job)
        return job

    def complete_generation_job(self, job_id: str, challenge_id: str) -> None:
        job = self.db.query(TimingGenerationJob).filter(TimingGenerationJob.job_id == job_id).first()
        if job is None:
            return
        job.status = "succeeded"
        job.challenge_id = challenge_id
        job.completed_at = _utcnow()
        job.error_message = None
        self.db.commit()

    def fail_generation_job(self, job_id: str, error_message: str) -> None:
        job = self.db.query(TimingGenerationJob).filter(TimingGenerationJob.job_id == job_id).first()
        if job is None:
            return
        job.status = "failed"
        job.completed_at = _utcnow()
        job.error_message = error_message[:2000]
        self.db.commit()

    def recover_interrupted_jobs(self) -> None:
        self.db.query(TimingGenerationJob).filter(TimingGenerationJob.status == "running").update(
            {TimingGenerationJob.status: "queued", TimingGenerationJob.started_at: None},
            synchronize_session=False,
        )
        self.db.commit()

    def retire_noncompliant_records(self, chapter_key: str) -> list[str]:
        """Keep historical rows but prevent legacy, repetitive graphs from being assigned again."""

        retired_ids: list[str] = []
        records = self.db.query(TimingChallenge).filter(
            TimingChallenge.chapter_key == chapter_key,
            TimingChallenge.status == "ready",
        )
        for record in records:
            try:
                clock_period = record.clock_period if record.clock_period > 0 else None
                dag = parse_timing_dag_text(record.dag_text, clock_period=clock_period)
                TimingAnalysisAgent._validate_fixed_complexity(dag)
            except (TimingAnalysisAgentError, TimingAnalysisError, TimingDagParseError, ValueError):
                record.status = "retired"
                record.is_current = False
                retired_ids.append(record.challenge_id)
        if retired_ids:
            self.db.commit()
        return retired_ids

    def record_attempt(
        self,
        player_id: str,
        challenge_id: str,
        question_id: str,
        answer_payload: dict[str, Any],
        result_payload: dict[str, Any],
    ) -> None:
        self.db.add(
            TimingChallengeAttempt(
                player_id=player_id,
                challenge_id=challenge_id,
                question_id=question_id,
                answer_payload=answer_payload,
                result_payload=result_payload,
                is_correct=bool(result_payload["correct"]),
            )
        )
        self.db.commit()

    def import_existing_dag_files(self, chapter_key: str) -> None:
        if not self.storage_dir.exists():
            return
        for dag_file in sorted(self.storage_dir.glob("*.txt")):
            challenge_id = dag_file.stem
            if len(challenge_id) != 32 or self.db.query(TimingChallenge).filter(
                TimingChallenge.challenge_id == challenge_id
            ).first():
                continue
            try:
                dag = parse_timing_dag_text(dag_file.read_text(encoding="utf-8"))
                TimingAnalysisAgent._validate_fixed_complexity(dag)
                generated = GeneratedTimingChallenge(
                    challenge_id=challenge_id,
                    dag=dag,
                    dag_file=dag_file,
                    questions=TimingAnalysisAgent._build_questions(dag),
                    model="legacy-import",
                )
                self.save_generated(generated, chapter_key, "legacy timing challenge")
            except (OSError, TimingAnalysisAgentError, TimingAnalysisError, TimingDagParseError):
                continue

    def create_initial_challenge(self, chapter_key: str) -> StoredTimingChallenge:
        challenge_id = uuid.uuid4().hex
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        dag_file = self.storage_dir / f"{challenge_id}.txt"
        dag_file.write_text(INITIAL_DAG_TEXT, encoding="utf-8")
        dag = parse_timing_dag_text(INITIAL_DAG_TEXT)
        TimingAnalysisAgent._validate_fixed_complexity(dag)
        generated = GeneratedTimingChallenge(
            challenge_id=challenge_id,
            dag=dag,
            dag_file=dag_file,
            questions=TimingAnalysisAgent._build_questions(dag),
            model="bootstrap",
        )
        return self.save_generated(generated, chapter_key, "initial timing challenge")

    def _to_stored(self, record: TimingChallenge) -> StoredTimingChallenge:
        clock_period = record.clock_period if record.clock_period > 0 else None
        dag = parse_timing_dag_text(record.dag_text, clock_period=clock_period)
        generated = GeneratedTimingChallenge(
            challenge_id=record.challenge_id,
            dag=dag,
            dag_file=self.storage_dir / record.dag_file_name,
            questions=record.questions_payload,
            model=record.model,
        )
        return StoredTimingChallenge(generated=generated, analysis=TimingAnalysisEngine().analyze(dag))


def _dag_to_text(generated: GeneratedTimingChallenge) -> str:
    edge_lines = [f"{edge.from_}-{edge.to}" for edge in generated.dag.edges]
    delay_lines = [
        f"{node.id}:{node.delay:g}"
        for node in generated.dag.nodes
        if node.id not in {generated.dag.start_node, generated.dag.end_node}
    ]
    return "\n".join([*edge_lines, *delay_lines]) + "\n"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def initialize_timing_challenge_pool(chapter_key: str = TIMING_CHAPTER_KEY) -> None:
    """Migrate existing DAG files, establish an initial challenge, and hydrate Redis from SQLite."""

    db = SessionLocal()
    try:
        repository = TimingChallengeRepository(db)
        repository.recover_interrupted_jobs()
        repository.import_existing_dag_files(chapter_key)
        retired_ids = repository.retire_noncompliant_records(chapter_key)

        records = repository.list_records(chapter_key, include_retired=True)
        if not any(record.status == "ready" for record in records):
            repository.create_initial_challenge(chapter_key)
            records = repository.list_records(chapter_key, include_retired=True)

        current = repository.get_current_record(chapter_key)
        if current is None:
            current = next((record for record in records if record.status == "ready"), None)
            if current is None:
                stored = repository.create_initial_challenge(chapter_key)
                repository.mark_current(chapter_key, stored.generated.challenge_id)
                records = repository.list_records(chapter_key, include_retired=True)
                current = repository.get_current_record(chapter_key)
            else:
                repository.mark_current(chapter_key, current.challenge_id)

        cache = TimingChallengeCache(get_redis_client())
        if retired_ids:
            cache.invalidate_challenges(retired_ids)
            cache.clear_assignments_for_challenges(chapter_key, retired_ids)

        for record in records:
            if record.status != "ready":
                continue
            stored = repository._to_stored(record)
            cache.set_challenge(record.challenge_id, cache_payload(stored))

        current = repository.get_current_record(chapter_key)
        if current is None:
            raise RuntimeError("Timing challenge pool has no current challenge")
        ready_ids = [
            record.challenge_id
            for record in repository.list_records(chapter_key, include_retired=False)
            if record.challenge_id != current.challenge_id
        ]
        cache.replace_chapter_state(chapter_key, current.challenge_id, ready_ids)
    finally:
        db.close()
