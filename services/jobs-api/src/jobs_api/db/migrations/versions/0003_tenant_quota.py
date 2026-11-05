"""Tenants with their in-flight Job quota, and what a pending Job needs to be sent later

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("quota", sa.Integer, nullable=False),
    )
    # Every Job stored before this revision asked for sentiment alone.
    op.add_column(
        "jobs",
        sa.Column(
            "analyses",
            JSONB,
            nullable=False,
            server_default=sa.text("'[\"sentiment\"]'"),
        ),
    )
    op.alter_column("jobs", "analyses", server_default=None)
    op.add_column(
        "jobs",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    # The quota counts a Tenant's Jobs by state and releases its oldest pending one.
    op.create_index(
        "ix_jobs_tenant_state", "jobs", ["tenant_id", "state", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_jobs_tenant_state", "jobs")
    op.drop_column("jobs", "created_at")
    op.drop_column("jobs", "analyses")
    op.drop_table("tenants")
