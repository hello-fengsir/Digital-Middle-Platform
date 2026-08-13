import re

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session

from app.catalog import active_models_query, compatible_gpus_for_model, model_to_summary, spec_definition_to_dict, spec_definitions_query, specs_for_model
from app.db import get_db
from app.models import Brand, CpuCompatibility, Model, ModelSpecValue, ProductType, Series, SpecDefinition
from app.model_matching import rank_model_rows
from app.schemas import AiRecommendIn, AiRecommendOut, BrandOut, HealthOut, ModelDetail, ModelSummary, ProductTypeOut, SeriesOut, SpecDefinitionOut

router = APIRouter(prefix="/api/v1")


@router.get("/health", response_model=HealthOut)
def health() -> dict:
    return {"status": "ok"}


@router.get("/brands", response_model=list[BrandOut])
def brands(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(Brand, func.count(Model.id))
        .outerjoin(Model, (Model.brand_id == Brand.id) & (Model.status == "active") & (Model.deleted_at.is_(None)))
        .where(Brand.deleted_at.is_(None), Brand.status == "active")
        .group_by(Brand.id)
    ).all()
    brand_order = {"generic": 0, "generic": 0, "inspur": 10, "lenovo": 20, "dell": 30, "accessory": 40}
    rows = sorted(rows, key=lambda row: (brand_order.get(row[0].code.lower(), 100), row[0].id))
    return [{"id": b.id, "code": b.code, "name": b.name, "source_name": b.source_name, "model_count": c} for b, c in rows]


@router.get("/product-types", response_model=list[ProductTypeOut])
def product_types(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(ProductType).where(ProductType.deleted_at.is_(None), ProductType.status == "active").order_by(ProductType.name)).all()
    return [{"id": row.id, "code": row.code, "name": row.name} for row in rows]


@router.get("/spec-definitions", response_model=list[SpecDefinitionOut])
def spec_definitions(db: Session = Depends(get_db)) -> list[dict]:
    return [spec_definition_to_dict(spec, group) for spec, group in db.execute(spec_definitions_query()).all()]


