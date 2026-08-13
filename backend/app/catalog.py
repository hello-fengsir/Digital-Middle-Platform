from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import re

from sqlalchemy import and_, delete, func, or_, select
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models import AuditLog, Brand, Model, ModelBusinessTag, ModelCompatibleGpu, ModelSpecValue, ProductType, Series, SpecDefinition, SpecGroup
from app.schemas import ModelPatch, ModelWrite, SpecDefinitionPatch, SpecInput


def resolve_existing_brand(db: Session, code: str) -> Brand:
    brand = db.scalar(select(Brand).where(Brand.code == code, Brand.deleted_at.is_(None), Brand.status == "active"))
    if not brand:
        raise HTTPException(status_code=400, detail="brand_code must be an existing active brand")
    return brand


def resolve_existing_product_type(db: Session, value: str) -> ProductType:
    product_type = db.scalar(
        select(ProductType).where(
            or_(ProductType.name == value, ProductType.code == value),
            ProductType.deleted_at.is_(None),
            ProductType.status == "active",
        )
    )
    if not product_type:
        raise HTTPException(status_code=400, detail="product_type must be an existing active product type")
    return product_type


def resolve_existing_series(db: Session, brand: Brand, product_type: ProductType, name: str) -> Series:
    normalized_name = name.strip()
    series = db.scalar(
        select(Series).where(
            Series.brand_id == brand.id,
            Series.product_type_id == product_type.id,
            func.lower(func.trim(Series.name)) == normalized_name.lower(),
            Series.deleted_at.is_(None),
            Series.status == "active",
        )
    )
    if not series:
        raise HTTPException(status_code=400, detail="series must be an existing active option for the selected brand and product_type")
    return series


LIFECYCLE_LABELS = {
    "npi": "新品",
    "rts": "在售",
    "rtq": "可报价",
    "eos": "停止接单",
    "eol": "停售",
}
BUSINESS_TAG_LABELS = {"featured": "主推"}


def replace_business_tags(db: Session, model: Model, tags: list[str] | None) -> None:
    if tags is None:
        return
    db.execute(delete(ModelBusinessTag).where(ModelBusinessTag.model_id == model.id))
    for tag in tags:
        db.add(ModelBusinessTag(model_id=model.id, tag=tag))
    db.flush()


def business_tags_for_model(model: Model) -> list[str]:
    return sorted(row.tag for row in model.business_tag_rows)


def badges_for_model(model: Model) -> list[dict]:
    lifecycle = model.lifecycle_status
    badges = ([{"kind": "lifecycle", "code": lifecycle, "label": LIFECYCLE_LABELS[lifecycle]}]
              if lifecycle in LIFECYCLE_LABELS else [])
    badges.extend({"kind": "business", "code": tag, "label": BUSINESS_TAG_LABELS[tag]} for tag in business_tags_for_model(model))
    return badges


GROUP_CODES = {
    "基础信息": "basic",
    "处理器": "processor",
    "内存": "memory",
    "存储": "storage",
    "RAID": "raid",
    "网络": "network",
    "PCIe与扩展": "pcie_expansion",
    "GPU": "gpu",
    "电源": "power",
    "管理": "management",
    "尺寸与环境": "dimension_environment",
    "操作系统与认证": "os_certification",
    "其他": "other",
}

