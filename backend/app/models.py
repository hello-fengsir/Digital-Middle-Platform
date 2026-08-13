from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Brand(Base, TimestampMixin):
    __tablename__ = "brands"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProductType(Base, TimestampMixin):
    __tablename__ = "product_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Series(Base, TimestampMixin):
    __tablename__ = "series"
    __table_args__ = (UniqueConstraint("brand_id", "product_type_id", "name", name="uq_series_brand_type_name"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), index=True)
    product_type_id: Mapped[int] = mapped_column(ForeignKey("product_types.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    brand: Mapped[Brand] = relationship()
    product_type: Mapped[ProductType] = relationship()


class Model(Base, TimestampMixin):
    __tablename__ = "models"
    __table_args__ = (CheckConstraint("lifecycle_status IN ('npi', 'rts', 'rtq', 'eos', 'eol')", name="ck_models_lifecycle_status"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), index=True)
    product_type_id: Mapped[int] = mapped_column(ForeignKey("product_types.id"), index=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"), index=True)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    platform_vendor: Mapped[str | None] = mapped_column(String(64))
    generation: Mapped[str | None] = mapped_column(String(64))
    source_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_source_id: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    lifecycle_status: Mapped[str | None] = mapped_column(String(16), nullable=True, default=None, server_default=None, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    brand: Mapped[Brand] = relationship()
    product_type: Mapped[ProductType] = relationship()
    series: Mapped[Series] = relationship()
    specs: Mapped[list["ModelSpecValue"]] = relationship(cascade="all, delete-orphan")
    business_tag_rows: Mapped[list["ModelBusinessTag"]] = relationship(cascade="all, delete-orphan")


class ModelBusinessTag(Base, TimestampMixin):
    __tablename__ = "model_business_tags"
    __table_args__ = (
        UniqueConstraint("model_id", "tag", name="uq_model_business_tag"),
        CheckConstraint("tag IN ('featured')", name="ck_model_business_tag_value"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id", ondelete="CASCADE"), index=True)
    tag: Mapped[str] = mapped_column(String(32), nullable=False, index=True)


class SpecGroup(Base, TimestampMixin):
    __tablename__ = "spec_groups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class SpecDefinition(Base, TimestampMixin):
    __tablename__ = "spec_definitions"
    __table_args__ = (UniqueConstraint("field_key", name="uq_spec_field_key"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("spec_groups.id"), index=True)
    field_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    group: Mapped[SpecGroup] = relationship()


class ModelSpecValue(Base, TimestampMixin):
    __tablename__ = "model_spec_values"
    __table_args__ = (UniqueConstraint("model_id", "spec_definition_id", name="uq_model_spec"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id"), index=True)
    spec_definition_id: Mapped[int] = mapped_column(ForeignKey("spec_definitions.id"), index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    raw_label: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_value: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="source")
    definition: Mapped[SpecDefinition] = relationship()




class ModelCompatibleGpu(Base, TimestampMixin):
    __tablename__ = "model_compatible_gpus"
    __table_args__ = (
        UniqueConstraint("model_id", "gpu_model_id", name="uq_model_compatible_gpu"),
        CheckConstraint("model_id <> gpu_model_id", name="ck_model_compatible_gpu_not_self"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id", ondelete="CASCADE"), index=True)
    gpu_model_id: Mapped[int] = mapped_column(ForeignKey("models.id", ondelete="CASCADE"), index=True)
    source_ref: Mapped[str] = mapped_column(String(255), nullable=False, default="admin")
    model: Mapped[Model] = relationship(foreign_keys=[model_id])
    gpu_model: Mapped[Model] = relationship(foreign_keys=[gpu_model_id])


class AiProviderConfig(Base, TimestampMixin):
    __tablename__ = "ai_provider_configs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, default="default", index=True)
    base_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    api_key_cipher: Mapped[str] = mapped_column(Text, nullable=False, default="")
    model: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    temperature: Mapped[str] = mapped_column(String(32), nullable=False, default="0.2")
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=1200)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class CpuCompatibility(Base, TimestampMixin):
    __tablename__ = "cpu_compatibility"
    __table_args__ = (UniqueConstraint("server_model", "config_id", "cpu_option_id", name="uq_cpu_compatibility_row"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    server_model: Mapped[str] = mapped_column(String(128), index=True)
    server_id: Mapped[str] = mapped_column(String(64), nullable=False)
    config_code: Mapped[str] = mapped_column(String(255), nullable=False)
    config_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    cpu_option_id: Mapped[str] = mapped_column(String(128), nullable=False)
    cpu_option_raw: Mapped[str] = mapped_column(String(255), nullable=False)
    cpu_display: Mapped[str] = mapped_column(String(255), nullable=False)
    cpu_spec: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    collected_date: Mapped[str] = mapped_column(String(32), nullable=False)


class ApiClient(Base, TimestampMixin):
    __tablename__ = "api_clients"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    key_hash: Mapped[str] = mapped_column(String(128), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    api_client_id: Mapped[int | None] = mapped_column(ForeignKey("api_clients.id"))
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
