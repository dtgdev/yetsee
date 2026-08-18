"""Galileo G3.1: persistent investigation missions.

Revision ID: 0013_investigation_missions
Revises: 0012_reasoning_runtime
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_investigation_missions"
down_revision = "0012_reasoning_runtime"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "investigation_missions",
        sa.Column("investigation_id", sa.String(length=36), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requested_by", sa.String(length=100), nullable=False),
        sa.Column("correlation_id", sa.String(length=36), nullable=True),
        sa.Column("command_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ("investigation_id", "status", "correlation_id", "command_id", "started_at", "finished_at"):
        op.create_index(op.f("ix_investigation_missions_" + col), "investigation_missions", [col], unique=False)

    op.create_table(
        "investigation_mission_steps",
        sa.Column("mission_id", sa.String(length=36), nullable=False),
        sa.Column("investigation_id", sa.String(length=36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.String(length=100), nullable=False),
        sa.Column("task_type", sa.String(length=100), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column("command_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("input_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("finding_ids", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"]),
        sa.ForeignKeyConstraint(["mission_id"], ["investigation_missions.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["agent_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mission_id", "sequence", name="uq_mission_step_sequence"),
    )
    for col in ("mission_id", "investigation_id", "agent_id", "task_id", "command_id", "status", "started_at", "finished_at"):
        op.create_index(op.f("ix_investigation_mission_steps_" + col), "investigation_mission_steps", [col], unique=False)


def downgrade() -> None:
    for col in reversed(("mission_id", "investigation_id", "agent_id", "task_id", "command_id", "status", "started_at", "finished_at")):
        op.drop_index(op.f("ix_investigation_mission_steps_" + col), table_name="investigation_mission_steps")
    op.drop_table("investigation_mission_steps")
    for col in reversed(("investigation_id", "status", "correlation_id", "command_id", "started_at", "finished_at")):
        op.drop_index(op.f("ix_investigation_missions_" + col), table_name="investigation_missions")
    op.drop_table("investigation_missions")
