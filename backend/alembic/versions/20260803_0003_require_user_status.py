"""require a populated user status

Revision ID: 20260803_0003
Revises: 20260803_0002
Create Date: 2026-08-03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260803_0003"
down_revision = "20260803_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE users SET status = 'active' WHERE status IS NULL OR status = ''")
    with op.batch_alter_table("users") as batch:
        batch.alter_column("status", existing_type=sa.String(length=20), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.alter_column("status", existing_type=sa.String(length=20), nullable=True)
