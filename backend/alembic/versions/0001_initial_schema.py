"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-21
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def lifecycle() -> list[sa.Column]:
    return [
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    op.create_table("brands", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(64), nullable=False), sa.Column("name", sa.String(128), nullable=False), sa.Column("source_name", sa.String(255), nullable=False), *lifecycle(), *timestamps())
    op.create_index("ix_brands_code", "brands", ["code"], unique=True)
    op.create_index("ix_brands_status", "brands", ["status"])

    op.create_table("product_types", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(64), nullable=False), sa.Column("name", sa.String(128), nullable=False), *lifecycle(), *timestamps())
    op.create_index("ix_product_types_code", "product_types", ["code"], unique=True)
    op.create_index("ix_product_types_status", "product_types", ["status"])

    op.create_table("spec_groups", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(64), nullable=False), sa.Column("name", sa.String(128), nullable=False), sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"), *timestamps())
    op.create_index("ix_spec_groups_code", "spec_groups", ["code"], unique=True)

    op.create_table("api_clients", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(128), nullable=False), sa.Column("key_hash", sa.String(128), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), *timestamps())
    op.create_index("ix_api_clients_name", "api_clients", ["name"], unique=True)
    op.create_index("ix_api_clients_key_hash", "api_clients", ["key_hash"], unique=True)

    op.create_table("series", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id"), nullable=False), sa.Column("product_type_id", sa.Integer(), sa.ForeignKey("product_types.id"), nullable=False), sa.Column("name", sa.String(255), nullable=False), *lifecycle(), *timestamps(), sa.UniqueConstraint("brand_id", "product_type_id", "name", name="uq_series_brand_type_name"))
    op.create_index("ix_series_brand_id", "series", ["brand_id"])
    op.create_index("ix_series_product_type_id", "series", ["product_type_id"])
    op.create_index("ix_series_status", "series", ["status"])

    op.create_table("models", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id"), nullable=False), sa.Column("product_type_id", sa.Integer(), sa.ForeignKey("product_types.id"), nullable=False), sa.Column("series_id", sa.Integer(), sa.ForeignKey("series.id"), nullable=False), sa.Column("model_name", sa.String(255), nullable=False), sa.Column("title", sa.String(512), nullable=False, server_default=""), sa.Column("platform_vendor", sa.String(64), nullable=True), sa.Column("generation", sa.String(64), nullable=True), sa.Column("source_ref", sa.String(255), nullable=False), sa.Column("raw_source_id", sa.String(512), nullable=True), *lifecycle(), *timestamps(), sa.UniqueConstraint("brand_id", "model_name", name="uq_model_brand_name"))
    op.create_index("ix_models_brand_id", "models", ["brand_id"])
    op.create_index("ix_models_product_type_id", "models", ["product_type_id"])
    op.create_index("ix_models_series_id", "models", ["series_id"])
    op.create_index("ix_models_model_name", "models", ["model_name"])
    op.create_index("ix_models_status", "models", ["status"])

    op.create_table("spec_definitions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("group_id", sa.Integer(), sa.ForeignKey("spec_groups.id"), nullable=False), sa.Column("field_key", sa.String(128), nullable=False), sa.Column("label", sa.String(128), nullable=False), sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"), *timestamps(), sa.UniqueConstraint("field_key", name="uq_spec_field_key"))
    op.create_index("ix_spec_definitions_group_id", "spec_definitions", ["group_id"])
    op.create_index("ix_spec_definitions_field_key", "spec_definitions", ["field_key"])

    op.create_table("model_spec_values", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("model_id", sa.Integer(), sa.ForeignKey("models.id"), nullable=False), sa.Column("spec_definition_id", sa.Integer(), sa.ForeignKey("spec_definitions.id"), nullable=False), sa.Column("value", sa.Text(), nullable=False), sa.Column("raw_label", sa.String(255), nullable=False), sa.Column("raw_value", sa.Text(), nullable=False), sa.Column("source_ref", sa.String(255), nullable=False), sa.Column("confidence", sa.String(32), nullable=False, server_default="source"), *timestamps(), sa.UniqueConstraint("model_id", "spec_definition_id", name="uq_model_spec"))
    op.create_index("ix_model_spec_values_model_id", "model_spec_values", ["model_id"])
    op.create_index("ix_model_spec_values_spec_definition_id", "model_spec_values", ["spec_definition_id"])

    op.create_table("audit_logs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("api_client_id", sa.Integer(), sa.ForeignKey("api_clients.id"), nullable=True), sa.Column("action", sa.String(64), nullable=False), sa.Column("entity_type", sa.String(64), nullable=False), sa.Column("entity_id", sa.Integer(), nullable=True), sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")), *timestamps())
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])


def downgrade() -> None:
    for table in ["audit_logs", "model_spec_values", "spec_definitions", "models", "series", "api_clients", "spec_groups", "product_types", "brands"]:
        op.drop_table(table)