@router.get("/series", response_model=list[SeriesOut])
def series(brand: str | None = None, product_type: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    stmt = (
        select(Series, Brand, ProductType, func.count(Model.id))
        .join(Brand, Series.brand_id == Brand.id)
        .join(ProductType, Series.product_type_id == ProductType.id)
        .outerjoin(Model, (Model.series_id == Series.id) & (Model.status == "active") & (Model.deleted_at.is_(None)))
        .where(
            Series.deleted_at.is_(None),
            Series.status == "active",
            Brand.deleted_at.is_(None),
            Brand.status == "active",
            ProductType.deleted_at.is_(None),
            ProductType.status == "active",
        )
        .group_by(Series.id, Brand.id, ProductType.id)
        .order_by(ProductType.name, Series.name)
    )
    if brand:
        stmt = stmt.where(func.lower(Brand.code) == brand.lower())
    if product_type:
        stmt = stmt.where(or_(ProductType.name == product_type, ProductType.code == product_type))
    rows = db.execute(stmt).all()
    return [{"id": s.id, "brand_code": b.code, "product_type": pt.name, "name": s.name, "model_count": c} for s, b, pt, c in rows]


def _keyword_terms(keyword: str) -> list[str]:
    return [term for term in keyword.replace("，", " ").replace("、", " ").replace(",", " ").split() if term]


SEARCH_EXCLUDED_FIELDS = {"cpu_notes", "selection_notes"}
NEGATIVE_SEARCH_MARKERS = ("不可混用", "不引用", "未确认", "不做推断", "不可作为", "相近型号")


def _normalized_search_token(value: str) -> str:
    return re.sub(r"[^A-Z0-9\u4e00-\u9fff]", "", str(value or "").upper())


def _model_like_term(value: str) -> bool:
    token = _normalized_search_token(value)
    return bool(re.search(r"[A-Z]", token) and re.search(r"\d", token))


def _search_rank(db: Session, model: Model, terms: list[str]) -> tuple:
    """固定相关度层级：型号 > 标题/系列/类型 > 正向规格；最后以 ID 稳定排序。"""
    model_name = _normalized_search_token(model.model_name)
    metadata = " ".join((model.title or "", model.series.name, model.product_type.name)).lower()
    specs = specs_for_model(db, model.id)
    positive_specs = " ".join(
        f"{s.get('label', '')} {s.get('field_key', '')} {s.get('value', '')}"
        for s in specs
        if s.get("field_key") not in SEARCH_EXCLUDED_FIELDS
        and not any(marker in str(s.get("value", "")) for marker in NEGATIVE_SEARCH_MARKERS)
    ).lower()
    levels = []
    for term in terms:
        normalized = _normalized_search_token(term)
        lowered = term.lower()
        if normalized and model_name == normalized:
            levels.append(500)
        elif normalized and model_name.startswith(normalized):
            levels.append(400)
        elif normalized and normalized in model_name:
            levels.append(350)
        elif lowered in metadata:
            levels.append(250)
        elif lowered in positive_specs:
            levels.append(100)
        else:
            levels.append(50)
    return (-min(levels or [0]), -sum(levels), model.id)


def _positive_spec_match(term: str):
    like = f"%{term}%"
    clauses = [SpecDefinition.field_key.notin_(SEARCH_EXCLUDED_FIELDS)]
    if _model_like_term(term):
        clauses.extend(~ModelSpecValue.value.ilike(f"%{marker}%") for marker in NEGATIVE_SEARCH_MARKERS)
        clauses.extend(~ModelSpecValue.raw_value.ilike(f"%{marker}%") for marker in NEGATIVE_SEARCH_MARKERS)
    return (
        select(ModelSpecValue.id)
        .join(SpecDefinition, ModelSpecValue.spec_definition_id == SpecDefinition.id)
        .where(
            ModelSpecValue.model_id == Model.id,
            *clauses,
            or_(ModelSpecValue.value.ilike(like), ModelSpecValue.raw_value.ilike(like), ModelSpecValue.raw_label.ilike(like), SpecDefinition.label.ilike(like), SpecDefinition.field_key.ilike(like)),
        ).exists()
    )


def enrich_gpu_display_fields(db: Session, rows: list[dict]) -> list[dict]:
    ids = [row["id"] for row in rows if row.get("product_type") == "显卡"]
    if not ids:
        return rows
    spec_rows = db.execute(
        select(ModelSpecValue.model_id, SpecDefinition.field_key, ModelSpecValue.value)
        .join(SpecDefinition, ModelSpecValue.spec_definition_id == SpecDefinition.id)
        .where(ModelSpecValue.model_id.in_(ids), SpecDefinition.field_key.in_(["gpu_slot_width", "gpu_cooling_type"]))
    ).all()
    by_model: dict[int, dict[str, str]] = {}
    for model_id, field_key, value in spec_rows:
        by_model.setdefault(model_id, {})[field_key] = value
    for row in rows:
        values = by_model.get(row["id"], {})
        row["gpu_slot_width"] = values.get("gpu_slot_width")
        row["gpu_cooling_type"] = values.get("gpu_cooling_type")
    return rows


def _exact_model_rows(db: Session, query: str, brand: str | None) -> list[Model]:
    stmt = active_models_query().order_by(Model.id)
    if brand:
        stmt = stmt.join(Brand, Model.brand_id == Brand.id).where(func.lower(Brand.code) == brand.lower())
    rows = db.scalars(stmt).unique().all()
    return rank_model_rows(query, rows, lambda row: row.model_name, lambda row: row.id)


@router.get("/models", response_model=list[ModelSummary])
def models(brand: str | None = None, keyword: str | None = Query(None, max_length=2000), db: Session = Depends(get_db)) -> list[dict]:
    if keyword:
        exact = _exact_model_rows(db, keyword, brand)
        if exact:
            return enrich_gpu_display_fields(db, [model_to_summary(model) for model in exact])
    stmt = active_models_query().order_by(Model.id)
    if brand:
        stmt = stmt.join(Brand, Model.brand_id == Brand.id).where(func.lower(Brand.code) == brand.lower())
    terms: list[str] = []
    if keyword:
        terms = _keyword_terms(keyword)
        for term in terms:
            like = f"%{term}%"
            spec_match = _positive_spec_match(term)
            stmt = stmt.where(or_(Model.model_name.ilike(like), Model.title.ilike(like), Model.series.has(Series.name.ilike(like)), Model.product_type.has(ProductType.name.ilike(like)), spec_match))
    model_rows = list(db.scalars(stmt).unique().all())
    if keyword:
        model_rows.sort(key=lambda model: _search_rank(db, model, terms))
    return enrich_gpu_display_fields(db, [model_to_summary(model) for model in model_rows])


@router.get("/models/{model_id}", response_model=ModelDetail)
def model_detail(model_id: int, db: Session = Depends(get_db)) -> dict:
    model = db.scalar(active_models_query().where(Model.id == model_id))
    if not model:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Model not found")
    data = model_to_summary(model)
    data.update({"source_ref": model.source_ref, "raw_source_id": model.raw_source_id, "specifications": specs_for_model(db, model.id), "compatible_gpus": compatible_gpus_for_model(db, model.id)})
    return data


@router.get("/models/{model_id}/specifications")
def model_specifications(model_id: int, db: Session = Depends(get_db)) -> list[dict]:
    if not db.scalar(active_models_query().where(Model.id == model_id)):
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Model not found")
    return specs_for_model(db, model_id)


@router.get("/search", response_model=list[ModelSummary])
def search(q: str = Query(min_length=1, max_length=2000), brand: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    exact = _exact_model_rows(db, q, brand)
    if exact:
        return enrich_gpu_display_fields(db, [model_to_summary(model) for model in exact])
    terms = _keyword_terms(q)
    if not terms:
        return []

    def term_matches(term: str):
        like = f"%{term}%"
        spec_match = _positive_spec_match(term)
        cpu_match = exists(
            select(1)
            .select_from(CpuCompatibility)
            .where(
                or_(
                    CpuCompatibility.server_model == Model.model_name,
                    func.replace(CpuCompatibility.server_model, "G7", "A7") == Model.model_name,
                ),
                or_(
                    CpuCompatibility.server_model.ilike(like),
                    CpuCompatibility.cpu_display.ilike(like),
                    CpuCompatibility.cpu_spec.ilike(like),
                    CpuCompatibility.config_code.ilike(like),
                    CpuCompatibility.product_name.ilike(like),
                ),
            )
        )
        return or_(
            Model.model_name.ilike(like),
            Model.title.ilike(like),
            Model.platform_vendor.ilike(like),
            Series.name.ilike(like),
            ProductType.name.ilike(like),
            spec_match,
            cpu_match,
        )

    stmt = (
        active_models_query()
        .join(Brand, Model.brand_id == Brand.id)
        .join(ProductType, Model.product_type_id == ProductType.id)
        .join(Series, Model.series_id == Series.id)
        .where(and_(*(term_matches(term) for term in terms)))
        .order_by(Brand.name, ProductType.name, Series.name, Model.model_name)
    )
    if brand:
        stmt = stmt.where(func.lower(Brand.code) == brand.lower())
    model_rows = list(db.scalars(stmt).unique().all())
    model_rows.sort(key=lambda model: _search_rank(db, model, terms))
    return enrich_gpu_display_fields(db, [model_to_summary(model) for model in model_rows])


@router.get("/cpu-compatibility/summary")
def cpu_compatibility_summary(db: Session = Depends(get_db)) -> dict:
    rows = db.execute(
        select(CpuCompatibility.server_model, func.count(CpuCompatibility.id), func.count(func.distinct(CpuCompatibility.config_id)))
        .group_by(CpuCompatibility.server_model)
        .order_by(CpuCompatibility.server_model)
    ).all()
    return {
        "row_count": sum(row_count for _, row_count, _ in rows),
        "model_count": len(rows),
        "models": [{"server_model": model, "row_count": row_count, "config_count": config_count} for model, row_count, config_count in rows],
    }


@router.get("/cpu-compatibility")
def cpu_compatibility(server_model: str = Query(min_length=1), limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(
        select(CpuCompatibility)
        .where(CpuCompatibility.server_model == server_model)
        .order_by(CpuCompatibility.config_code, CpuCompatibility.cpu_display)
        .limit(limit)
    ).all()
    return [
        {
            "server_model": row.server_model,
            "server_id": row.server_id,
            "config_code": row.config_code,
            "config_id": row.config_id,
            "product_name": row.product_name,
            "cpu_display": row.cpu_display,
            "cpu_spec": row.cpu_spec,
            "source_url": row.source_url,
            "collected_date": row.collected_date,
        }
        for row in rows
    ]


@router.post("/ai/recommend", response_model=AiRecommendOut)
def ai_recommend(payload: AiRecommendIn, db: Session = Depends(get_db)) -> dict:
    from app.ai_service import recommend_models
    return recommend_models(db, payload.message, payload.brand_code)
