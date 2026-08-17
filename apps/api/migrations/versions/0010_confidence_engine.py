"""Confidence Engine: deterministic hypothesis confidence history.

Revision ID: 0010_confidence_engine
Revises: 0009_living_investigation
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_confidence_engine"
down_revision = "0009_living_investigation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("hypotheses", sa.Column("prior_confidence", sa.Float(), nullable=True))
    op.execute("UPDATE hypotheses SET prior_confidence = confidence WHERE prior_confidence IS NULL")
    op.alter_column("hypotheses", "prior_confidence", nullable=False)

    op.create_table(
        "hypothesis_confidence_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("hypothesis_id", sa.String(36), sa.ForeignKey("hypotheses.id"), nullable=False),
        sa.Column("old_confidence", sa.Float(), nullable=False),
        sa.Column("new_confidence", sa.Float(), nullable=False),
        sa.Column("prior_confidence", sa.Float(), nullable=False),
        sa.Column("supporting_weight", sa.Float(), nullable=False),
        sa.Column("contradicting_weight", sa.Float(), nullable=False),
        sa.Column("neutral_weight", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("trigger", sa.String(80), nullable=False),
        sa.Column("observation_id", sa.String(36), sa.ForeignKey("observations.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_hypothesis_confidence_history_hypothesis_id", "hypothesis_confidence_history", ["hypothesis_id"])
    op.create_index("ix_hypothesis_confidence_history_trigger", "hypothesis_confidence_history", ["trigger"])
    op.create_index("ix_hypothesis_confidence_history_observation_id", "hypothesis_confidence_history", ["observation_id"])


def downgrade() -> None:
    op.drop_table("hypothesis_confidence_history")
    op.drop_column("hypotheses", "prior_confidence")
