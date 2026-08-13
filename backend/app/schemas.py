from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError


class ApiSchema(BaseModel):
    model_config = ConfigDict(protected_namespaces=())


class BrandOut(ApiSchema):
    id: int
    code: str
    name: str
    source_name: str
    model_count: int = 0


class ProductTypeOut(ApiSchema):
    id: int
    code: str
    name: str


class SeriesOut(ApiSchema):
    id: int
    brand_code: str
    product_type: str
    name: str
    model_count: int


LifecycleStatus = Literal["npi", "rts", "rtq", "eos", "eol"]
BusinessTag = Literal["featured"]


class ModelBadge(ApiSchema):
    kind: Literal["lifecycle", "business"]
    code: str
    label: str


class ModelSummary(ApiSchema):
    id: int
    brand_code: str
    brand_name: str
    product_type: str
    series: str
    model_name: str
    title: str
    platform_vendor: str | None = None
    generation: str | None = None
    status: str = "active"
    deleted_at: datetime | None = None
    lifecycle_status: LifecycleStatus | None = None
    business_tags: list[BusinessTag] = []
    badges: list[ModelBadge] = []
    gpu_slot_width: str | None = None
    gpu_cooling_type: str | None = None




class CompatibleGpuOut(ApiSchema):
    id: int
    model_name: str
    title: str = ""
    brand_code: str
    product_type: str
    series: str
    memory: str | None = None
    display_name: str


class SpecValueOut(ApiSchema):
    group_code: str
    group_name: str
    field_key: str
    label: str
    value: str
    raw_label: str
    source_ref: str
    confidence: str


class SpecFieldOut(ApiSchema):
    id: int
    field_key: str
    label: str
    sort_order: int


class SpecGroupOut(ApiSchema):
    id: int
    code: str
    name: str
    sort_order: int
    fields: list[SpecFieldOut] = []


class SpecDefinitionOut(ApiSchema):
    id: int
    group_id: int
    group_code: str
    group_name: str
    field_key: str
    label: str
    sort_order: int


class SpecDefinitionPatch(ApiSchema):
    group_id: int | None = None
    group_code: str | None = None
    label: str | None = None
    sort_order: int | None = None


class ModelDetail(ModelSummary):
    source_ref: str
    raw_source_id: str | None = None
    specifications: list[SpecValueOut] = []
    compatible_gpus: list[CompatibleGpuOut] = []


