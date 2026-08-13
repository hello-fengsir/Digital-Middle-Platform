import logging

from fastapi import APIRouter, Cookie, Depends, File, HTTPException, Query, Response, UploadFile

ADMIN_SESSION_COOKIE = "producthub_admin_session"
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.catalog import (
    active_models_query,
    create_model_with_existing_catalog,
    model_to_summary,
    patch_model,
    replace_model_specs,
    soft_delete_model,
    spec_definition_to_dict,
    spec_definitions_query,
    spec_groups_with_fields,
    specs_for_model,
    compatible_gpus_for_model,
    list_gpu_accessory_models,
    replace_compatible_gpus_atomic,
    upsert_model,
)
from app.db import get_db
from app.importer import build_import_template, parse_import_workbook, parse_markdown_import
from app.models import AuditLog, Brand, Model, ModelSpecValue, Series, SpecDefinition
from app.schemas import (
    AdminLoginIn,
    AiAgentRuleIn,
    AiAgentRuleOut,
    AiConfigIn,
    AiConfigOut,
    AiConfigTestIn,
    AdminMeOut,
    AdminSessionOut,
    ImportPreviewOut,
    ImportPreviewRow,
    MarkdownImportIn,
    ModelDetail,
    ModelPatch,
    CompatibleGpuWrite,
    CompatibleGpuOut,
    ModelSummary,
    ModelWrite,
    SpecDefinitionOut,
    SpecDefinitionPatch,
    SpecGroupOut,
    SpecInput,
    SpecRecognitionPreviewIn,
    SpecRecognitionPreviewOut,
)
from app.security import create_admin_session_token, format_expires_at, parse_admin_session_token, require_admin_session, verify_admin_password
from app.config import settings
from app.catalog import preview_spec_recognition

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin")


