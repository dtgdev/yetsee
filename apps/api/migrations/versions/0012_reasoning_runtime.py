"""Reasoning Runtime: persistent reasoning runs and results.

Revision ID: 0012_reasoning_runtime
Revises: 0011_kernel_command_runtime
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_reasoning_runtime"
down_revision = "0011_kernel_command_runtime"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reasoning_runs",
        sa.Column("investigation_id", sa.String(length=36), nullable=False),
        sa.Column("reasoner_id", sa.String(length=120), nullable=False),
        sa.Column("reasoner_version", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("triggered_by", sa.String(length=80), nullable=False),
        sa.Column("command_id", sa.String(length=36), nullable=True),
        sa.Column("correlation_id", sa.String(length=36), nullable=True),
        sa.Column("input_revision_id", sa.String(length=36), nullable=True),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ("investigation_id", "reasoner_id", "status", "command_id", "correlation_id", "input_revision_id"):
        op.create_index(op.f("ix_reasoning_runs_" + col), "reasoning_runs", [col], unique=False)

    op.create_table(
        "reasoning_results",
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("investigation_id", sa.String(length=36), nullable=False),
        sa.Column("reasoner_id", sa.String(length=120), nullable=False),
        sa.Column("conclusion", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("support_level", sa.String(length=40), nullable=False),
        sa.Column("supporting_factors", sa.JSON(), nullable=False),
        sa.Column("contradicting_factors", sa.JSON(), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("limitations", sa.JSON(), nullable=False),
        sa.Column("recommended_evidence", sa.JSON(), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["reasoning_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reasoning_results_run_id"), "reasoning_results", ["run_id"], unique=True)
    op.create_index(op.f("ix_reasoning_results_investigation_id"), "reasoning_results", ["investigation_id"], unique=False)
    op.create_index(op.f("ix_reasoning_results_reasoner_id"), "reasoning_results", ["reasoner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reasoning_results_reasoner_id"), table_name="reasoning_results")
    op.drop_index(op.f("ix_reasoning_results_investigation_id"), table_name="reasoning_results")
    op.drop_index(op.f("ix_reasoning_results_run_id"), table_name="reasoning_results")
    op.drop_table("reasoning_results")
    for col in reversed(("investigation_id", "reasoner_id", "status", "command_id", "correlation_id", "input_revision_id")):
        op.drop_index(op.f("ix_reasoning_runs_" + col), table_name="reasoning_runs")
    op.drop_table("reasoning_runs")
