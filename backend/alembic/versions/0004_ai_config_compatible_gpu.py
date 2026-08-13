"""add ai config and compatible gpu links

Revision ID: 0004_ai_config_compatible_gpu
Revises: 0003_gpu_slot_cooling
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_ai_config_compatible_gpu"
down_revision = "0003_gpu_slot_cooling"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_compatible_gpus",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_id", sa.Integer(), sa.ForeignKey("models.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gpu_model_id", sa.Integer(), sa.ForeignKey("models.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_ref", sa.String(length=255), nullable=False, server_default="admin"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("model_id", "gpu_model_id", name="uq_model_compatible_gpu"),
    )
    op.create_index("ix_model_compatible_gpus_model_id", "model_compatible_gpus", ["model_id"])
    op.create_index("ix_model_compatible_gpus_gpu_model_id", "model_compatible_gpus", ["gpu_model_id"])
    op.create_table(
        "ai_provider_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=64), nullable=False, server_default="default"),
        sa.Column("base_url", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("api_key_cipher", sa.Text(), nullable=False, server_default=""),
        sa.Column("model", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("temperature", sa.String(length=32), nullable=False, server_default="0.2"),
        sa.Column("max_tokens", sa.Integer(), nullable=False, server_default="1200"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("name", name="uq_ai_provider_configs_name"),
    )
    op.create_index("ix_ai_provider_configs_name", "ai_provider_configs", ["name"])


def downgrade() -> None:
    op.drop_index("ix_ai_provider_configs_name", table_name="ai_provider_configs")
    op.drop_table("ai_provider_configs")
    op.drop_index("ix_model_compatible_gpus_gpu_model_id", table_name="model_compatible_gpus")
    op.drop_index("ix_model_compatible_gpus_model_id", table_name="model_compatible_gpus")
    op.drop_table("model_compatible_gpus")
