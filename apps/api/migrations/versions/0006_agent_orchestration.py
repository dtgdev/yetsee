"""Agent Orchestration Layer: typed tasks, audited runs and evidence-linked findings.

Revision ID: 0006_agent_orchestration
Revises: 0005_knowledge_graph
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_agent_orchestration"
down_revision = "0005_knowledge_graph"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_type", sa.String(100), nullable=False),
        sa.Column("agent_id", sa.String(100), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(80)),
        sa.Column("target_id", sa.String(100)),
        sa.Column("requested_by", sa.String(100), nullable=False),
        sa.Column("input_json", sa.JSON(), nullable=False),
        sa.Column("constraints", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ["task_type", "agent_id", "status", "target_type", "target_id", "started_at", "finished_at"]:
        op.create_index(f"ix_agent_tasks_{column}", "agent_tasks", [column])

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("agent_tasks.id"), nullable=False),
        sa.Column("agent_id", sa.String(100), nullable=False),
        sa.Column("agent_version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("input_json", sa.JSON(), nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=False),
        sa.Column("permissions_used", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ["task_id", "agent_id", "status"]:
        op.create_index(f"ix_agent_runs_{column}", "agent_runs", [column])

    op.create_table(
        "agent_findings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("agent_tasks.id"), nullable=False),
        sa.Column("agent_id", sa.String(100), nullable=False),
        sa.Column("target_type", sa.String(80)),
        sa.Column("target_id", sa.String(100)),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(24), nullable=False),
        sa.Column("stance", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ["task_id", "agent_id", "target_type", "target_id", "category", "severity"]:
        op.create_index(f"ix_agent_findings_{column}", "agent_findings", [column])


def downgrade() -> None:
    op.drop_table("agent_findings")
    op.drop_table("agent_runs")
    op.drop_table("agent_tasks")