FIELD_MAP: dict[str, tuple[str, str, str]] = {
    "产品形态": ("basic", "rack_height", "产品形态/机架高度"),
    "外形": ("basic", "rack_height", "产品形态/机架高度"),
    "系列/类型": ("basic", "product_form", "系列/类型"),
    "机型": ("basic", "machine_type", "机型编码"),
    "机型编码": ("basic", "machine_type", "机型编码"),
    "资料类型": ("basic", "source_material_type", "资料类型"),
    "处理器": ("processor", "cpu_family", "处理器"),
    "CPU": ("processor", "cpu_family", "处理器"),
    "内存": ("memory", "memory", "内存"),
    "存储": ("storage", "storage", "存储"),
    "存储控制器": ("raid", "raid_controller", "存储控制器"),
    "RAID": ("raid", "raid_controller", "RAID"),
    "网络接口": ("network", "network_interfaces", "网络接口"),
    "网络": ("network", "network_interfaces", "网络接口"),
    "I/O扩展插槽": ("pcie_expansion", "pcie_slots", "I/O扩展插槽"),
    "PCIe": ("pcie_expansion", "pcie_slots", "PCIe"),
    "GPU": ("gpu", "gpu_support", "GPU"),
    "显卡": ("gpu", "gpu_support", "显卡"),
    "产品定位": ("gpu", "gpu_product_positioning", "产品定位"),
    "显存容量": ("gpu", "gpu_memory_capacity", "显存容量"),
    "显存类型与带宽": ("gpu", "gpu_memory_type_bandwidth", "显存类型与带宽"),
    "单精度算力(FP8)": ("gpu", "gpu_fp8_performance", "单精度算力(FP8)"),
    "AI 算力(TensorCore)": ("gpu", "gpu_ai_tensor_performance", "AI 算力(TensorCore)"),
    "互联技术": ("gpu", "gpu_interconnect", "互联技术"),
    "功耗(TDP)": ("gpu", "gpu_tdp", "功耗(TDP)"),
    "市场参考价格": ("gpu", "gpu_market_reference_price", "市场参考价格"),
    "官网参数链接": ("basic", "official_params_url", "官网参数链接"),
    "产品彩页": ("basic", "product_brochure_url", "产品彩页"),
    "产品彩页链接": ("basic", "product_brochure_url", "产品彩页"),
    "产品技术白皮书下载": ("basic", "whitepaper_url", "产品技术白皮书下载"),
    "白皮书": ("basic", "whitepaper_url", "产品技术白皮书下载"),
    "选型注意事项": ("basic", "selection_notes", "选型注意事项"),
    "电源": ("power", "power_supply", "电源"),
    "风扇": ("power", "fan", "风扇"),
    "系统管理": ("management", "management", "系统管理"),
    "BMC": ("management", "management", "BMC"),
    "尺寸": ("dimension_environment", "dimensions", "尺寸与重量"),
    "重量": ("dimension_environment", "dimensions", "尺寸与重量"),
    "重量(不带硬盘)": ("dimension_environment", "dimensions", "尺寸与重量"),
    "重量（不带硬盘，kg）": ("dimension_environment", "dimensions", "尺寸与重量"),
    "工作温度": ("dimension_environment", "operating_temperature", "工作温度"),
    "操作系统": ("os_certification", "operating_system", "操作系统"),
    "认证": ("os_certification", "certification", "认证"),
    "特点": ("other", "features", "特点"),
    "补充说明": ("other", "notes", "补充说明"),
}

CANONICAL_SPEC_LABELS = {
    "dimensions": "尺寸与重量",
}

STANDARD_FIELDS: list[tuple[str, str, str, int]] = [
    ("基础信息", "rack_height", "产品形态/机架高度", 10),
    ("基础信息", "product_form", "系列/类型", 20),
    ("基础信息", "machine_type", "机型编码", 30),
    ("处理器", "cpu_socket_count", "CPU路数", 10),
    ("处理器", "cpu_family", "处理器", 20),
    ("内存", "memory_slots", "内存插槽", 10),
    ("内存", "memory_max_capacity", "最大内存容量", 20),
    ("内存", "memory", "内存", 30),
    ("存储", "drive_bay_25", "2.5英寸盘位", 10),
    ("存储", "drive_bay_35", "3.5英寸盘位", 20),
    ("存储", "nvme_support", "NVMe支持", 30),
    ("存储", "storage", "存储", 40),
    ("RAID", "raid_controller", "RAID/存储控制器", 10),
    ("网络", "network_interfaces", "网络接口", 10),
    ("PCIe与扩展", "pcie_slots", "PCIe与扩展", 10),
    ("GPU", "gpu_support", "GPU支持", 10),
    ("电源", "power_supply", "电源", 10),
    ("电源", "fan", "风扇", 20),
    ("管理", "management", "管理", 10),
    ("尺寸与环境", "dimensions", "尺寸与重量", 10),
    ("尺寸与环境", "operating_temperature", "工作温度", 20),
    ("操作系统与认证", "operating_system", "操作系统", 10),
    ("操作系统与认证", "certification", "认证", 20),
    ("其他", "features", "特点", 20),
    ("其他", "notes", "备注", 30),
]


def normalize_product_type(name: str) -> str:
    value = name.strip()
    if "工作站" in value:
        return "工作站"
    if "存储" in value:
        return "存储"
    if "服务器" in value or "Rack" in value:
        return "服务器"
    return value.split("(")[0].strip() or "其他"


def stable_raw_field_key(label: str) -> str:
    digest = hashlib.sha1(label.encode("utf-8")).hexdigest()[:12]
    return f"raw_{digest}"


def map_field(raw_label: str) -> tuple[str, str, str]:
    label = raw_label.strip()
    if label in FIELD_MAP:
        return FIELD_MAP[label]
    for key, mapped in FIELD_MAP.items():
        if key in label:
            return mapped
    return ("other", stable_raw_field_key(label), label)



