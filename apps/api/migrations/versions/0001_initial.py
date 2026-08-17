"""Initial YetSee Sprint 1 schema."""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(120)),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "observations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("source_ref", sa.String(500)),
        sa.Column("topic", sa.String(255)),
        sa.Column("metric", sa.String(120), nullable=False),
        sa.Column("value", sa.Float()),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("content_hash"),
    )
    op.create_index("ix_observations_source", "observations", ["source"])
    op.create_index("ix_observations_topic", "observations", ["topic"])
    op.create_index("ix_observations_observed_at", "observations", ["observed_at"])
    op.create_index("ix_observations_content_hash", "observations", ["content_hash"], unique=True)

    op.create_table(
        "signals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("observation_id", sa.String(36), sa.ForeignKey("observations.id"), nullable=False),
        sa.Column("kind", sa.String(80), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("strength", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("detector", sa.String(120), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_signals_observation_id", "signals", ["observation_id"])
    op.create_index("ix_signals_kind", "signals", ["kind"])
    op.create_index("ix_signals_subject", "signals", ["subject"])

    op.create_table(
        "entities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("kind", sa.String(80), nullable=False),
        sa.Column("canonical_name", sa.String(255), nullable=False),
        sa.Column("canonical_key", sa.String(320), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("canonical_key"),
    )
    op.create_index("ix_entities_kind", "entities", ["kind"])
    op.create_index("ix_entities_canonical_name", "entities", ["canonical_name"])
    op.create_index("ix_entities_canonical_key", "entities", ["canonical_key"], unique=True)

    op.create_table(
        "relationships",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_entity_id", sa.String(36), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("target_entity_id", sa.String(36), sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("kind", sa.String(100), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_relationships_source_entity_id", "relationships", ["source_entity_id"])
    op.create_index("ix_relationships_target_entity_id", "relationships", ["target_entity_id"])
    op.create_index("ix_relationships_kind", "relationships", ["kind"])

    op.create_table(
        "investigations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("hypothesis", sa.Text()),
        sa.Column("counter_thesis", sa.Text()),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_investigations_title", "investigations", ["title"])
    op.create_index("ix_investigations_slug", "investigations", ["slug"], unique=True)
    op.create_index("ix_investigations_status", "investigations", ["status"])

    op.create_table(
        "evidence_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("investigation_id", sa.String(36), sa.ForeignKey("investigations.id"), nullable=False),
        sa.Column("observation_id", sa.String(36), sa.ForeignKey("observations.id")),
        sa.Column("signal_id", sa.String(36), sa.ForeignKey("signals.id")),
        sa.Column("stance", sa.String(24), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evidence_links_investigation_id", "evidence_links", ["investigation_id"])
    op.create_index("ix_evidence_links_observation_id", "evidence_links", ["observation_id"])
    op.create_index("ix_evidence_links_signal_id", "evidence_links", ["signal_id"])

    op.create_table(
        "opportunities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("investigation_id", sa.String(36), sa.ForeignKey("investigations.id"), nullable=False),
        sa.Column("kind", sa.String(60), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("thesis", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("stage", sa.String(40), nullable=False),
        sa.Column("reasoning", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_opportunities_investigation_id", "opportunities", ["investigation_id"])
    op.create_index("ix_opportunities_kind", "opportunities", ["kind"])


def downgrade() -> None:
    op.drop_table("opportunities")
    op.drop_table("evidence_links")
    op.drop_table("investigations")
    op.drop_table("relationships")
    op.drop_table("entities")
    op.drop_table("signals")
    op.drop_table("observations")
    op.drop_table("users")
