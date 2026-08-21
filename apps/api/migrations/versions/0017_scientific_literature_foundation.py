"""scientific literature evidence foundation

Revision ID: 0017_scientific_literature
Revises: 0016_scientific_memories
"""

from alembic import op
import sqlalchemy as sa

revision = "0017_scientific_literature"
down_revision = "0016_scientific_memories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scientific_publications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_system", sa.String(length=40), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("pmid", sa.String(length=32), nullable=True),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("journal", sa.String(length=255), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("authors_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("retrieval_ref", sa.String(length=1000), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_system", "source_id", name="uq_scientific_publication_source"),
        sa.UniqueConstraint("pmid"), sa.UniqueConstraint("doi"), sa.UniqueConstraint("content_hash"),
    )
    for column in ("source_system", "source_id", "pmid", "doi", "content_hash"):
        op.create_index(f"ix_scientific_publications_{column}", "scientific_publications", [column])

    op.create_table(
        "scientific_passages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("publication_id", sa.String(length=36), nullable=False),
        sa.Column("section", sa.String(length=120), nullable=True),
        sa.Column("locator", sa.String(length=255), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["publication_id"], ["scientific_publications.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("publication_id", "content_hash", name="uq_scientific_passage_publication_hash"),
    )
    op.create_index("ix_scientific_passages_publication_id", "scientific_passages", ["publication_id"])
    op.create_index("ix_scientific_passages_section", "scientific_passages", ["section"])
    op.create_index("ix_scientific_passages_content_hash", "scientific_passages", ["content_hash"])

    op.create_table(
        "scientific_claims",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("publication_id", sa.String(length=36), nullable=False),
        sa.Column("passage_id", sa.String(length=36), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.String(length=40), nullable=False),
        sa.Column("extraction_method", sa.String(length=80), nullable=False),
        sa.Column("extraction_version", sa.String(length=80), nullable=True),
        sa.Column("extraction_json", sa.JSON(), nullable=False),
        sa.Column("canonical_evidence", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["publication_id"], ["scientific_publications.id"]),
        sa.ForeignKeyConstraint(["passage_id"], ["scientific_passages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scientific_claims_publication_id", "scientific_claims", ["publication_id"])
    op.create_index("ix_scientific_claims_passage_id", "scientific_claims", ["passage_id"])

    op.add_column("evidence_links", sa.Column("scientific_passage_id", sa.String(length=36), nullable=True))
    op.add_column("evidence_links", sa.Column("scientific_claim_id", sa.String(length=36), nullable=True))
    op.create_foreign_key("fk_evidence_links_scientific_passage", "evidence_links", "scientific_passages", ["scientific_passage_id"], ["id"])
    op.create_foreign_key("fk_evidence_links_scientific_claim", "evidence_links", "scientific_claims", ["scientific_claim_id"], ["id"])
    op.create_index("ix_evidence_links_scientific_passage_id", "evidence_links", ["scientific_passage_id"])
    op.create_index("ix_evidence_links_scientific_claim_id", "evidence_links", ["scientific_claim_id"])


def downgrade() -> None:
    op.drop_index("ix_evidence_links_scientific_claim_id", table_name="evidence_links")
    op.drop_index("ix_evidence_links_scientific_passage_id", table_name="evidence_links")
    op.drop_constraint("fk_evidence_links_scientific_claim", "evidence_links", type_="foreignkey")
    op.drop_constraint("fk_evidence_links_scientific_passage", "evidence_links", type_="foreignkey")
    op.drop_column("evidence_links", "scientific_claim_id")
    op.drop_column("evidence_links", "scientific_passage_id")
    op.drop_table("scientific_claims")
    op.drop_table("scientific_passages")
    op.drop_table("scientific_publications")
