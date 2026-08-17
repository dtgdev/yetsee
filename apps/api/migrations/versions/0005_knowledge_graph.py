"""Knowledge Graph Engine: entity aliases, temporal evidence-backed edges and graph runs.

Revision ID: 0005_knowledge_graph
Revises: 0004_feature_engine
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_knowledge_graph"
down_revision = "0004_feature_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("entities", sa.Column("aliases", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("entities", sa.Column("description", sa.Text()))

    op.add_column("relationships", sa.Column("evidence_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("relationships", sa.Column("first_seen", sa.DateTime(timezone=True)))
    op.add_column("relationships", sa.Column("last_seen", sa.DateTime(timezone=True)))
    op.create_index("ix_relationships_first_seen", "relationships", ["first_seen"])
    op.create_index("ix_relationships_last_seen", "relationships", ["last_seen"])

    op.create_table(
        "graph_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("observation_count", sa.Integer(), nullable=False),
        sa.Column("entity_count", sa.Integer(), nullable=False),
        sa.Column("relationship_count", sa.Integer(), nullable=False),
        sa.Column("feature_count", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_graph_runs_status", "graph_runs", ["status"])


def downgrade() -> None:
    op.drop_table("graph_runs")
    op.drop_index("ix_relationships_last_seen", table_name="relationships")
    op.drop_index("ix_relationships_first_seen", table_name="relationships")
    op.drop_column("relationships", "last_seen")
    op.drop_column("relationships", "first_seen")
    op.drop_column("relationships", "evidence_ids")
    op.drop_column("entities", "description")
    op.drop_column("entities", "aliases")
