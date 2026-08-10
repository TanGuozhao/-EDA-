from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.db.mysql.database import Base
from app.adapters.db.mysql.models import TimingChallenge, TimingChallengeAttempt
from app.timing.agent import GeneratedTimingChallenge
from app.timing.challenge_repository import TimingChallengeRepository, cache_payload, cached_challenge_to_stored
from app.timing.dag_text import parse_timing_dag_text


def test_repository_persists_challenges_jobs_and_attempts_without_clock_period(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    dag_file = tmp_path / "challenge-001.txt"
    dag_file.write_text("START-A\nA-END\nA:2\n", encoding="utf-8")
    dag = parse_timing_dag_text(dag_file.read_text(encoding="utf-8"))
    generated = GeneratedTimingChallenge(
        challenge_id="challenge-001",
        dag=dag,
        dag_file=dag_file,
        questions=[{"id": "arrival_time", "type": "arrival_time", "target_node_ids": ["A"]}],
        model="test-model",
    )
    repository = TimingChallengeRepository(session, storage_dir=tmp_path)

    stored = repository.save_generated(generated, "chapter-5", "test topic")
    repository.mark_current("chapter-5", stored.generated.challenge_id)

    restored = repository.get(stored.generated.challenge_id)
    cached = cached_challenge_to_stored(cache_payload(restored))
    job_id = repository.enqueue_generation_job("chapter-5", "next topic", "test-model")
    claimed_job = repository.claim_next_generation_job("chapter-5")
    repository.complete_generation_job(job_id, stored.generated.challenge_id)
    repository.record_attempt(
        player_id="player-001",
        challenge_id=stored.generated.challenge_id,
        question_id="arrival_time",
        answer_payload={"answers": {"A": 0}},
        result_payload={"correct": True, "question_type": "arrival_time"},
    )

    assert restored is not None
    assert restored.generated.dag.clock_period is None
    assert cached.generated.challenge_id == stored.generated.challenge_id
    assert claimed_job is not None and claimed_job.job_id == job_id
    assert session.query(TimingChallengeAttempt).count() == 1


def test_repository_retires_legacy_dags_that_fail_the_current_profile(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    dag_file = tmp_path / "legacy.txt"
    dag_file.write_text("START-A\nA-END\nA:2\n", encoding="utf-8")
    dag = parse_timing_dag_text(dag_file.read_text(encoding="utf-8"))
    generated = GeneratedTimingChallenge(
        challenge_id="legacy-challenge",
        dag=dag,
        dag_file=dag_file,
        questions=[],
        model="legacy-import",
    )
    repository = TimingChallengeRepository(session, storage_dir=tmp_path)
    repository.save_generated(generated, "chapter-5", "legacy topic")
    repository.mark_current("chapter-5", generated.challenge_id)

    assert repository.retire_noncompliant_records("chapter-5") == [generated.challenge_id]

    record = session.query(TimingChallenge).filter_by(challenge_id=generated.challenge_id).one()
    assert record.status == "retired"
    assert record.is_current is False
