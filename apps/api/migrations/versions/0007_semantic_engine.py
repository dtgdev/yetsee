"""Semantic Engine: canonical concepts and semantic run audit history.

Revision ID: 0007_semantic_engine
Revises: 0006_agent_orchestration
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_semantic_engine"
down_revision = "0006_agent_orchestration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "semantic_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("observation_count", sa.Integer(), nullable=False),
        sa.Column("concept_count", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ["status", "started_at", "finished_at"]:
        op.create_index(f"ix_semantic_runs_{column}", "semantic_runs", [column])

    op.create_table(
        "semantic_concepts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("observation_id", sa.String(36), nullable=False),
        sa.Column("canonical_name", sa.String(255), nullable=False),
        sa.Column("canonical_key", sa.String(320), nullable=False),
        sa.Column("kind", sa.String(80), nullable=False),
        sa.Column("mention_text", sa.String(500)),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("method", sa.String(100), nullable=False),
        sa.Column("extractor_version", sa.String(40), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("observation_id", "canonical_key", "extractor_version", name="uq_semantic_concept_observation_key_version"),
    )
    for column in ["observation_id", "canonical_name", "canonical_key", "kind", "method"]:
        op.create_index(f"ix_semantic_concepts_{column}", "semantic_concepts", [column])


def downgrade() -> None:
    op.drop_table("semantic_concepts")
    op.drop_table("semantic_runs")
