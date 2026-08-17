"""YetSee OS Alpha kernel: event log, investigation revisions, workflows and plugins.

Revision ID: 0008_yetsee_os_kernel
Revises: 0007_semantic_engine
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_yetsee_os_kernel"
down_revision = "0007_semantic_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kernel_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("aggregate_type", sa.String(80), nullable=False),
        sa.Column("aggregate_id", sa.String(36)),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for col in ["event_type", "aggregate_type", "aggregate_id", "occurred_at"]:
        op.create_index(f"ix_kernel_events_{col}", "kernel_events", [col])

    op.create_table(
        "investigation_revisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("investigation_id", sa.String(36), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("change_type", sa.String(80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("author_type", sa.String(40), nullable=False),
        sa.Column("author_id", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("investigation_id", "revision_number", name="uq_investigation_revision_number"),
    )
    op.create_index("ix_investigation_revisions_investigation_id", "investigation_revisions", ["investigation_id"])
    op.create_index("ix_investigation_revisions_change_type", "investigation_revisions", ["change_type"])

    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workflow_id", sa.String(120), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("target_type", sa.String(80)),
        sa.Column("target_id", sa.String(36)),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for col in ["workflow_id", "status", "target_type", "target_id"]:
        op.create_index(f"ix_workflow_runs_{col}", "workflow_runs", [col])

    op.create_table(
        "plugin_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("plugin_id", sa.String(160), nullable=False, unique=True),
        sa.Column("plugin_type", sa.String(80), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for col in ["plugin_id", "plugin_type", "status"]:
        op.create_index(f"ix_plugin_records_{col}", "plugin_records", [col])


def downgrade() -> None:
    op.drop_table("plugin_records")
    op.drop_table("workflow_runs")
    op.drop_table("investigation_revisions")
    op.drop_table("kernel_events")
