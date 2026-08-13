"""add controlled product lifecycle and business tags

Revision ID: 0009_controlled_lifecycle_tags
Revises: 0008_nf5468a7_cn_notes
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_controlled_lifecycle_tags"
down_revision = "0008_nf5468a7_cn_notes"
branch_labels = None
depends_on = None

# Formal dump/source-spec count closure expected by the bounded migration.
LEGACY_LIFECYCLE_EXPECTED_COUNTS = {"npi": 22, "rts": 41, "rtq": 8, "eos": 17, "eol": 2}


def upgrade() -> None:
    # Unknown is represented by SQL NULL.  Do not invent RTS for rows without
    # explicit legacy specification evidence.
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

    # Preserve the existing lifecycle_status spec as provenance/legacy compatibility;
    # copy only its five explicitly known source strings into the governed column.
    op.execute("""
        UPDATE models m
           SET lifecycle_status = CASE trim(v.value)
               WHEN 'NPI (新产品导入)' THEN 'npi'
               WHEN 'RTS（可销售）' THEN 'rts'
               WHEN 'RTQ（可报价）' THEN 'rtq'
               WHEN 'EOS（停止接单）' THEN 'eos'
               WHEN 'EOL（生命周期终止）' THEN 'eol'
               ELSE NULL
           END
          FROM model_spec_values v
          JOIN spec_definitions d ON d.id = v.spec_definition_id
         WHERE v.model_id = m.id
           AND d.field_key = 'lifecycle_status'
           AND trim(v.value) IN (
               'NPI (新产品导入)', 'RTS（可销售）', 'RTQ（可报价）',
               'EOS（停止接单）', 'EOL（生命周期终止）'
           )
    """)
    # Explicit evidence only: the exact observed HW5345 catalog name contains 主推最优.
    op.execute("""
        INSERT INTO model_business_tags (model_id, tag)
        SELECT id, 'featured'
          FROM models
         WHERE model_name = 'HW5345 塔式工作站（主推最优）'
        ON CONFLICT (model_id, tag) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_table("model_business_tags")
    op.drop_constraint("ck_models_lifecycle_status", "models", type_="check")
    op.drop_index("ix_models_lifecycle_status", table_name="models")
    op.drop_column("models", "lifecycle_status")
