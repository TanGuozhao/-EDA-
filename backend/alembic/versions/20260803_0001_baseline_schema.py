"""baseline schema

Revision ID: 20260803_0001
Revises:
Create Date: 2026-08-03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260803_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=512)),
        sa.Column("display_name", sa.String(length=100)),
        sa.Column("status", sa.String(length=20)),
        sa.Column("last_login_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_id", "users", ["id"])

    op.create_table(
        "chapters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("icon", sa.String(length=50)),
        sa.Column("sort_order", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_chapters_id", "chapters", ["id"])

    op.create_table(
        "tools",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("version", sa.String(length=20)),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean()),
        sa.Column("installed_path", sa.String(length=255)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_tools_id", "tools", ["id"])

    op.create_table(
        "timing_graphs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("clock_period", sa.Integer()),
        sa.Column("edges", sa.JSON(), nullable=False),
        sa.Column("delays", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_timing_graphs_id", "timing_graphs", ["id"])

    op.create_table(
        "levels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chapter_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("sort_order", sa.Integer()),
        sa.Column("question_ids", sa.JSON()),
        sa.Column("pass_criteria", sa.Text()),
        sa.Column("status", sa.Enum("locked", "unlocked", "completed", name="level_status")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"]),
    )
    op.create_index("ix_levels_id", "levels", ["id"])

    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("level_id", sa.Integer(), nullable=False),
        sa.Column("question_type", sa.Enum("choice", "qa", "code", "experiment", name="question_type")),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("options", sa.JSON()),
        sa.Column("correct_answer", sa.Text(), nullable=False),
        sa.Column("score", sa.Integer()),
        sa.Column("difficulty", sa.Integer()),
        sa.Column("hint", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["level_id"], ["levels.id"]),
    )
    op.create_index("ix_questions_id", "questions", ["id"])

    op.create_table(
        "experiments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("level_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("goal", sa.Text()),
        sa.Column("input_materials", sa.Text()),
        sa.Column("tools_required", sa.String(length=255)),
        sa.Column("expected_output", sa.Text()),
        sa.Column("pass_criteria", sa.Text()),
        sa.Column("status", sa.Enum("pending", "running", "passed", "failed", name="experiment_status")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["level_id"], ["levels.id"]),
    )
    op.create_index("ix_experiments_id", "experiments", ["id"])

    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer()),
        sa.Column("experiment_id", sa.Integer()),
        sa.Column("submission_type", sa.Enum("question", "experiment", name="submission_type"), nullable=False),
        sa.Column("user_answer", sa.Text()),
        sa.Column("result", sa.Text()),
        sa.Column("score", sa.Integer()),
        sa.Column("status", sa.Enum("pending", "correct", "wrong", "error", name="submission_status")),
        sa.Column("tool_output", sa.Text()),
        sa.Column("submitted_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_submissions_id", "submissions", ["id"])

    op.create_table(
        "user_sessions",
        sa.Column("session_key", sa.String(length=128), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("issued_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])

    op.create_table(
        "timing_challenges",
        sa.Column("challenge_id", sa.String(length=32), primary_key=True),
        sa.Column("chapter_key", sa.String(length=64), nullable=False),
        sa.Column("topic", sa.String(length=200), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("dag_file_name", sa.String(length=255), nullable=False),
        sa.Column("dag_text", sa.Text(), nullable=False),
        sa.Column("clock_period", sa.Float(), nullable=False),
        sa.Column("dag_payload", sa.JSON(), nullable=False),
        sa.Column("questions_payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime()),
        sa.CheckConstraint("status IN ('ready', 'retired')", name="ck_timing_challenges_status"),
    )
    op.create_index("ix_timing_challenges_chapter_key", "timing_challenges", ["chapter_key"])
    op.create_index("ix_timing_challenges_is_current", "timing_challenges", ["is_current"])
    op.create_index(
        "ix_timing_challenges_chapter_current",
        "timing_challenges",
        ["chapter_key", "is_current"],
    )

    op.create_table(
        "timing_generation_jobs",
        sa.Column("job_id", sa.String(length=32), primary_key=True),
        sa.Column("chapter_key", sa.String(length=64), nullable=False),
        sa.Column("topic", sa.String(length=200), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("challenge_id", sa.String(length=32)),
        sa.Column("error_message", sa.Text()),
        sa.Column("requested_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("completed_at", sa.DateTime()),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name="ck_timing_generation_jobs_status",
        ),
        sa.ForeignKeyConstraint(["challenge_id"], ["timing_challenges.challenge_id"]),
    )
    op.create_index("ix_timing_generation_jobs_chapter_key", "timing_generation_jobs", ["chapter_key"])
    op.create_index("ix_timing_generation_jobs_status", "timing_generation_jobs", ["status"])

    op.create_table(
        "timing_challenge_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("challenge_id", sa.String(length=32), nullable=False),
        sa.Column("player_id", sa.String(length=128), nullable=False),
        sa.Column("question_id", sa.String(length=64), nullable=False),
        sa.Column("answer_payload", sa.JSON(), nullable=False),
        sa.Column("result_payload", sa.JSON(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["challenge_id"], ["timing_challenges.challenge_id"]),
    )
    op.create_index("ix_timing_challenge_attempts_id", "timing_challenge_attempts", ["id"])
    op.create_index(
        "ix_timing_challenge_attempts_player_question",
        "timing_challenge_attempts",
        ["player_id", "challenge_id", "question_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_timing_challenge_attempts_player_question", table_name="timing_challenge_attempts")
    op.drop_index("ix_timing_challenge_attempts_id", table_name="timing_challenge_attempts")
    op.drop_table("timing_challenge_attempts")
    op.drop_index("ix_timing_generation_jobs_status", table_name="timing_generation_jobs")
    op.drop_index("ix_timing_generation_jobs_chapter_key", table_name="timing_generation_jobs")
    op.drop_table("timing_generation_jobs")
    op.drop_index("ix_timing_challenges_chapter_current", table_name="timing_challenges")
    op.drop_index("ix_timing_challenges_is_current", table_name="timing_challenges")
    op.drop_index("ix_timing_challenges_chapter_key", table_name="timing_challenges")
    op.drop_table("timing_challenges")
    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index("ix_submissions_id", table_name="submissions")
    op.drop_table("submissions")
    op.drop_index("ix_experiments_id", table_name="experiments")
    op.drop_table("experiments")
    op.drop_index("ix_questions_id", table_name="questions")
    op.drop_table("questions")
    op.drop_index("ix_levels_id", table_name="levels")
    op.drop_table("levels")
    op.drop_index("ix_timing_graphs_id", table_name="timing_graphs")
    op.drop_table("timing_graphs")
    op.drop_index("ix_tools_id", table_name="tools")
    op.drop_table("tools")
    op.drop_index("ix_chapters_id", table_name="chapters")
    op.drop_table("chapters")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
