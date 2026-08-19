"""scientific memories

Revision ID: 0016_scientific_memories
Revises: 0015_scientific_resolutions
"""

from alembic import op
import sqlalchemy as sa

revision = "0016_scientific_memories"
down_revision = "0015_scientific_resolutions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scientific_memories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("investigation_id", sa.String(length=36), nullable=False),
        sa.Column("resolution_id", sa.String(length=36), nullable=False),
        sa.Column("decision_id", sa.String(length=36), nullable=False),
        sa.Column("parent_mission_id", sa.String(length=36), nullable=False),
        sa.Column("followup_mission_id", sa.String(length=36), nullable=False),
        sa.Column("memory_type", sa.String(length=100), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("compiler_version", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("lesson_json", sa.JSON(), nullable=False),
        sa.Column("source_synthesis_finding_ids", sa.JSON(), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"]),
        sa.ForeignKeyConstraint(["resolution_id"], ["scientific_resolutions.id"]),
        sa.ForeignKeyConstraint(["decision_id"], ["scientific_decisions.id"]),
        sa.ForeignKeyConstraint(["parent_mission_id"], ["investigation_missions.id"]),
        sa.ForeignKeyConstraint(["followup_mission_id"], ["investigation_missions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resolution_id", name="uq_scientific_memory_resolution"),
    )
    for column in ("investigation_id", "resolution_id", "decision_id", "parent_mission_id", "followup_mission_id", "memory_type", "outcome"):
        op.create_index(f"ix_scientific_memories_{column}", "scientific_memories", [column])


def downgrade() -> None:
    op.drop_table("scientific_memories")
