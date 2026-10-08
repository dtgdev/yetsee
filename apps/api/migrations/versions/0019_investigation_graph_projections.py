"""Investigation graph projection freshness and active membership."""

from alembic import op
import sqlalchemy as sa

revision = "0019_investigation_graph"
down_revision = "0018_claim_candidate_reviews"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "investigation_graph_projections",
        sa.Column("investigation_id", sa.String(36), nullable=False),
        sa.Column("projection_version", sa.String(80), nullable=False),
        sa.Column("input_fingerprint", sa.String(64), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"]),
        sa.PrimaryKeyConstraint("investigation_id"),
    )


def downgrade() -> None:
    op.drop_table("investigation_graph_projections")
