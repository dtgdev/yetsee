"""scientific decisions

Revision ID: 0014_scientific_decisions
Revises: 0013_investigation_missions
"""

from alembic import op
import sqlalchemy as sa

revision = "0014_scientific_decisions"
down_revision = "0013_investigation_missions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scientific_decisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("investigation_id", sa.String(length=36), nullable=False),
        sa.Column("mission_id", sa.String(length=36), nullable=False),
        sa.Column("synthesis_finding_id", sa.String(length=36), nullable=False),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("proposed_objective", sa.Text(), nullable=False),
        sa.Column("source_agent_ids", sa.JSON(), nullable=False),
        sa.Column("source_finding_ids", sa.JSON(), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("basis_json", sa.JSON(), nullable=False),
        sa.Column("next_mission_id", sa.String(length=36), nullable=True),
        sa.Column("command_id", sa.String(length=36), nullable=True),
        sa.Column("correlation_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"]),
        sa.ForeignKeyConstraint(["mission_id"], ["investigation_missions.id"]),
        sa.ForeignKeyConstraint(["synthesis_finding_id"], ["agent_findings.id"]),
        sa.ForeignKeyConstraint(["next_mission_id"], ["investigation_missions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("synthesis_finding_id", name="uq_scientific_decision_synthesis_finding"),
    )
    for column in ("investigation_id", "mission_id", "synthesis_finding_id", "action_type", "status", "priority", "next_mission_id", "command_id", "correlation_id"):
        op.create_index(f"ix_scientific_decisions_{column}", "scientific_decisions", [column])


def downgrade() -> None:
    op.drop_table("scientific_decisions")
