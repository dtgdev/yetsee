"""scientific resolutions

Revision ID: 0015_scientific_resolutions
Revises: 0014_scientific_decisions
"""

from alembic import op
import sqlalchemy as sa

revision = "0015_scientific_resolutions"
down_revision = "0014_scientific_decisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scientific_resolutions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("investigation_id", sa.String(length=36), nullable=False),
        sa.Column("decision_id", sa.String(length=36), nullable=False),
        sa.Column("parent_mission_id", sa.String(length=36), nullable=False),
        sa.Column("followup_mission_id", sa.String(length=36), nullable=False),
        sa.Column("parent_synthesis_finding_id", sa.String(length=36), nullable=False),
        sa.Column("followup_synthesis_finding_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("objective_satisfied", sa.Boolean(), nullable=False),
        sa.Column("resolution_score", sa.Float(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("before_json", sa.JSON(), nullable=False),
        sa.Column("after_json", sa.JSON(), nullable=False),
        sa.Column("delta_json", sa.JSON(), nullable=False),
        sa.Column("evidence_added_ids", sa.JSON(), nullable=False),
        sa.Column("evidence_removed_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"]),
        sa.ForeignKeyConstraint(["decision_id"], ["scientific_decisions.id"]),
        sa.ForeignKeyConstraint(["parent_mission_id"], ["investigation_missions.id"]),
        sa.ForeignKeyConstraint(["followup_mission_id"], ["investigation_missions.id"]),
        sa.ForeignKeyConstraint(["parent_synthesis_finding_id"], ["agent_findings.id"]),
        sa.ForeignKeyConstraint(["followup_synthesis_finding_id"], ["agent_findings.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("decision_id", name="uq_scientific_resolution_decision"),
    )
    for column in ("investigation_id", "decision_id", "parent_mission_id", "followup_mission_id", "parent_synthesis_finding_id", "followup_synthesis_finding_id", "status"):
        op.create_index(f"ix_scientific_resolutions_{column}", "scientific_resolutions", [column])


def downgrade() -> None:
    op.drop_table("scientific_resolutions")