@router.post("/auth/login", response_model=AdminSessionOut)
def admin_login(payload: AdminLoginIn, response: Response) -> dict:
    if payload.username != settings.admin_username or not verify_admin_password(payload.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token, expires_at = create_admin_session_token(payload.username)
    response.set_cookie(
        key=ADMIN_SESSION_COOKIE,
        value=token,
        max_age=int(settings.admin_session_ttl_seconds),
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return {"token": token, "username": payload.username, "expires_at": format_expires_at(expires_at)}


@router.get("/auth/nginx", status_code=204)
def admin_nginx_auth(
    session_token: str | None = Cookie(default=None, alias=ADMIN_SESSION_COOKIE),
) -> Response:
    if not session_token:
        raise HTTPException(status_code=401, detail="Admin login required")
    parse_admin_session_token(session_token)
    return Response(status_code=204)


@router.get("/auth/me", response_model=AdminMeOut)
def admin_me(admin=Depends(require_admin_session)) -> dict:
    return {"username": admin["sub"], "expires_at": format_expires_at(int(admin["exp"]))}


@router.post("/auth/logout")
def admin_logout(response: Response) -> dict:
    response.delete_cookie(
        key=ADMIN_SESSION_COOKIE,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )
    return {"ok": True}


@router.get("/spec-groups", response_model=list[SpecGroupOut])
def admin_spec_groups(db: Session = Depends(get_db), admin=Depends(require_admin_session)) -> list[dict]:
    return spec_groups_with_fields(db)


@router.get("/spec-definitions", response_model=list[SpecDefinitionOut])
def admin_spec_definitions(db: Session = Depends(get_db), admin=Depends(require_admin_session)) -> list[dict]:
    return [spec_definition_to_dict(spec, group) for spec, group in db.execute(spec_definitions_query()).all()]


@router.patch("/spec-definitions/{spec_id}", response_model=SpecDefinitionOut)
def admin_patch_spec_definition(spec_id: int, payload: SpecDefinitionPatch, db: Session = Depends(get_db), admin=Depends(require_admin_session)) -> dict:
    raise HTTPException(status_code=423, detail={"code": "FIELD_DICTIONARY_LOCKED", "message": "Field dictionary is migration-only"})


@router.delete("/series/{series_id}", status_code=204)
def admin_delete_series(series_id: int, db: Session = Depends(get_db), admin=Depends(require_admin_session)) -> None:
    series = db.get(Series, series_id)
    if not series or series.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Series not found")
    has_models = db.scalar(select(Model.id).where(Model.series_id == series.id).exists().select())
    if has_models:
        raise HTTPException(status_code=409, detail="Series has bound models and cannot be deleted")
    db.execute(delete(Series).where(Series.id == series.id))
    db.commit()


@router.get("/models", response_model=list[ModelSummary])
def admin_models(brand: str | None = None, keyword: str | None = None, status: str = Query("active", pattern="^(active|deleted|all)$"), db: Session = Depends(get_db), admin=Depends(require_admin_session)) -> list[dict]:
    stmt = select(Model).where(Model.brand.has(Brand.deleted_at.is_(None))).order_by(Model.id)
    if status == "active":
        stmt = stmt.where(Model.deleted_at.is_(None), Model.status == "active")
    elif status == "deleted":
        stmt = stmt.where(or_(Model.deleted_at.is_not(None), Model.status == "deleted"))
    if brand:
        stmt = stmt.join(Brand, Model.brand_id == Brand.id).where(Brand.code.ilike(brand))
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(Model.model_name.ilike(like), Model.title.ilike(like)))
    return [model_to_summary(model) for model in db.scalars(stmt).unique().all()]


def _model_detail_data(model: Model, db: Session) -> dict:
    data = model_to_summary(model)
    data.update({"source_ref": model.source_ref, "raw_source_id": model.raw_source_id, "specifications": specs_for_model(db, model.id), "compatible_gpus": compatible_gpus_for_model(db, model.id)})
    return data


@router.get("/models/{model_id}", response_model=ModelDetail)
def admin_model_detail(model_id: int, db: Session = Depends(get_db), admin=Depends(require_admin_session)) -> dict:
    model = db.get(Model, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return _model_detail_data(model, db)


@router.post("/spec-recognition/preview", response_model=SpecRecognitionPreviewOut)
def admin_spec_recognition_preview(payload: SpecRecognitionPreviewIn, db: Session = Depends(get_db), admin=Depends(require_admin_session)) -> dict:
    return {"items": preview_spec_recognition(db, payload.raw_text, brand_code=payload.brand_code, product_type=payload.product_type, series=payload.series, model_name=payload.model_name)}



def _validate_import_field_keys(db: Session, sheet_rows: list) -> list[str]:
    existing_keys = set(db.scalars(select(SpecDefinition.field_key)).all())
    errors: list[str] = []
    seen: set[tuple[str, str, int]] = set()
    for item in sheet_rows:
        # 校验与后续写入必须使用同一份规范值，避免 preview 通过而 run
        # 又把首尾空格写回 payload。str.strip() 同时覆盖 Unicode 空白。
        item.model_name = (item.model_name or "").strip()
        item.field_key = (item.field_key or "").strip()
        item.field_label = (item.field_label or "").strip()
        item.field_group = (item.field_group or "").strip()
        item.value = (item.value or "").strip()
        item.source_ref = (item.source_ref or "").strip()
        if not item.field_key or item.field_key not in existing_keys or item.field_key.startswith("raw_"):
            marker = (item.model_name, item.field_key, item.row_number)
            if marker in seen:
                continue
            seen.add(marker)
            errors.append(f"第 {item.row_number} 行 / 型号 {item.model_name} 字段“{item.field_label}”未绑定现有字段字典（field_key={item.field_key}），导入不允许自动新增字段，请先在后台字段字典中选择/维护现有字段")
    return errors


def _import_preview_response(rows: list[ModelWrite], errors: list[str], sheet_rows: list) -> dict:
    preview_rows = [
        ImportPreviewRow(
            row_number=i + 2,
            brand_code=row.brand_code,
            brand_name=row.brand_name or "",
            product_type=row.product_type,
            series=row.series,
            model_name=row.model_name,
            title=row.title,
            platform_vendor=row.platform_vendor,
            generation=row.generation,
            source_ref=row.source_ref,
            raw_source_id=row.raw_source_id,
        )
        for i, row in enumerate(rows)
    ]
    valid_rows = sum(1 for row in rows if row.brand_code and row.product_type and row.series and row.model_name)
    invalid_rows = len(rows) - valid_rows
    return {"total_rows": len(rows), "valid_rows": valid_rows, "invalid_rows": invalid_rows, "errors": errors, "rows": preview_rows, "sheet_rows": sheet_rows}


def _run_import_payloads(rows: list[ModelWrite], sheet_rows: list, db: Session, source_label: str) -> dict:
    created = updated = 0
    for payload in rows:
        existing = db.scalar(select(Model).join(Brand).where(Brand.code == payload.brand_code, Model.model_name == payload.model_name, Model.deleted_at.is_(None)))
        if existing:
            updated += 1
        else:
            created += 1
        relevant = [item for item in sheet_rows if item.model_name == payload.model_name]
        payload.specifications = [
            SpecInput(
                field_key=item.field_key,
                label=item.field_label,
                group=item.field_group,
                value=item.value,
                raw_label=item.field_label,
                source_ref=item.source_ref or source_label,
            )
            for item in relevant
        ]
        upsert_model(db, payload, None, source_label)
    return {"created": created, "updated": updated, "errors": [], "sheet_rows": len(sheet_rows)}


@router.get("/import/template")
def admin_import_template(admin=Depends(require_admin_session)) -> Response:
    data = build_import_template()
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=hardware-product-library-import-template.xlsx"},
    )


@router.post("/import/preview", response_model=ImportPreviewOut)
def admin_import_preview(file: UploadFile = File(...), db: Session = Depends(get_db), admin=Depends(require_admin_session)) -> dict:
    rows, errors, sheet_rows = parse_import_workbook(file.file.read())
    errors = [*errors, *_validate_import_field_keys(db, sheet_rows)]
    return _import_preview_response(rows, errors, sheet_rows)


@router.post("/import/run")
def admin_import_run(file: UploadFile = File(...), db: Session = Depends(get_db), admin=Depends(require_admin_session)) -> dict:
    rows, errors, sheet_rows = parse_import_workbook(file.file.read())
    errors = [*errors, *_validate_import_field_keys(db, sheet_rows)]
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})
    try:
        return _run_import_payloads(rows, sheet_rows, db, "import")
    except Exception:
        db.rollback()
        raise


