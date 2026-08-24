"""scientific claim candidate reviews

Revision ID: 0018_claim_candidate_reviews
Revises: 0017_scientific_literature
"""

from alembic import op
import sqlalchemy as sa

revision = "0018_claim_candidate_reviews"
down_revision = "0017_scientific_literature"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scientific_claim_candidate_reviews",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("investigation_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=40), nullable=False),
        sa.Column("decision", sa.String(length=24), nullable=False),
        sa.Column("reviewer", sa.String(length=255), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("candidate_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("reviewed_claim_json", sa.JSON(), nullable=False),
        sa.Column("scientific_claim_id", sa.String(length=36), nullable=True),
        sa.Column("relationship_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"]),
        sa.ForeignKeyConstraint(["scientific_claim_id"], ["scientific_claims.id"]),
        sa.ForeignKeyConstraint(["relationship_id"], ["relationships.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "investigation_id",
            "candidate_id",
            name="uq_scientific_claim_candidate_review",
        ),
    )
    for column in (
        "investigation_id",
        "candidate_id",
        "decision",
        "scientific_claim_id",
        "relationship_id",
    ):
        op.create_index(
            f"ix_scientific_claim_candidate_reviews_{column}",
            "scientific_claim_candidate_reviews",
            [column],
        )


def downgrade() -> None:
    op.drop_table("scientific_claim_candidate_reviews")
