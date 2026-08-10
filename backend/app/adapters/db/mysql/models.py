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
# name=backend/app/adapters/db/mysql/models.py
"""
在现有 models.py 中追加所需的数据模型。
确保运行迁移将这些表创建到 MySQL（此处仅模型声明）。
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    JSON,
    func,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from app.adapters.db.mysql.database import Base


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


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(120), nullable=False)
    mode = Column(String(40), nullable=False, default="eda")
    reply_style = Column(String(40), nullable=False, default="default")
    last_message_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )

    __table_args__ = (
        Index("ix_chat_sessions_user_last_message", "user_id", "last_message_at"),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text)
    model = Column(String(120))
    request_id = Column(String(128), index=True)
    skill_id = Column(String(128))
    attachment_ids = Column(JSON, nullable=False, default=list)
    rag_sources = Column(JSON, nullable=False, default=list)
    tool_calls = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)

    session = relationship("ChatSession", back_populates="messages")

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_chat_messages_role"),
        Index("ix_chat_messages_session_created", "session_id", "created_at"),
    )


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




class RTLDesign(Base):
    __tablename__ = "rtl_designs"

    design_id = Column(String(64), primary_key=True, index=True)
    requirement = Column(Text, nullable=False)
    module_name = Column(String(128), nullable=False)
    ports = Column(JSON, nullable=False)
    reference_verilog = Column(Text, nullable=False)
    llm_model = Column(String(128), nullable=True)
    status = Column(String(64), nullable=False, default="created")
    created_at = Column(DateTime, server_default=func.now())

    validation_runs = relationship("RTLValidationRun", back_populates="design")
    repair_questions = relationship("RTLRepairQuestion", back_populates="design")


class RTLValidationRun(Base):
    __tablename__ = "rtl_validation_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    design_id = Column(String(64), ForeignKey("rtl_designs.design_id"), nullable=True)
    input_verilog = Column(Text, nullable=False)
    input_hash = Column(String(128), nullable=False, index=True)
    tool_name = Column(String(64), nullable=False)
    tool_version = Column(String(64), nullable=True)
    command = Column(Text, nullable=True)
    exit_code = Column(Integer, nullable=False)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    logs = Column(Text, nullable=True)
    summary = Column(JSON, nullable=True)
    passed = Column(Boolean, nullable=False, default=False)
    run_at = Column(DateTime, server_default=func.now())

    design = relationship("RTLDesign", back_populates="validation_runs")


class RTLRepairQuestion(Base):
    __tablename__ = "rtl_repair_questions"

    question_id = Column(String(64), primary_key=True, index=True)
    design_id = Column(String(64), ForeignKey("rtl_designs.design_id"), nullable=True)
    requirement = Column(Text, nullable=False)
    module_name = Column(String(128), nullable=False)
    ports = Column(JSON, nullable=False)
    error_verilog = Column(Text, nullable=False)
    reference_verilog = Column(Text, nullable=True)
    error_type = Column(String(64), nullable=False)
    hidden_tests = Column(JSON, nullable=True)
    status = Column(String(64), nullable=False, default="active")
    created_at = Column(DateTime, server_default=func.now())

    design = relationship("RTLDesign", back_populates="repair_questions")
    submissions = relationship("RTLSubmission", back_populates="question")


class RTLSubmission(Base):
    __tablename__ = "rtl_submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(String(64), ForeignKey("rtl_repair_questions.question_id"), nullable=False)
    user_id = Column(Integer, nullable=False)
    submitted_verilog = Column(Text, nullable=False)
    validation_run_id = Column(Integer, ForeignKey("rtl_validation_runs.id"), nullable=True)
    passed = Column(Boolean, nullable=False, default=False)
    score = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)
    submitted_at = Column(DateTime, server_default=func.now())

    question = relationship("RTLRepairQuestion", back_populates="submissions")


# HLS 数据模型
class HLSChallenge(Base):
    __tablename__ = "hls_challenges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    challenge_id = Column(String(64), unique=True, nullable=False, index=True)
    dag_json = Column(JSON, nullable=False)
    resource_constraints = Column(JSON, nullable=False)
    algorithm = Column(String(64), nullable=False)
    correct_answer = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    submissions = relationship("HLSSubmission", back_populates="challenge")


class HLSSubmission(Base):
    __tablename__ = "hls_submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    challenge_id = Column(String(64), ForeignKey("hls_challenges.challenge_id"), nullable=False)
    user_id = Column(Integer, nullable=False)
    student_answer_json = Column(JSON, nullable=False)
    passed = Column(Boolean, nullable=False, default=False)
    score = Column(Integer, nullable=True)
    feedback = Column(JSON, nullable=True)
    submitted_at = Column(DateTime, server_default=func.now())

    challenge = relationship("HLSChallenge", back_populates="submissions")

