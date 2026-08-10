from sqlalchemy import create_engine, inspect

from app.adapters.db.mysql.database import Base
from app.adapters.db.mysql.models import TimingChallenge, TimingChallengeAttempt, TimingGenerationJob
from app.timing.cache import TimingRedisKeys


def test_timing_persistence_tables_are_registered():
    assert TimingChallenge.__tablename__ == "timing_challenges"
    assert TimingGenerationJob.__tablename__ == "timing_generation_jobs"
    assert TimingChallengeAttempt.__tablename__ == "timing_challenge_attempts"

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    table_names = set(inspect(engine).get_table_names())

    assert {"timing_challenges", "timing_generation_jobs", "timing_challenge_attempts"} <= table_names


def test_timing_redis_keys_are_chapter_scoped_and_versioned():
    keys = TimingRedisKeys()

    assert keys.challenge("challenge-001") == "timing:v1:challenge:challenge-001"
    assert keys.current("chapter-5") == "timing:v1:current:chapter-5"
    assert keys.ready_pool("chapter-5") == "timing:v1:pool:ready:chapter-5"
    assert keys.generation_lock("chapter-5") == "timing:v1:lock:generate:chapter-5"