@router.post("/import/markdown/preview", response_model=ImportPreviewOut)
def admin_markdown_import_preview(payload: MarkdownImportIn, db: Session = Depends(get_db), admin=Depends(require_admin_session)) -> dict:
    rows, errors, sheet_rows = parse_markdown_import(payload.raw_text)
    errors = [*errors, *_validate_import_field_keys(db, sheet_rows)]
    return _import_preview_response(rows, errors, sheet_rows)


@router.post("/import/markdown/run")
def admin_markdown_import_run(payload: MarkdownImportIn, db: Session = Depends(get_db), admin=Depends(require_admin_session)) -> dict:
    rows, errors, sheet_rows = parse_markdown_import(payload.raw_text)
    errors = [*errors, *_validate_import_field_keys(db, sheet_rows)]
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})
    try:
        return _run_import_payloads(rows, sheet_rows, db, "markdown")
    except Exception:
        db.rollback()
        raise


@router.post("/models", response_model=ModelDetail)
def admin_create(payload: ModelWrite, db: Session = Depends(get_db), admin=Depends(require_admin_session)) -> dict:
    model = create_model_with_existing_catalog(db, payload, None)
    return _model_detail_data(model, db)


@router.patch("/models/{model_id}", response_model=ModelDetail)
def admin_patch(model_id: int, payload: ModelPatch, db: Session = Depends(get_db), admin=Depends(require_admin_session)) -> dict:
    model = db.scalar(active_models_query().where(Model.id == model_id))
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    patch_model(db, model, payload, None)
    return _model_detail_data(model, db)


@router.put("/models/{model_id}/compatible-gpus", response_model=list[CompatibleGpuOut])
@router.patch("/models/{model_id}/compatible-gpus", response_model=list[CompatibleGpuOut])
def admin_replace_compatible_gpus(model_id: int, payload: CompatibleGpuWrite, db: Session = Depends(get_db), admin=Depends(require_admin_session)) -> list[dict]:
    model = db.scalar(active_models_query().where(Model.id == model_id))
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    replace_compatible_gpus_atomic(db, model, payload.compatible_gpu_ids, None)
    return compatible_gpus_for_model(db, model.id)


