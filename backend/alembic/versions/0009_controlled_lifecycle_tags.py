"""add controlled product lifecycle and business tags (public schema-only)

Revision ID: 0009_controlled_lifecycle_tags
Revises: 0008_nf5468a7_cn_notes

The private deployment copied legacy catalog values and seeded a featured tag. The
public release contains no production catalog, so this revision creates schema
only. Existing rows remain NULL/un-tagged until an operator explicitly supplies
its own authorized data.
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_controlled_lifecycle_tags"
down_revision = "0008_nf5468a7_cn_notes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("models", sa.Column("lifecycle_status", sa.String(16), nullable=True, server_default=sa.null()))
    op.create_index("ix_models_lifecycle_status", "models", ["lifecycle_status"])
    op.create_check_constraint(
        "ck_models_lifecycle_status", "models",
        "lifecycle_status IN ('npi', 'rts', 'rtq', 'eos', 'eol')",
    )
    op.create_table(
        "model_business_tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_id", sa.Integer(), sa.ForeignKey("models.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tag", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("model_id", "tag", name="uq_model_business_tag"),
        sa.CheckConstraint("tag IN ('featured')", name="ck_model_business_tag_value"),
    )
    op.create_index("ix_model_business_tags_model_id", "model_business_tags", ["model_id"])
    op.create_index("ix_model_business_tags_tag", "model_business_tags", ["tag"])


def downgrade() -> None:
    op.drop_table("model_business_tags")
    op.drop_constraint("ck_models_lifecycle_status", "models", type_="check")
    op.drop_index("ix_models_lifecycle_status", table_name="models")
    op.drop_column("models", "lifecycle_status")