SPEC_RECOGNITION_ALIASES: dict[str, list[str]] = {
    "cpu_family": ["cpu", "处理器", "cpu型号", "处理器型号", "cpu规格", "processor"],
    "cpu_socket_count": ["cpu路数", "处理器数量", "处理器路数", "socket", "sockets"],
    "memory": ["内存", "内存规格", "内存类型", "memory", "ram"],
    "memory_slots": ["内存插槽", "内存槽位", "dimm", "dimm插槽", "memory slots"],
    "memory_max_capacity": ["最大内存", "最大内存容量", "内存容量", "max memory"],
    "storage": ["硬盘", "存储", "硬盘配置", "存储配置", "drive", "storage", "disk"],
    "drive_bay_25": ["2.5英寸盘位", "2.5寸盘位", "2.5盘位", "sff盘位"],
    "drive_bay_35": ["3.5英寸盘位", "3.5寸盘位", "3.5盘位", "lff盘位"],
    "nvme_support": ["nvme", "nvme支持"],
    "raid_controller": ["raid", "raid卡", "阵列卡", "存储控制器", "raid控制器"],
    "network_interfaces": ["网卡", "网络", "网络接口", "以太网", "lan", "nic", "network"],
    "pcie_slots": ["pcie", "pci-e", "扩展槽", "i/o扩展插槽", "io扩展插槽", "pcie插槽"],
    "gpu_support": ["gpu", "显卡", "gpu支持"],
    "power_supply": ["电源", "电源模块", "psu", "power"],
    "fan": ["风扇", "散热", "fan"],
    "management": ["管理", "系统管理", "bmc", "ipmi", "远程管理", "管理芯片"],
    "dimensions": ["尺寸", "重量", "尺寸与重量", "规格尺寸", "外形尺寸", "物理尺寸", "重量不带硬盘", "dimension", "dimensions", "weight"],
    "operating_temperature": ["工作温度", "运行温度", "温度"],
    "operating_system": ["操作系统", "os", "系统支持"],
    "certification": ["认证", "资质认证"],
    "rack_height": ["产品形态", "机架高度", "外形", "形态", "高度"],
    "product_form": ["系列/类型", "产品类型", "类型"],
    "machine_type": ["机型", "机型编码", "型号编码"],
    "official_params_url": ["官网链接", "官网参数", "官网参数链接", "参数链接", "官方网站", "url", "链接"],
    "product_brochure_url": ["彩页", "产品彩页", "产品手册", "brochure"],
    "whitepaper_url": ["白皮书", "技术白皮书", "whitepaper"],
    "selection_notes": ["选型注意事项", "注意事项", "选型说明"],
    "features": ["特点", "特性", "功能特性", "亮点"],
    "notes": ["备注", "补充说明", "说明"],
}

_LABEL_SPLIT_RE = re.compile(r"^\s*([^：:\t|]+?)\s*(?:[:：\t|]|\s{2,})\s*(.+?)\s*$")
_MULTI_SPACE_RE = re.compile(r"\s+")


def _normalize_match_text(value: str) -> str:
    return _MULTI_SPACE_RE.sub("", (value or "").strip().lower().replace("：", ":").replace("（", "(").replace("）", ")"))


