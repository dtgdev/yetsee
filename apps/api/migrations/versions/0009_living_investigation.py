"""Living Investigation Runtime: hypotheses and directional evidence.

Revision ID: 0009_living_investigation
Revises: 0008_yetsee_os_kernel
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_living_investigation"
down_revision = "0008_yetsee_os_kernel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hypotheses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("investigation_id", sa.String(36), sa.ForeignKey("investigations.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_by_type", sa.String(40), nullable=False),
        sa.Column("created_by_id", sa.String(120)),
        sa.Column("supersedes_id", sa.String(36), sa.ForeignKey("hypotheses.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_hypotheses_investigation_id", "hypotheses", ["investigation_id"])
    op.create_index("ix_hypotheses_status", "hypotheses", ["status"])
    op.create_index("ix_hypotheses_supersedes_id", "hypotheses", ["supersedes_id"])

    op.create_table(
        "hypothesis_evidence_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("hypothesis_id", sa.String(36), sa.ForeignKey("hypotheses.id"), nullable=False),
        sa.Column("observation_id", sa.String(36), sa.ForeignKey("observations.id"), nullable=False),
        sa.Column("stance", sa.String(24), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("hypothesis_id", "observation_id", "stance", name="uq_hypothesis_evidence_stance"),
    )
    op.create_index("ix_hypothesis_evidence_links_hypothesis_id", "hypothesis_evidence_links", ["hypothesis_id"])
    op.create_index("ix_hypothesis_evidence_links_observation_id", "hypothesis_evidence_links", ["observation_id"])
    op.create_index("ix_hypothesis_evidence_links_stance", "hypothesis_evidence_links", ["stance"])


def downgrade() -> None:
    op.drop_table("hypothesis_evidence_links")
    op.drop_table("hypotheses")
