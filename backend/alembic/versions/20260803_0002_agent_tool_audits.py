"""add persistent agent tool audits

Revision ID: 20260803_0002
Revises: 20260803_0001
Create Date: 2026-08-03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260803_0002"
down_revision = "20260803_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_tool_audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("tool_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("session_id", sa.String(length=128)),
        sa.Column("agent_id", sa.String(length=128)),
        sa.Column("skill_id", sa.String(length=128)),
        sa.Column("arguments_summary", sa.JSON(), nullable=False),
        sa.Column("result_summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_code", sa.String(length=128)),
        sa.Column("elapsed_ms", sa.Integer()),
        sa.Column("resource_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_agent_tool_audits_id", "agent_tool_audits", ["id"])
    op.create_index("ix_agent_tool_audits_request_id", "agent_tool_audits", ["request_id"])
    op.create_index("ix_agent_tool_audits_tool_id", "agent_tool_audits", ["tool_id"])
    op.create_index("ix_agent_tool_audits_user_id", "agent_tool_audits", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_tool_audits_user_id", table_name="agent_tool_audits")
    op.drop_index("ix_agent_tool_audits_tool_id", table_name="agent_tool_audits")
    op.drop_index("ix_agent_tool_audits_request_id", table_name="agent_tool_audits")
    op.drop_index("ix_agent_tool_audits_id", table_name="agent_tool_audits")
    op.drop_table("agent_tool_audits")