@router.delete("/models/{model_id}", status_code=204)
def admin_delete(model_id: int, db: Session = Depends(get_db), admin=Depends(require_admin_session)) -> None:
    model = db.get(Model, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    if model.deleted_at is not None or model.status == "deleted":
        db.execute(delete(ModelSpecValue).where(ModelSpecValue.model_id == model.id))
        db.execute(delete(Model).where(Model.id == model.id))
        db.commit()
        return
    soft_delete_model(db, model, None)


@router.put("/models/{model_id}/specifications", response_model=list[dict])
def admin_put_specs(model_id: int, payload: list[SpecInput], db: Session = Depends(get_db), admin=Depends(require_admin_session)) -> list[dict]:
    model = db.scalar(active_models_query().where(Model.id == model_id))
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    replace_model_specs(db, model, payload, None)
    return specs_for_model(db, model.id)


@router.post("/models/upsert", response_model=ModelDetail)
def admin_upsert(payload: ModelWrite, db: Session = Depends(get_db), admin=Depends(require_admin_session)) -> dict:
    model = upsert_model(db, payload, None, "upsert")
    return _model_detail_data(model, db)


@router.get("/gpu-options")
def admin_gpu_options(db: Session = Depends(get_db), admin=Depends(require_admin_session)) -> list[dict]:
    return list_gpu_accessory_models(db)


@router.get("/ai-config", response_model=AiConfigOut)
def admin_ai_config(db: Session = Depends(get_db), admin=Depends(require_admin_session)) -> dict:
    from app.ai_service import get_ai_config_public
    return get_ai_config_public(db)


@router.put("/ai-config", response_model=AiConfigOut)
def admin_put_ai_config(payload: AiConfigIn, db: Session = Depends(get_db), admin=Depends(require_admin_session)) -> dict:
    from app.ai_service import save_ai_config
    return save_ai_config(db, payload)


@router.delete("/ai-config/api-key", response_model=AiConfigOut)
def admin_delete_ai_config_api_key(
    db: Session = Depends(get_db),
    admin=Depends(require_admin_session),
) -> dict:
    from app.ai_service import delete_ai_provider_api_key
    return delete_ai_provider_api_key(db, admin.get("sub", "unknown"))


@router.post("/ai-config/test")
def admin_test_ai_config(payload: AiConfigTestIn, db: Session = Depends(get_db), admin=Depends(require_admin_session)) -> dict:
    from app.ai_service import test_ai_config
    return test_ai_config(db, payload)


@router.get("/ai-agent-rule", response_model=AiAgentRuleOut)
def admin_ai_agent_rule(admin=Depends(require_admin_session)) -> dict:
    from app.ai_agent_rule import get_ai_agent_rule
    return get_ai_agent_rule()


@router.put("/ai-agent-rule", response_model=AiAgentRuleOut)
def admin_put_ai_agent_rule(
    payload: AiAgentRuleIn,
    db: Session = Depends(get_db),
    admin=Depends(require_admin_session),
) -> dict:
    from app.ai_agent_rule import (
        RULE_BACKUP_NAME,
        restore_ai_agent_rule_files,
        save_ai_agent_rule,
        snapshot_ai_agent_rule_files,
    )

    snapshot = snapshot_ai_agent_rule_files()
    result = save_ai_agent_rule(payload.content)
    db.add(AuditLog(
        api_client_id=None,
        action="update_ai_selection_agent_rule",
        entity_type="ai_selection_agent_rule",
        entity_id=None,
        payload={
            "character_count": len(payload.content),
            "sha256": result["sha256"],
            "backup_name": RULE_BACKUP_NAME,
            # AuditLog lacks an admin FK/actor column. Preserve the authenticated
            # subject as a bounded string without changing the database schema.
            "actor": str(admin.get("sub", "unknown"))[:128],
        },
    ))
    try:
        db.commit()
    except Exception:
        db.rollback()
        # Preserve the original commit exception; compensation must never log rule bytes.
        try:
            restore_ai_agent_rule_files(snapshot)
        except Exception:
            logger.error("AI agent rule file compensation restore failed")
        raise
    return result
