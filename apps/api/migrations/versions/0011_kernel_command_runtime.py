"""Kernel Command Runtime audit log.

Revision ID: 0011_kernel_command_runtime
Revises: 0010_confidence_engine
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_kernel_command_runtime"
down_revision = "0010_confidence_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kernel_command_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("command_id", sa.String(36), nullable=False, unique=True),
        sa.Column("command_type", sa.String(120), nullable=False),
        sa.Column("actor_type", sa.String(40), nullable=False),
        sa.Column("actor_id", sa.String(160)),
        sa.Column("aggregate_type", sa.String(80), nullable=False),
        sa.Column("aggregate_id", sa.String(36)),
        sa.Column("correlation_id", sa.String(36), nullable=False),
        sa.Column("causation_id", sa.String(36)),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("command_id", "command_type", "actor_type", "actor_id", "aggregate_type", "aggregate_id", "correlation_id", "causation_id", "status"):
        op.create_index(f"ix_kernel_command_log_{column}", "kernel_command_log", [column])


def downgrade() -> None:
    op.drop_table("kernel_command_log")
