"""Feature Engine append-only feature store.

Revision ID: 0004_feature_engine
Revises: 0003_discovery_engine
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_feature_engine"
down_revision = "0003_discovery_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "features",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("subject", sa.String(320), nullable=False),
        sa.Column("feature_type", sa.String(80), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("value", sa.Float()),
        sa.Column("vector", sa.JSON(), nullable=False),
        sa.Column("window", sa.String(40)),
        sa.Column("extractor_id", sa.String(120), nullable=False),
        sa.Column("extractor_version", sa.String(40), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ["subject", "feature_type", "name", "window", "extractor_id", "computed_at"]:
        op.create_index(f"ix_features_{column}", "features", [column])

    op.create_table(
        "feature_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("extractor_id", sa.String(120), nullable=False),
        sa.Column("extractor_version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("observation_count", sa.Integer(), nullable=False),
        sa.Column("feature_count", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_feature_runs_extractor_id", "feature_runs", ["extractor_id"])
    op.create_index("ix_feature_runs_status", "feature_runs", ["status"])


def downgrade() -> None:
    op.drop_table("feature_runs")
    op.drop_table("features")
