"""cpu compatibility evidence

Revision ID: 0002_cpu_compatibility
Revises: 0001_initial_schema
Create Date: 2026-07-21 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_cpu_compatibility"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def timestamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "cpu_compatibility",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("server_model", sa.String(128), nullable=False),
        sa.Column("server_id", sa.String(64), nullable=False),
        sa.Column("config_code", sa.String(255), nullable=False),
        sa.Column("config_id", sa.String(64), nullable=False),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("cpu_option_id", sa.String(128), nullable=False),
        sa.Column("cpu_option_raw", sa.String(255), nullable=False),
        sa.Column("cpu_display", sa.String(255), nullable=False),
        sa.Column("cpu_spec", sa.String(255), nullable=False),
        sa.Column("source_url", sa.String(512), nullable=False),
        sa.Column("collected_date", sa.String(32), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("server_model", "config_id", "cpu_option_id", name="uq_cpu_compatibility_row"),
    )
    op.create_index("ix_cpu_compatibility_server_model", "cpu_compatibility", ["server_model"])
    op.create_index("ix_cpu_compatibility_config_id", "cpu_compatibility", ["config_id"])


def downgrade() -> None:
    op.drop_index("ix_cpu_compatibility_config_id", table_name="cpu_compatibility")
    op.drop_index("ix_cpu_compatibility_server_model", table_name="cpu_compatibility")
    op.drop_table("cpu_compatibility")