def _extract_spec_pairs(raw_text: str) -> list[tuple[str, str, str]]:
    pairs: list[tuple[str, str, str]] = []
    for raw_line in (raw_text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        match = _LABEL_SPLIT_RE.match(line)
        if match:
            label, value = match.group(1).strip(), match.group(2).strip()
            if label and value:
                pairs.append((label[:255], value, "规则：参数名-值分隔"))
            continue
        cells = [cell.strip() for cell in re.split(r"\t+|\s{2,}|\|", line) if cell.strip()]
        if len(cells) >= 2:
            pairs.append((cells[0][:255], " ".join(cells[1:]), "规则：表格行复制文本"))
    return pairs


def _build_spec_match_index(db: Session) -> list[tuple[str, str, str, str, str]]:
    rows = db.execute(spec_definitions_query()).all()
    candidates: list[tuple[str, str, str, str, str]] = []
    for spec, group in rows:
        texts = {spec.field_key, spec.label}
        texts.update(SPEC_RECOGNITION_ALIASES.get(spec.field_key, []))
        for text in texts:
            normalized = _normalize_match_text(text)
            if normalized:
                candidates.append((normalized, spec.field_key, spec.label, group.code, group.name))
    return candidates


def _match_spec_label(raw_label: str, candidates: list[tuple[str, str, str, str, str]]) -> tuple[str | None, str | None, str | None, str | None, float, str]:
    normalized = _normalize_match_text(raw_label)
    if not normalized:
        return None, None, None, None, 0.0, "未识别：空参数名"
    best: tuple[str | None, str | None, str | None, str | None, float, str] = (None, None, None, None, 0.0, "未匹配到 spec_definitions 字段")
    for text, field_key, label, group_code, group_name in candidates:
        if normalized == text:
            return field_key, label, group_code, group_name, 1.0, "精确匹配 spec_definitions/别名"
        if text in normalized or normalized in text:
            score = min(len(text), len(normalized)) / max(len(text), len(normalized))
            score = max(0.82, min(0.95, score))
        else:
            score = SequenceMatcher(None, normalized, text).ratio()
        if score > best[4]:
            best = (field_key, label, group_code, group_name, round(score, 2), "相似度匹配 spec_definitions/别名")
    if best[4] >= 0.72:
        return best
    return None, None, None, None, round(best[4], 2), "未匹配到 spec_definitions 字段"



def _ai_spec_recognition(db: Session, raw_text: str, *, brand_code: str | None = None, product_type: str | None = None, series: str | None = None, model_name: str | None = None) -> list[dict] | None:
    import json
    import os
    import urllib.request
    from app.config import settings
    base_url = (settings.ai_base_url or os.getenv("HPL_AI_BASE_URL") or "").strip().rstrip("/")
    api_key = (settings.ai_api_key or os.getenv("HPL_AI_API_KEY") or "").strip()
    model = (settings.ai_model or os.getenv("HPL_AI_MODEL") or "").strip()
    if not (base_url and api_key and model and raw_text.strip()):
        return None
    chat_url = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
    definitions = [
        {"field_key": spec.field_key, "label": spec.label, "group_code": group.code if group else None, "group_name": group.name if group else None}
        for spec, group in db.execute(spec_definitions_query()).all()
        if not spec.field_key.startswith("raw_")
    ]
    system = "你是服务器产品参数录入助手。把用户粘贴的服务器参数拆成结构化参数行，并从给定字段字典中选择最匹配的 field_key。只能使用字段字典里的 field_key；无法匹配返回 null。不要编造，不要补充常识。只输出 JSON。"
    user = {"context": {"brand_code": brand_code, "product_type": product_type, "series": series, "model_name": model_name}, "field_definitions": definitions, "raw_text": raw_text, "output_schema": {"items": [{"raw_label": "原始参数名", "value": "原始参数值", "matched_field_key": "字段字典field_key或null", "confidence": 0.0, "note": "简短理由"}]}}
    payload = {"model": model, "temperature": 0, "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, ensure_ascii=False)}]}
    try:
        req = urllib.request.Request(chat_url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=45) as res:
            data = json.loads(res.read().decode("utf-8"))
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        parsed = json.loads(content)
        raw_items = parsed.get("items", []) if isinstance(parsed, dict) else []
    except Exception:
        return None
    by_key = {item["field_key"]: item for item in definitions}
    results: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for item in raw_items:
        raw_label = str(item.get("raw_label") or "").strip()[:128]
        value = str(item.get("value") or "").strip()
        if not raw_label or not value:
            continue
        key = (_normalize_match_text(raw_label), value)
        if key in seen:
            continue
        seen.add(key)
        matched_key = item.get("matched_field_key")
        definition = by_key.get(matched_key) if matched_key else None
        try:
            confidence = float(item.get("confidence", 0.85 if definition else 0.2))
        except Exception:
            confidence = 0.85 if definition else 0.2
        results.append({"raw_label": raw_label, "value": value, "matched_field_key": definition["field_key"] if definition else None, "matched_label": definition["label"] if definition else None, "group_code": definition["group_code"] if definition else None, "group_name": definition["group_name"] if definition else None, "confidence": max(0.0, min(1.0, confidence)), "note": f"AI识别；{str(item.get('note') or '').strip()[:120]}" if definition else "AI识别；未匹配字段字典，需人工选择字段"})
    return results or None

def preview_spec_recognition(db: Session, raw_text: str, *, brand_code: str | None = None, product_type: str | None = None, series: str | None = None, model_name: str | None = None) -> list[dict]:
    ai_items = _ai_spec_recognition(db, raw_text, brand_code=brand_code, product_type=product_type, series=series, model_name=model_name)
    if ai_items is not None:
        return ai_items
    candidates = _build_spec_match_index(db)
    items: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for raw_label, value, parse_note in _extract_spec_pairs(raw_text):
        key = (_normalize_match_text(raw_label), value.strip())
        if key in seen:
            continue
        seen.add(key)
        matched_field_key, matched_label, group_code, group_name, confidence, match_note = _match_spec_label(raw_label, candidates)
        items.append({
            "raw_label": raw_label,
            "value": value,
            "matched_field_key": matched_field_key,
            "matched_label": matched_label,
            "group_code": group_code,
            "group_name": group_name,
            "confidence": confidence,
            "note": f"规则识别；{parse_note}；{match_note}",
        })
    return items

def seed_spec_template(db: Session) -> None:
    groups: dict[str, SpecGroup] = {}
    for idx, (name, code) in enumerate(GROUP_CODES.items(), start=1):
        group = db.scalar(select(SpecGroup).where(SpecGroup.code == code))
        if not group:
            group = SpecGroup(code=code, name=name, sort_order=idx * 100)
            db.add(group)
            db.flush()
        groups[code] = group
    for name, field_key, label, order in STANDARD_FIELDS:
        group = groups[GROUP_CODES[name]]
        spec = db.scalar(select(SpecDefinition).where(SpecDefinition.field_key == field_key))
        if not spec:
            db.add(SpecDefinition(group_id=group.id, field_key=field_key, label=label, sort_order=order))
    basic_group = groups[GROUP_CODES["基础信息"]]
    for field_key, label, order in [
        ("selection_notes", "选型注意事项", 5),
        ("official_params_url", "官网参数链接", 6),
        ("product_brochure_url", "产品彩页", 7),
        ("whitepaper_url", "产品技术白皮书下载", 8),
    ]:
        spec = db.scalar(select(SpecDefinition).where(SpecDefinition.field_key == field_key))
        if not spec:
            db.add(SpecDefinition(group_id=basic_group.id, field_key=field_key, label=label, sort_order=order))
        else:
            spec.group_id = basic_group.id
            spec.label = label
            spec.sort_order = order
    db.commit()


def get_or_create_brand(db: Session, code: str, name: str | None = None, source_name: str | None = None) -> Brand:
    brand = db.scalar(select(Brand).where(Brand.code == code))
    if brand:
        return brand
    brand = Brand(code=code, name=name or code, source_name=source_name or name or code)
    db.add(brand)
    db.flush()
    return brand


def get_or_create_product_type(db: Session, name: str) -> ProductType:
    normalized = normalize_product_type(name)
    code = normalized.lower().replace(" ", "_")
    product_type = db.scalar(select(ProductType).where(ProductType.code == code))
    if product_type:
        return product_type
    product_type = ProductType(code=code, name=normalized)
    db.add(product_type)
    db.flush()
    return product_type


def get_or_create_series(db: Session, brand: Brand, product_type: ProductType, name: str) -> Series:
    normalized_name = name.strip()
    if not normalized_name:
        raise HTTPException(status_code=400, detail="series is required")
    series = db.scalar(
        select(Series).where(
            Series.brand_id == brand.id,
            Series.product_type_id == product_type.id,
            func.lower(func.trim(Series.name)) == normalized_name.lower(),
            Series.deleted_at.is_(None),
        )
    )
    if series:
        if series.name != normalized_name:
            series.name = normalized_name
        if series.status != "active":
            series.status = "active"
            series.deleted_at = None
        return series
    series = Series(brand_id=brand.id, product_type_id=product_type.id, name=normalized_name)
    db.add(series)
    db.flush()
    return series


def resolve_existing_spec_definitions(db: Session, specs: list[SpecInput], *, model_id: int | None = None) -> dict[str, SpecDefinition]:
    """Resolve the complete request before any business side effect.

    Historical raw definitions remain readable, but may only be updated through an
    already existing model/definition binding. They can never be newly referenced.
    Client label/group/order metadata is deliberately ignored.
    """
    keys = [(item.field_key or "").strip() for item in specs]
    invalid = sorted({key for key in keys if not key})
    unique = sorted(set(keys) - {""})
    definitions = {row.field_key: row for row in db.scalars(select(SpecDefinition).where(SpecDefinition.field_key.in_(unique))).all()} if unique else {}
    invalid.extend(key for key in unique if key not in definitions)
    raw_keys = [key for key in unique if key.startswith("raw_")]
    if raw_keys:
        bound: set[str] = set()
        if model_id is not None:
            bound = set(db.scalars(select(SpecDefinition.field_key).join(ModelSpecValue, ModelSpecValue.spec_definition_id == SpecDefinition.id).where(ModelSpecValue.model_id == model_id, SpecDefinition.field_key.in_(raw_keys))).all())
        invalid.extend(key for key in raw_keys if key not in bound)
    if invalid:
        raise HTTPException(status_code=422, detail={"code": "INVALID_FIELD_KEY", "field_keys": sorted(set(invalid))})
    return definitions


def write_spec_values(db: Session, model: Model, specs: list[SpecInput], resolved: dict[str, SpecDefinition] | None = None) -> None:
    resolved = resolved or resolve_existing_spec_definitions(db, specs, model_id=model.id)
    merged: dict[str, SpecInput] = {}
    rendered_seen: set[tuple[str, str, str]] = set()
    for item in specs:
        key = item.field_key.strip()
        rendered_key = (key, item.value, item.raw_label or "")
        if rendered_key in rendered_seen:
            continue
        rendered_seen.add(rendered_key)
        if key in merged:
            prior = merged[key]
            prior.value = f"{prior.value}\n{item.raw_label or resolved[key].label}: {item.value}"
            prior.raw_label = f"{prior.raw_label or resolved[key].label} / {item.raw_label or resolved[key].label}"
            prior.source_ref = prior.source_ref if prior.source_ref == item.source_ref else f"{prior.source_ref};{item.source_ref}"
        else:
            merged[key] = item
    for key, item in merged.items():
        spec = resolved[key]
        existing = db.scalar(select(ModelSpecValue).where(ModelSpecValue.model_id == model.id, ModelSpecValue.spec_definition_id == spec.id))
        raw_label = item.raw_label or spec.label
        if existing:
            existing.value = item.value
            existing.raw_label = raw_label
            existing.raw_value = item.value
            existing.source_ref = item.source_ref
        else:
            db.add(ModelSpecValue(model_id=model.id, spec_definition_id=spec.id, value=item.value, raw_label=raw_label, raw_value=item.value, source_ref=item.source_ref))


def upsert_model(db: Session, payload: ModelWrite, client_id: int | None = None, action: str = "upsert") -> Model:
    resolved_specs = resolve_existing_spec_definitions(db, payload.specifications)
    brand = get_or_create_brand(db, payload.brand_code, payload.brand_name or payload.brand_code.title(), payload.brand_name)
    product_type = get_or_create_product_type(db, payload.product_type)
    series = get_or_create_series(db, brand, product_type, payload.series)
    model = db.scalar(select(Model).where(Model.brand_id == brand.id, Model.model_name == payload.model_name))
    if not model:
        model = Model(brand_id=brand.id, product_type_id=product_type.id, series_id=series.id, model_name=payload.model_name, source_ref=payload.source_ref)
        db.add(model)
        db.flush()
    model.product_type_id = product_type.id
    model.series_id = series.id
    model.title = payload.title or payload.model_name
    model.platform_vendor = payload.platform_vendor
    model.generation = payload.generation
    model.source_ref = payload.source_ref
    model.raw_source_id = payload.raw_source_id
    model.lifecycle_status = payload.lifecycle_status
    replace_business_tags(db, model, payload.business_tags)
    model.status = "active"
    model.deleted_at = None
    write_spec_values(db, model, payload.specifications, resolved_specs)
    db.add(AuditLog(api_client_id=client_id, action=action, entity_type="model", entity_id=model.id, payload=payload.model_dump()))
    db.commit()
    db.refresh(model)
    return model


def create_model_with_existing_catalog(db: Session, payload: ModelWrite, client_id: int | None = None) -> Model:
    resolved_specs = resolve_existing_spec_definitions(db, payload.specifications)
    brand = resolve_existing_brand(db, payload.brand_code)
    product_type = resolve_existing_product_type(db, payload.product_type)
    series = get_or_create_series(db, brand, product_type, payload.series)
    existing = db.scalar(select(Model).where(Model.brand_id == brand.id, Model.model_name == payload.model_name, Model.deleted_at.is_(None)))
    if existing:
        raise HTTPException(status_code=409, detail="Model already exists")
    model = Model(
        brand_id=brand.id,
        product_type_id=product_type.id,
        series_id=series.id,
        model_name=payload.model_name,
        source_ref=payload.source_ref,
    )
    db.add(model)
    db.flush()
    model.title = payload.title or payload.model_name
    model.platform_vendor = payload.platform_vendor
    model.generation = payload.generation
    model.raw_source_id = payload.raw_source_id
    model.lifecycle_status = payload.lifecycle_status
    replace_business_tags(db, model, payload.business_tags)
    model.status = "active"
    model.deleted_at = None
    write_spec_values(db, model, payload.specifications, resolved_specs)
    replace_compatible_gpus(db, model, payload.compatible_gpu_ids, payload.source_ref)
    db.add(AuditLog(api_client_id=client_id, action="create", entity_type="model", entity_id=model.id, payload=payload.model_dump()))
    db.commit()
    db.refresh(model)
    return model


def patch_model(db: Session, model: Model, payload: ModelPatch, client_id: int) -> Model:
    resolved_specs = resolve_existing_spec_definitions(db, payload.specifications, model_id=model.id) if payload.specifications is not None else None
    data = payload.model_dump(exclude_unset=True)
    if "brand_code" in data and data["brand_code"]:
        model.brand = resolve_existing_brand(db, data["brand_code"])
        if data.get("brand_name"):
            model.brand.name = data["brand_name"]
            model.brand.source_name = data["brand_name"]
    elif "brand_name" in data and data["brand_name"]:
        model.brand.name = data["brand_name"]
        model.brand.source_name = data["brand_name"]
    if "product_type" in data and data["product_type"]:
        model.product_type = resolve_existing_product_type(db, data["product_type"])
    if "series" in data and data["series"]:
        model.series = resolve_existing_series(db, model.brand, model.product_type, data["series"])
    elif ("brand_code" in data or "product_type" in data) and model.series:
        model.series = resolve_existing_series(db, model.brand, model.product_type, model.series.name)
    for attr in ("model_name", "title", "platform_vendor", "generation", "source_ref", "raw_source_id", "status"):
        if attr in data:
            setattr(model, attr, data[attr])
    if "lifecycle_status" in data:
        model.lifecycle_status = data["lifecycle_status"]
    replace_business_tags(db, model, data.get("business_tags"))
    if payload.specifications is not None:
        write_spec_values(db, model, payload.specifications, resolved_specs)
    replace_compatible_gpus(db, model, payload.compatible_gpu_ids, data.get("source_ref") or "admin")
    db.add(AuditLog(api_client_id=client_id, action="patch", entity_type="model", entity_id=model.id, payload=data))
    db.commit()
    db.refresh(model)
    return model


def soft_delete_model(db: Session, model: Model, client_id: int) -> None:
    model.status = "deleted"
    model.deleted_at = datetime.now(timezone.utc)
    db.add(AuditLog(api_client_id=client_id, action="delete", entity_type="model", entity_id=model.id, payload={}))
    db.commit()


def replace_model_specs(db: Session, model: Model, specs: list[SpecInput], client_id: int) -> None:
    resolved_specs = resolve_existing_spec_definitions(db, specs, model_id=model.id)
    db.execute(delete(ModelSpecValue).where(ModelSpecValue.model_id == model.id))
    db.flush()
    write_spec_values(db, model, specs, resolved_specs)
    db.add(AuditLog(api_client_id=client_id, action="replace_specs", entity_type="model", entity_id=model.id, payload={"specifications": [spec.model_dump() for spec in specs]}))
    db.commit()


def active_models_query():
    return (
        select(Model)
        .options(joinedload(Model.brand), joinedload(Model.product_type), joinedload(Model.series), joinedload(Model.business_tag_rows))
        .where(Model.deleted_at.is_(None), Model.status == "active")
    )


def model_to_summary(model: Model) -> dict:
    return {
        "id": model.id,
        "brand_code": model.brand.code,
        "brand_name": model.brand.name,
        "product_type": model.product_type.name,
        "series": model.series.name,
        "model_name": model.model_name,
        "title": model.title,
        "platform_vendor": model.platform_vendor,
        "generation": model.generation,
        "status": model.status,
        "deleted_at": model.deleted_at,
        "lifecycle_status": model.lifecycle_status,
        "business_tags": business_tags_for_model(model),
        "badges": badges_for_model(model),
    }


def _gpu_memory_for_model(db: Session, model_id: int) -> str | None:
    row = db.execute(
        select(ModelSpecValue.value)
        .join(SpecDefinition, ModelSpecValue.spec_definition_id == SpecDefinition.id)
        .where(ModelSpecValue.model_id == model_id, SpecDefinition.field_key == "gpu_memory_capacity")
        .limit(1)
    ).first()
    return row[0] if row else None


def compatible_gpu_to_dict(db: Session, gpu: Model) -> dict:
    memory = _gpu_memory_for_model(db, gpu.id)
    return {"id": gpu.id, "model_name": gpu.model_name, "title": gpu.title or "", "brand_code": gpu.brand.code, "product_type": gpu.product_type.name, "series": gpu.series.name, "memory": memory, "display_name": f"{gpu.model_name}（{memory}）" if memory else gpu.model_name}


def compatible_gpus_for_model(db: Session, model_id: int) -> list[dict]:
    rows = db.scalars(select(Model).join(ModelCompatibleGpu, ModelCompatibleGpu.gpu_model_id == Model.id).options(joinedload(Model.brand), joinedload(Model.product_type), joinedload(Model.series), joinedload(Model.business_tag_rows)).where(ModelCompatibleGpu.model_id == model_id, Model.deleted_at.is_(None), Model.status == "active").order_by(Model.model_name)).unique().all()
    return [compatible_gpu_to_dict(db, gpu) for gpu in rows]


def list_gpu_accessory_models(db: Session) -> list[dict]:
    rows = db.scalars(active_models_query().join(Brand, Model.brand_id == Brand.id).join(ProductType, Model.product_type_id == ProductType.id).where(func.lower(Brand.code) == "accessory", ProductType.name == "显卡").order_by(Model.model_name)).unique().all()
    return [compatible_gpu_to_dict(db, gpu) for gpu in rows]


def replace_compatible_gpus_atomic(db: Session, model: Model, gpu_ids: list[int], client_id: int | None, source_ref: str = "admin") -> None:
    """Validate first, then replace links and audit in one transaction."""
    try:
        replace_compatible_gpus(db, model, gpu_ids, source_ref)
        db.add(AuditLog(api_client_id=client_id, action="replace_compatible_gpus", entity_type="model", entity_id=model.id, payload={"compatible_gpu_ids": list(dict.fromkeys(gpu_ids))}))
        db.commit()
    except Exception:
        db.rollback()
        raise


def replace_compatible_gpus(db: Session, model: Model, gpu_ids: list[int] | None, source_ref: str = "admin") -> None:
    if gpu_ids is None:
        return
    # 配件-显卡本身是兼容显卡数据源，禁止再给显卡配件绑定“兼容显卡”，避免递归/语义混乱。
    if model.brand and model.product_type and model.brand.code.lower() == "accessory" and model.product_type.name == "显卡":
        if gpu_ids:
            raise HTTPException(status_code=400, detail="GPU accessory models are the compatibility data source and cannot have compatible GPUs")
        db.execute(delete(ModelCompatibleGpu).where(ModelCompatibleGpu.model_id == model.id))
        return
    if model.id in gpu_ids:
        raise HTTPException(status_code=400, detail="compatible_gpu_ids must not contain the model itself")
    cleaned = list(dict.fromkeys(gpu_ids))
    if cleaned:
        valid_ids = set(db.scalars(select(Model.id).join(Brand, Model.brand_id == Brand.id).join(ProductType, Model.product_type_id == ProductType.id).where(Model.id.in_(cleaned), Model.deleted_at.is_(None), Model.status == "active", func.lower(Brand.code) == "accessory", ProductType.name == "显卡")).all())
        invalid = [gid for gid in cleaned if gid not in valid_ids]
        if invalid:
            raise HTTPException(status_code=400, detail=f"compatible_gpu_ids contains non-GPU accessory model ids: {invalid}")
    db.execute(delete(ModelCompatibleGpu).where(ModelCompatibleGpu.model_id == model.id))
    for gid in cleaned:
        db.add(ModelCompatibleGpu(model_id=model.id, gpu_model_id=gid, source_ref=source_ref))


def specs_for_model(db: Session, model_id: int) -> list[dict]:
    rows = db.scalars(
        select(ModelSpecValue)
        .options(joinedload(ModelSpecValue.definition).joinedload(SpecDefinition.group))
        .join(SpecDefinition)
        .join(SpecGroup)
        .where(ModelSpecValue.model_id == model_id)
        .order_by(SpecGroup.sort_order, SpecDefinition.sort_order, SpecDefinition.label)
    ).all()
    result = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        # 历史导入可能留下空串；读取侧兜底避免空规格渲染，数据库清理由迁移负责。
        if not (row.value or "").strip():
            continue
        rendered_key = (row.definition.group.name, row.definition.label, row.value)
        if rendered_key in seen:
            continue
        seen.add(rendered_key)
        result.append(
            {
                "group_code": row.definition.group.code,
                "group_name": row.definition.group.name,
                "field_key": row.definition.field_key,
                "label": row.definition.label,
                "value": row.value,
                "raw_label": row.raw_label,
                "source_ref": row.source_ref,
                "confidence": row.confidence,
            }
        )
    return result


def spec_definitions_query():
    return (
        select(SpecDefinition, SpecGroup)
        .join(SpecGroup, SpecDefinition.group_id == SpecGroup.id)
        .order_by(SpecGroup.sort_order, SpecDefinition.sort_order, SpecDefinition.label)
    )


def spec_definition_to_dict(spec: SpecDefinition, group: SpecGroup) -> dict:
    return {
        "id": spec.id,
        "group_id": group.id,
        "group_code": group.code,
        "group_name": group.name,
        "field_key": spec.field_key,
        "label": spec.label,
        "sort_order": spec.sort_order,
    }


def spec_groups_with_fields(db: Session) -> list[dict]:
    groups = db.scalars(select(SpecGroup).order_by(SpecGroup.sort_order, SpecGroup.name)).all()
    definitions = db.scalars(
        select(SpecDefinition)
        .join(SpecGroup)
        .order_by(SpecGroup.sort_order, SpecDefinition.sort_order, SpecDefinition.label)
    ).all()
    by_group: dict[int, list[dict]] = {group.id: [] for group in groups}
    for spec in definitions:
        by_group.setdefault(spec.group_id, []).append(
            {"id": spec.id, "field_key": spec.field_key, "label": spec.label, "sort_order": spec.sort_order}
        )
    return [
        {"id": group.id, "code": group.code, "name": group.name, "sort_order": group.sort_order, "fields": by_group.get(group.id, [])}
        for group in groups
    ]


def update_spec_definition(db: Session, spec_id: int, payload: SpecDefinitionPatch) -> SpecDefinition:
    spec = db.get(SpecDefinition, spec_id)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec definition not found")
    if payload.group_id is not None or payload.group_code is not None:
        spec.group_id = resolve_spec_group(db, group_id=payload.group_id, group_code=payload.group_code).id
    if payload.label is not None:
        label = payload.label.strip()
        if not label:
            raise HTTPException(status_code=400, detail="label must not be empty")
        spec.label = label[:128]
    if payload.sort_order is not None:
        spec.sort_order = payload.sort_order
    db.commit()
    db.refresh(spec)
    return spec
