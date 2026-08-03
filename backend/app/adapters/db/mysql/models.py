from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(512))
    display_name = Column(String(100))
    status = Column(String(20), nullable=False, default="active")
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


class UserSession(Base):
    __tablename__ = "user_sessions"

    session_key = Column(String(128), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    issued_at = Column(DateTime, nullable=False, server_default=func.now())
    expires_at = Column(DateTime, nullable=False, index=True)


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(Text)
    icon = Column(String(50))
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    levels = relationship("Level", back_populates="chapter", order_by="Level.sort_order")


class Level(Base):
    __tablename__ = "levels"

    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text)
    sort_order = Column(Integer, default=0)
    question_ids = Column(JSON)
    pass_criteria = Column(Text)
    status = Column(Enum("locked", "unlocked", "completed"), default="locked")
    created_at = Column(DateTime, server_default=func.now())

    chapter = relationship("Chapter", back_populates="levels")
    questions = relationship("Question", back_populates="level")
    experiment = relationship("Experiment", back_populates="level", uselist=False)


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    level_id = Column(Integer, ForeignKey("levels.id"), nullable=False)
    question_type = Column(Enum("choice", "qa", "code", "experiment"), default="choice")
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    options = Column(JSON)
    correct_answer = Column(Text, nullable=False)
    score = Column(Integer, default=10)
    difficulty = Column(Integer, default=1)
    hint = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    level = relationship("Level", back_populates="questions")


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)
    level_id = Column(Integer, ForeignKey("levels.id"), nullable=False)
    name = Column(String(100), nullable=False)
    goal = Column(Text)
    input_materials = Column(Text)
    tools_required = Column(String(255))
    expected_output = Column(Text)
    pass_criteria = Column(Text)
    status = Column(Enum("pending", "running", "passed", "failed"), default="pending")
    created_at = Column(DateTime, server_default=func.now())

    level = relationship("Level", back_populates="experiment")


class Tool(Base):
    __tablename__ = "tools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    version = Column(String(20))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    installed_path = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())


class AgentToolAudit(Base):
    __tablename__ = "agent_tool_audits"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(128), nullable=False, index=True)
    tool_id = Column(String(128), nullable=False, index=True)
    user_id = Column(String(128), nullable=False, index=True)
    session_id = Column(String(128))
    agent_id = Column(String(128))
    skill_id = Column(String(128))
    arguments_summary = Column(JSON, nullable=False)
    result_summary = Column(Text, nullable=False, default="")
    status = Column(String(16), nullable=False)
    error_code = Column(String(128))
    elapsed_ms = Column(Integer)
    resource_ids = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class TimingGraphRecord(Base):
    __tablename__ = "timing_graphs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    clock_period = Column(Integer, default=15)
    edges = Column(JSON, nullable=False)
    delays = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class TimingChallenge(Base):
    """A durable timing level: one DAG and its five deterministic questions."""

    __tablename__ = "timing_challenges"

    challenge_id = Column(String(32), primary_key=True)
    chapter_key = Column(String(64), nullable=False, index=True)
    topic = Column(String(200), nullable=False)
    model = Column(String(200), nullable=False)
    dag_file_name = Column(String(255), nullable=False)
    dag_text = Column(Text, nullable=False)
    clock_period = Column(Float, nullable=False)
    dag_payload = Column(JSON, nullable=False)
    questions_payload = Column(JSON, nullable=False)
    status = Column(String(16), nullable=False, default="ready")
    is_current = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    published_at = Column(DateTime)

    generation_jobs = relationship("TimingGenerationJob", back_populates="challenge")
    attempts = relationship("TimingChallengeAttempt", back_populates="challenge")

    __table_args__ = (
        CheckConstraint("status IN ('ready', 'retired')", name="ck_timing_challenges_status"),
        Index("ix_timing_challenges_chapter_current", "chapter_key", "is_current"),
    )


class TimingGenerationJob(Base):
    """Lifecycle record for an asynchronous timing challenge generation request."""

    __tablename__ = "timing_generation_jobs"

    job_id = Column(String(32), primary_key=True)
    chapter_key = Column(String(64), nullable=False, index=True)
    topic = Column(String(200), nullable=False)
    model = Column(String(200), nullable=False)
    status = Column(String(16), nullable=False, default="queued", index=True)
    challenge_id = Column(String(32), ForeignKey("timing_challenges.challenge_id"))
    error_message = Column(Text)
    requested_at = Column(DateTime, nullable=False, server_default=func.now())
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    challenge = relationship("TimingChallenge", back_populates="generation_jobs")

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name="ck_timing_generation_jobs_status",
        ),
    )


class TimingChallengeAttempt(Base):
    """One submitted answer. Player identity can be an authenticated or anonymous ID."""

    __tablename__ = "timing_challenge_attempts"

    id = Column(Integer, primary_key=True, index=True)
    challenge_id = Column(String(32), ForeignKey("timing_challenges.challenge_id"), nullable=False)
    player_id = Column(String(128), nullable=False)
    question_id = Column(String(64), nullable=False)
    answer_payload = Column(JSON, nullable=False)
    result_payload = Column(JSON, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    submitted_at = Column(DateTime, nullable=False, server_default=func.now())

    challenge = relationship("TimingChallenge", back_populates="attempts")

    __table_args__ = (
        Index(
            "ix_timing_challenge_attempts_player_question",
            "player_id",
            "challenge_id",
            "question_id",
        ),
    )


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"))
    experiment_id = Column(Integer, ForeignKey("experiments.id"))
    submission_type = Column(Enum("question", "experiment"), nullable=False)
    user_answer = Column(Text)
    result = Column(Text)
    score = Column(Integer, default=0)
    status = Column(Enum("pending", "correct", "wrong", "error"), default="pending")
    tool_output = Column(Text)
    submitted_at = Column(DateTime, server_default=func.now())