class SpecInput(ApiSchema):
    field_key: str = Field(min_length=1)

    @field_validator("field_key")
    @classmethod
    def normalize_field_key(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field_key must not be empty")
        return value
    label: str
    group: str = "其他"
    group_id: int | None = None
    group_code: str | None = None
    sort_order: int | None = None
    value: str
    raw_label: str | None = None
    source_ref: str = "api"


class ModelWrite(ApiSchema):
    @model_validator(mode="before")
    @classmethod
    def reject_explicit_null_lifecycle(cls, value: Any) -> Any:
        if isinstance(value, dict) and "lifecycle_status" in value and value["lifecycle_status"] is None:
            raise PydanticCustomError("lifecycle_status", "lifecycle_status must be one of npi, rts, rtq, eos, eol when provided")
        return value

    brand_code: str = Field(min_length=1)
    brand_name: str | None = None
    product_type: str = Field(min_length=1)
    series: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    title: str = ""
    platform_vendor: str | None = None
    generation: str | None = None
    source_ref: str = "api"
    raw_source_id: str | None = None
    specifications: list[SpecInput] = []
    compatible_gpu_ids: list[int] = []
    lifecycle_status: LifecycleStatus | None = None
    business_tags: list[BusinessTag] = []


class CompatibleGpuWrite(ApiSchema):
    model_config = ConfigDict(extra="forbid")
    compatible_gpu_ids: list[int] = Field(default_factory=list)


class ModelPatch(ApiSchema):
    @model_validator(mode="before")
    @classmethod
    def reject_explicit_null_lifecycle(cls, value: Any) -> Any:
        if isinstance(value, dict) and "lifecycle_status" in value and value["lifecycle_status"] is None:
            raise PydanticCustomError("lifecycle_status", "lifecycle_status must be one of npi, rts, rtq, eos, eol when provided")
        return value

    brand_code: str | None = None
    brand_name: str | None = None
    product_type: str | None = None
    series: str | None = None
    model_name: str | None = None
    title: str | None = None
    platform_vendor: str | None = None
    generation: str | None = None
    source_ref: str | None = None
    raw_source_id: str | None = None
    status: str | None = None
    specifications: list[SpecInput] | None = None
    compatible_gpu_ids: list[int] | None = None
    lifecycle_status: LifecycleStatus | None = None
    business_tags: list[BusinessTag] | None = None


class ImportPreviewRow(ApiSchema):
    row_number: int
    brand_code: str
    brand_name: str
    product_type: str
    series: str
    model_name: str
    title: str
    platform_vendor: str | None = None
    generation: str | None = None
    source_ref: str
    raw_source_id: str | None = None


class ImportPreviewSpecRow(ApiSchema):
    row_number: int
    model_name: str
    field_group: str
    field_label: str
    field_key: str
    value: str
    source_ref: str


class MarkdownImportIn(ApiSchema):
    raw_text: str = Field(min_length=1, max_length=2000)


class ImportPreviewOut(ApiSchema):
    total_rows: int
    valid_rows: int
    invalid_rows: int
    errors: list[str] = []
    rows: list[ImportPreviewRow] = []
    sheet_rows: list[ImportPreviewSpecRow] = []


class SpecRecognitionPreviewIn(ApiSchema):
    raw_text: str = Field(min_length=1, max_length=2000)
    brand_code: str | None = None
    product_type: str | None = None
    series: str | None = None
    model_name: str | None = None


class SpecRecognitionPreviewItem(ApiSchema):
    raw_label: str
    value: str
    matched_field_key: str | None = None
    matched_label: str | None = None
    group_code: str | None = None
    group_name: str | None = None
    confidence: float
    note: str


class SpecRecognitionPreviewOut(ApiSchema):
    items: list[SpecRecognitionPreviewItem] = []


class HealthOut(ApiSchema):
    status: str


class AdminLoginIn(ApiSchema):
    username: str
    password: str


class AdminSessionOut(ApiSchema):
    token: str
    username: str
    expires_at: str


class AdminMeOut(ApiSchema):
    username: str
    expires_at: str


class AiConfigOut(ApiSchema):
    base_url: str = ""
    model: str = ""
    temperature: float = 0.2
    max_tokens: int = 1200
    enabled: bool = False
    has_api_key: bool = False


class AiConfigIn(ApiSchema):
    base_url: str = ""
    api_key: str | None = None
    model: str = ""
    temperature: float = 0.2
    max_tokens: int = 1200
    enabled: bool = False


class AiConfigTestIn(ApiSchema):
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None


class AiAgentRuleIn(ApiSchema):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=20000)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        if "\x00" in value:
            raise PydanticCustomError("ai_agent_rule_nul", "content must not contain NUL")
        if not value.strip():
            raise PydanticCustomError("ai_agent_rule_blank", "content must not be blank")
        return value


class AiAgentRuleOut(ApiSchema):
    content: str
    sha256: str
    updated_at: datetime | None = None
    source: Literal["runtime", "default"]


class AiRecommendIn(ApiSchema):
    message: str = Field(min_length=1, max_length=2000)
    brand_code: str | None = None


class AiHardCondition(ApiSchema):
    id: str
    kind: str
    operator: str
    value: Any
    unit: str | None = None
    width: Literal["double", "single"] | None = None
    generation: int | None = None
    lanes: int | None = None
    label: str


class AiConditionResult(ApiSchema):
    condition_id: str
    kind: str
    label: str
    satisfied: bool
    status: Literal["satisfied", "unsatisfied", "unknown"]
    verification_status: Literal["confirmed", "conflict", "unknown"]
    generation: int | None = None
    lanes: int | None = None
    actual: Any = None
    evidence: str | None = None


class AiBrandCoverage(ApiSchema):
    brand_code: str
    brand_name: str
    status: Literal["covered", "uncovered"]
    candidate_count: int = 0
    message: str


class AiCoverage(ApiSchema):
    requested_brands: list[str] = []
    covered_brands: list[str] = []
    uncovered_brands: list[str] = []
    brand_results: list[AiBrandCoverage] = []


class AiRecommendModel(ApiSchema):
    id: int
    model_name: str
    brand_code: str
    brand_name: str
    product_type: str
    series: str
    reason: str = ""
    evidence: list[str] = []
    fully_matched: bool = False
    condition_results: list[AiConditionResult] = []


class AiRecommendOut(ApiSchema):
    answer: str
    models: list[AiRecommendModel] = []
    source: str = "local"
    warning: str | None = None
    provenance: Literal["ai_used_with_evidence", "ai_used_no_evidence_refusal", "ai_provider_failed", "ai_not_available"] = "ai_not_available"
    match_status: Literal["matched", "partial_match", "no_match"] = "no_match"
    hard_conditions: list[AiHardCondition] = []
    coverage: AiCoverage = AiCoverage()
    selected_model_ids: list[int] = []
    # 新字段可选，旧客户端继续只读 match_status/models。
    match_basis: Literal["hard_conditions", "catalog_match", "none"] = "none"
    catalog_match: bool = False
    unparsed_conditions: list[str] = []
