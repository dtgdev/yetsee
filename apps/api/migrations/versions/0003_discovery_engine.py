"""Discovery Engine detector audit and candidate tables.

Revision ID: 0003_discovery_engine
Revises: 0002_signal_lake
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_discovery_engine"
down_revision = "0002_signal_lake"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "detector_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("detector_id", sa.String(120), nullable=False),
        sa.Column("detector_version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("observation_count", sa.Integer(), nullable=False),
        sa.Column("signal_count", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_detector_runs_detector_id", "detector_runs", ["detector_id"])
    op.create_index("ix_detector_runs_status", "detector_runs", ["status"])
    op.create_table(
        "discovery_candidates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("canonical_key", sa.String(320), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("detector_count", sa.Integer(), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("detector_scores", sa.JSON(), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_discovery_candidates_canonical_key", "discovery_candidates", ["canonical_key"])
    op.create_index("ix_discovery_candidates_title", "discovery_candidates", ["title"])
    op.create_index("ix_discovery_candidates_status", "discovery_candidates", ["status"])


def downgrade() -> None:
    op.drop_table("discovery_candidates")
    op.drop_table("detector_runs")
