"""Jobs, their Segments and one result per step

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("tenant_id", sa.String, nullable=False),
        sa.Column("state", sa.String, nullable=False),
        sa.Column("language", sa.String, nullable=False),
    )
    op.create_table(
        "segments",
        sa.Column("job_id", sa.Uuid, sa.ForeignKey("jobs.id"), primary_key=True),
        sa.Column("index", sa.Integer, primary_key=True),
        sa.Column("text", sa.Text, nullable=False),
    )
    op.create_table(
        "step_results",
        sa.Column("job_id", sa.Uuid, sa.ForeignKey("jobs.id"), primary_key=True),
        sa.Column("step", sa.String, primary_key=True),
        sa.Column("payload", JSONB, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("step_results")
    op.drop_table("segments")
    op.drop_table("jobs")
