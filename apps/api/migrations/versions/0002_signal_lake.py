"""Signal Lake connector run and state tables.

Revision ID: 0002_signal_lake
Revises: 0001_initial
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_signal_lake"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connector_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("connector_id", sa.String(120), nullable=False),
        sa.Column("connector_version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("fetched_count", sa.Integer(), nullable=False),
        sa.Column("accepted_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("cursor_before", sa.Text()),
        sa.Column("cursor_after", sa.Text()),
        sa.Column("error", sa.Text()),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_connector_runs_connector_id", "connector_runs", ["connector_id"])
    op.create_index("ix_connector_runs_status", "connector_runs", ["status"])

    op.create_table(
        "connector_states",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("connector_id", sa.String(120), nullable=False),
        sa.Column("cursor", sa.Text()),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_error_at", sa.DateTime(timezone=True)),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("state_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("connector_id"),
    )
    op.create_index("ix_connector_states_connector_id", "connector_states", ["connector_id"], unique=True)


def downgrade() -> None:
    op.drop_table("connector_states")
    op.drop_table("connector_runs")
