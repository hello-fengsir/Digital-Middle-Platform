import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from hashlib import sha256

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AiProviderConfig, AuditLog, Model
from app.catalog import active_models_query, compatible_gpus_for_model, model_to_summary, specs_for_model
from app.model_matching import model_name_match_rank, positive_model_text_match
from app.ai_agent_rule import provider_system_messages


_AI_SEMAPHORE = threading.BoundedSemaphore(max(1, settings.ai_max_concurrency))
PUBLIC_AI_WARNING = "AI上游暂时不可用，已返回本地资料库匹配结果。"
AI_USED_WITH_EVIDENCE = "ai_used_with_evidence"
AI_USED_NO_EVIDENCE_REFUSAL = "ai_used_no_evidence_refusal"
AI_PROVIDER_FAILED = "ai_provider_failed"
AI_NOT_AVAILABLE = "ai_not_available"
NO_EVIDENCE_REFUSAL = "本地检索暂无可核验证据，不能给出型号或参数建议。"
UNPARSED_REFUSAL = "需求中存在未解析条件，请补充或改写后再试。"


def _xor_secret(value: str) -> str:
    secret = (settings.admin_session_secret or settings.api_key or "hpl-local-secret").encode()
    data = value.encode()
    return "".join(f"{b ^ secret[i % len(secret)]:02x}" for i, b in enumerate(data))


def _xor_unsecret(value: str) -> str:
    if not value:
        return ""
    secret = (settings.admin_session_secret or settings.api_key or "hpl-local-secret").encode()
    raw = bytes.fromhex(value)
    return bytes(b ^ secret[i % len(secret)] for i, b in enumerate(raw)).decode()


def _get_config(db: Session) -> AiProviderConfig:
    cfg = db.scalar(select(AiProviderConfig).where(AiProviderConfig.name == "default"))
    if cfg:
        return cfg
    cfg = AiProviderConfig(
        name="default",
        base_url=settings.ai_base_url or "",
        api_key_cipher=_xor_secret(settings.ai_api_key) if settings.ai_api_key else "",
        model=settings.ai_model or "",
        temperature="0.2",
        max_tokens=1200,
        enabled=bool(settings.ai_base_url and settings.ai_api_key and settings.ai_model),
    )
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return cfg


def get_ai_config_public(db: Session) -> dict:
    cfg = _get_config(db)
    return {
        "base_url": cfg.base_url,
        "model": cfg.model,
        "temperature": float(cfg.temperature or 0.2),
        "max_tokens": cfg.max_tokens,
        "enabled": cfg.enabled,
        "has_api_key": bool(cfg.api_key_cipher),
    }


def save_ai_config(db: Session, payload) -> dict:
    cfg = _get_config(db)
    cfg.base_url = payload.base_url.strip().rstrip("/")
    cfg.model = payload.model.strip()
    cfg.temperature = str(payload.temperature)
    cfg.max_tokens = payload.max_tokens
    cfg.enabled = payload.enabled
    if payload.api_key is not None and payload.api_key.strip():
        cfg.api_key_cipher = _xor_secret(payload.api_key.strip())
    db.commit()
    return get_ai_config_public(db)


def delete_ai_provider_api_key(db: Session, actor: str) -> dict:
    """Atomically clear the persisted default provider key and disable AI."""
    cfg = _get_config(db)
    had_api_key = bool(cfg.api_key_cipher)
    cfg.api_key_cipher = ""
    cfg.enabled = False
    db.add(AuditLog(
        api_client_id=None,
        action="delete_ai_provider_api_key",
        entity_type="ai_provider_config",
        entity_id=cfg.id,
        payload={
            "actor": str(actor or "unknown")[:128],
            "had_api_key": had_api_key,
        },
    ))
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return get_ai_config_public(db)


def _effective_ai(db: Session, override=None) -> tuple[str, str, str, float, int, bool]:
    cfg = _get_config(db)
    base_url = ((getattr(override, "base_url", None) or cfg.base_url or settings.ai_base_url or "").strip().rstrip("/"))
    model = ((getattr(override, "model", None) or cfg.model or settings.ai_model or "").strip())
    override_key = getattr(override, "api_key", None) if override else None
    if override_key:
        api_key = override_key.strip()
    elif cfg.api_key_cipher:
        api_key = _xor_unsecret(cfg.api_key_cipher)
    else:
        # An existing row is authoritative: an empty cipher means no key.
        api_key = ""
    return base_url, api_key, model, float(cfg.temperature or 0.2), int(cfg.max_tokens or 1200), bool(cfg.enabled)


def _chat_completion(base_url: str, api_key: str, model: str, messages: list[dict], temperature: float = 0.2, max_tokens: int = 1200) -> str:
    if not base_url or not api_key or not model:
        raise HTTPException(status_code=400, detail="AI配置不完整")
    url = base_url.rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"
    # Load the fixed bind-mounted rule immediately before every provider call.
    # A second system message keeps catalog decisions outside editable prose.
    messages = [*provider_system_messages(), *messages]
    body = json.dumps({"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}, ensure_ascii=False).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}, method="POST")
    total_timeout = max(1.0, float(settings.ai_total_timeout_seconds))
    started = time.monotonic()
    if not _AI_SEMAPHORE.acquire(timeout=total_timeout):
        raise HTTPException(status_code=503, detail="AI服务繁忙，请稍后重试")
    try:
        remaining = max(1.0, total_timeout - (time.monotonic() - started))
        with urllib.request.urlopen(req, timeout=remaining) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"AI上游返回错误（HTTP {exc.code}）") from None
    except (TimeoutError, urllib.error.URLError):
        raise HTTPException(status_code=504, detail="AI上游连接或响应超时") from None
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        raise HTTPException(status_code=502, detail="AI上游响应格式异常") from None
    except Exception:
        raise HTTPException(status_code=502, detail="AI上游调用失败") from None
    finally:
        _AI_SEMAPHORE.release()
    return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()


def test_ai_config(db: Session, payload) -> dict:
    base_url, api_key, model, temperature, max_tokens, _enabled = _effective_ai(db, payload)
    text = _chat_completion(base_url, api_key, model, [{"role": "user", "content": "回复：天枢 TenSpur AI OK"}], temperature, min(max_tokens, 64))
    return {"ok": True, "message": text[:200]}


BRAND_ALIASES = {
    "lenovo": ("联想", "lenovo", "thinkstation", "thinksystem", "开天"),
    "inspur": ("浪潮", "inspur", "ieit", "浪潮信息"),
    "dell": ("戴尔", "dell"),
    "generic": ("示例品牌", "generic"),
}
BRAND_NAMES = {"lenovo": "联想", "inspur": "浪潮", "dell": "戴尔", "generic": "示例品牌"}
TYPE_ALIASES = {
    "服务器": ("服务器", "server"),
    "工作站": ("工作站", "workstation", "thinkstation"),
    "显卡": ("显卡", "gpu卡", "gpu card", "加速卡"),
}
DOMAIN_CONCEPTS = {
    "dual_socket": ("双路", "两路", "2路", "双插槽", "双cpu", "2颗cpu", "两颗cpu", "dual socket"),
    "gpu_expansion": ("gpu扩展", "显卡扩展", "gpu扩展能力", "pcie扩展", "pci-e扩展", "扩展槽"),
}
UNKNOWN_MARKERS = ("待补充", "无法验证", "未提供", "未确认", "不做推断", "未知")


def _contains_alias(text: str, aliases: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(alias.lower() in lowered for alias in aliases)


def _model_name_match_strength(message: str, model_name: str) -> int:
    return model_name_match_rank(message, model_name) // 100


def _explicit_brands(message: str) -> list[str]:
    return [code for code, aliases in BRAND_ALIASES.items() if _contains_alias(message, aliases)]


def _explicit_types(message: str) -> list[str]:
    return [name for name, aliases in TYPE_ALIASES.items() if _contains_alias(message, aliases)]


def _clip(value: str, limit: int = 320) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def _condition(kind: str, value, unit: str | None, label: str, *, width: str | None = None, operator: str | None = None, generation: int | None = None, lanes: int | None = None) -> dict:
    condition = {"id": f"c{len(label)}-{kind}-{value}", "kind": kind, "operator": operator or ("gte" if kind in {"memory_capacity", "pcie_slots", "gpu_count"} else "eq"), "value": value, "unit": unit, "label": label}
    if kind == "gpu_count":
        condition["width"] = width
    if kind in {"pcie_interface", "gpu_interface"}:
        condition.update({"generation": generation, "lanes": lanes})
    return condition


def _negative_clauses(message: str) -> list[tuple[int, int, str]]:
    pattern = re.compile(r"(?:明确不支持|不支持|不接受|不要|排除|不能|必须不是)\s*[^，。；;]*", re.I)
    return [(match.start(), match.end(), match.group(0).strip()) for match in pattern.finditer(message)]


def _mask_negative_clauses(message: str) -> str:
    chars = list(message)
    for start, end, _clause in _negative_clauses(message):
        chars[start:end] = " " * (end - start)
    return "".join(chars)


def _pcie_tuple(text: str) -> tuple[int | None, int] | None:
    match = re.search(r"PCI\s*-?\s*E\s*(?:(?:GEN(?:ERATION)?\s*)?(\d+)(?:\.0)?\s*)?[x×]\s*(\d+)", text, re.I)
    if not match:
        return None
    return (int(match.group(1)) if match.group(1) else None, int(match.group(2)))


def _extract_hard_conditions(message: str) -> list[dict]:
    """Only explicit positive clauses are parsed; negative spans are handled later."""
    positive_message = _mask_negative_clauses(message)
    # PCIe descriptors are parsed in their own field scope and masked from counts/models.
    interfaces = list(re.finditer(r"PCI\s*-?\s*E\s*(?:(?:GEN(?:ERATION)?\s*)?(\d+)(?:\.0)?\s*)?[x×]\s*(\d+)", positive_message, re.I))
    text = positive_message
    for interface in reversed(interfaces):
        text = text[:interface.start()] + " " * (interface.end() - interface.start()) + text[interface.end():]
    conditions: list[dict] = []
    memory = re.search(
        r"(?:最大内存容量|内存(?:容量)?)(?:\s|[:：,，]){0,4}(?:至少|不低于|>=|≥|最低|最少|达到|支持|最大|最高)?\s*(\d+(?:\.\d+)?)\s*(TB|GB|T|G)(?!\s*(?:/|每)\s*s\b)",
        text,
        re.I,
    )
    if not memory:
        memory = re.search(
            r"(?:至少|不低于|>=|≥|最低|最少)\s*(\d+(?:\.\d+)?)\s*(TB|GB|T|G)\s*(?:的)?\s*内存(?:容量)?",
            text,
            re.I,
        )
    if memory:
        unit = "TB" if memory.group(2).upper() in {"TB", "T"} else "GB"
        value = float(memory.group(1))
        conditions.append(_condition("memory_capacity", value, unit, f"内存至少{value:g}{unit}"))
    pcie = re.search(r"(?:至少|不低于|>=|≥|最少|支持)?\s*(\d+)\s*(?:个|条)?\s*(?:PCI[- ]?E(?:\s*扩展)?槽|PCI[- ]?E|扩展槽)", text, re.I)
    if not pcie:
        pcie = re.search(r"(?:PCI[- ]?E(?:\s*扩展)?槽|扩展槽).{0,8}?(?:至少|不低于|>=|≥|最少|支持)?\s*(\d+)\s*(?:个|条)?", text, re.I)
    if pcie:
        value = int(pcie.group(1))
        conditions.append(_condition("pcie_slots", value, "slot", f"PCIe插槽至少{value}个"))
    if re.search(r"(?:1\s*\+\s*1|双)\s*(?:冗余)?\s*电源|电源.{0,8}(?:1\s*\+\s*1|双电源|冗余)", text, re.I):
        conditions.append(_condition("redundant_power", "1+1", None, "双电源/1+1冗余"))
    if _contains_alias(text, DOMAIN_CONCEPTS["dual_socket"]):
        conditions.append(_condition("dual_socket", 2, "socket", "双路CPU"))
    for interface in interfaces:
        generation = int(interface.group(1)) if interface.group(1) else None
        lanes = int(interface.group(2))
        context = positive_message[max(0, interface.start() - 28):interface.end() + 28]
        gpu_scoped = bool(re.search(r"(?:GPU|显卡|加速卡)\s*(?:接口|总线)?[^，。；;]{0,16}$", positive_message[max(0, interface.start() - 28):interface.start()], re.I)
                          or re.match(r"[^，。；;]{0,16}(?:接口)?\s*(?:的)?\s*(?:GPU|显卡|加速卡)", positive_message[interface.end():interface.end() + 28], re.I))
        server_pcie_scoped = bool(re.search(r"(?:服务器|PCIe接口|PCI-E接口|扩展接口|扩展槽|总线)", context, re.I))
        if not gpu_scoped and not server_pcie_scoped:
            continue
        kind = "gpu_interface" if gpu_scoped else "pcie_interface"
        value = f"PCIe Gen{generation} x{lanes}" if generation else f"PCIe x{lanes}"
        label = ("GPU接口" if gpu_scoped else "服务器PCIe接口") + value
        conditions.append(_condition(kind, value, None, label, generation=generation, lanes=lanes))
    if _contains_alias(text, DOMAIN_CONCEPTS["gpu_expansion"]):
        conditions.append(_condition("gpu_expansion", True, None, "GPU扩展能力"))

    gpu_model_match = None
    gpu_patterns = (
        r"(?:NVIDIA|英伟达)\s+([A-Za-z][A-Za-z0-9-]{1,19}\d[A-Za-z0-9-]*)",
        r"(?:支持|配备|可配|要求)\s*([A-Za-z][A-Za-z0-9-]{1,19}\d[A-Za-z0-9-]*)(?=\s|[,，。;；]|$)",
        r"(?:支持|配备|可配)?\s*([A-Za-z][A-Za-z0-9-]{1,19}\d[A-Za-z0-9-]*)\s*(?:GPU|显卡|加速卡)",
        r"([A-Za-z][A-Za-z0-9-]{1,19}\d[A-Za-z0-9-]*)\s*(?:GPU)?\s*[x×]\s*\d+",
        r"(?:双|\d+\s*(?:张|块|卡|个))\s*([A-Za-z][A-Za-z0-9-]{1,19}\d[A-Za-z0-9-]*)",
        r"(?:GPU|显卡|加速卡)(?:\s|[:：]){0,3}(?:支持|型号|为|可配)?\s*([A-Za-z][A-Za-z0-9-]{1,19}\d[A-Za-z0-9-]*)",
    )
    for pattern in gpu_patterns:
        gpu_model_match = re.search(pattern, text, re.I)
        if gpu_model_match:
            break
    if gpu_model_match:
        gpu_model = gpu_model_match.group(1).upper()
        if not re.fullmatch(r"(?:PCIE?|GEN(?:ERATION)?\d*|X\d+)", gpu_model, re.I):
            conditions.append(_condition("gpu_model", gpu_model, None, f"GPU型号{gpu_model}"))

    gpu_count = None
    gpu_width = None
    gpu_count_patterns = (
        r"[A-Za-z][A-Za-z0-9-]{1,19}\d[A-Za-z0-9-]*\s*(?:GPU)?\s*[x×]\s*(\d+)\s*(双宽|单宽)?",
        r"(\d+)\s*(?:张|块|卡|个)\s*(双宽|单宽)?\s*[A-Za-z][A-Za-z0-9-]{1,19}\d[A-Za-z0-9-]*",
        r"(?:支持|最多|至少|可配|最高支持)\s*(\d+)\s*(?:张|块|卡|个|[x×])?\s*(双宽|单宽)?\s*(?:[A-Za-z][A-Za-z0-9-]*\s*)?(?:GPU|显卡|加速卡)",
        r"(?:GPU|显卡|加速卡)(?:支持|容量|数量|配置|扩展)?(?:\s|[:：]){0,4}(?:支持|最多|至少|可配|最高)?\s*(\d+)\s*(?:张|块|卡|个|[x×])?\s*(双宽|单宽)?",
        r"(?:GPU|显卡|加速卡).{0,12}?(\d+)\s*[x×]\s*(双宽|单宽)",
        r"(\d+)\s*[x×]\s*(双宽|单宽)\s*(?:GPU|显卡|加速卡)",
    )
    for pattern in gpu_count_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            gpu_count = int(match.group(1))
            width_token = match.group(2) if match.lastindex and match.lastindex >= 2 else ""
            gpu_width = "double" if width_token == "双宽" else "single" if width_token == "单宽" else None
            break
    if gpu_model_match and re.search(r"双\s*" + re.escape(gpu_model_match.group(1)), text, re.I):
        gpu_count = 2
        gpu_width = None
    if gpu_count is not None and 1 <= gpu_count <= 64:
        width_label = "双宽" if gpu_width == "double" else "单宽" if gpu_width == "single" else ""
        conditions.append(_condition("gpu_count", gpu_count, "card", f"GPU至少{gpu_count}张{width_label}", width=gpu_width))

    # Every item in a negative list inherits the same exclusion semantics.
    for _start, _end, clause in _negative_clauses(message):
        body = re.sub(r"^(?:明确不支持|不支持|不接受|不要|排除|不能|必须不是)\s*", "", clause, flags=re.I)
        if _contains_alias(body, DOMAIN_CONCEPTS["dual_socket"]):
            conditions.append(_condition("dual_socket", 2, "socket", "排除双路CPU", operator="exclude_eq"))
        for token in re.findall(r"[A-Za-z][A-Za-z0-9-]{1,30}\d[A-Za-z0-9-]*", body, re.I):
            value = token.upper()
            if re.fullmatch(r"(?:PCIE?|GEN(?:ERATION)?\d*|X\d+|CPU)", value, re.I):
                continue
            conditions.append(_condition("gpu_model", value, None, f"排除GPU型号{value}", operator="exclude_eq"))
        alternatives = re.findall(r"(\d+)\s*(?:个|张|块|卡)?\s*(单宽|双宽)(?:\s*(?:GPU|显卡|加速卡))?", body, re.I)
        for count, width_token in alternatives:
            width = "double" if width_token == "双宽" else "single"
            conditions.append(_condition("gpu_count", int(count), "card", f"排除{count}个{width_token}GPU配置", width=width, operator="exclude_eq"))
    return list({(c["kind"], str(c["value"]), c["unit"], c["operator"], c.get("width")): c for c in conditions}.values())


def _unparsed_conditions(message: str, conditions: list[dict]) -> list[str]:
    result: list[str] = []
    for _start, _end, clause in _negative_clauses(message):
        body = re.sub(r"^(?:明确不支持|不支持|不接受|不要|排除|不能|必须不是)\s*", "", clause, flags=re.I)
        structured = (_contains_alias(body, DOMAIN_CONCEPTS["dual_socket"])
                      or bool(re.search(r"[A-Za-z][A-Za-z0-9-]{1,30}\d[A-Za-z0-9-]*", body, re.I))
                      or bool(re.search(r"\d+\s*(?:个|张|块|卡)?\s*(?:单宽|双宽)", body)))
        if not structured:
            result.append(clause)
    # Capability-looking requirements that have no deterministic parser must block
    # catalog fallback and recommendation actions (e.g. hot-swap fans / IPMI).
    positive = _mask_negative_clauses(message)
    parsed_kinds = {condition["kind"] for condition in conditions if not condition["operator"].startswith("exclude")}
    capabilities = (
        (r"热插拔\s*风扇", "hot_swap_fan"),
        (r"(?<![A-Za-z0-9])IPMI(?![A-Za-z0-9])", "ipmi"),
        (r"(?:带外|远程)管理", "management"),
    )
    for pattern, kind in capabilities:
        match = re.search(pattern, positive, re.I)
        if match and kind not in parsed_kinds:
            result.append(match.group(0))
    return list(dict.fromkeys(result))


def _spec_text(spec: dict) -> str:
    return f"{spec.get('field_key', '')} {spec.get('label', '')} {spec.get('value', '')}"


def _usable(spec: dict) -> bool:
    value = str(spec.get("value", ""))
    return bool(value.strip()) and not any(marker in value for marker in UNKNOWN_MARKERS)


def _memory_spec(spec: dict) -> bool:
    identity = f"{spec.get('group_name', '')} {spec.get('label', '')} {spec.get('field_key', '')}".lower()
    if re.search(r"gpu|显存|video\s*memory|graphics", identity, re.I):
        return False
    return bool(
        re.search(r"内存", str(spec.get("group_name", "")), re.I)
        or re.search(r"^(?:最大|最高)?内存(?:最大)?容量$|^内存$", str(spec.get("label", "")).strip(), re.I)
        or str(spec.get("field_key", "")).lower() in {"memory", "memory_capacity", "memory_max_capacity", "max_memory_capacity"}
    )


def _memory_capacities_gb(spec: dict) -> list[float]:
    """Parse plausible capacity tokens only from explicitly memory-scoped evidence."""
    if not _memory_spec(spec):
        return []
    text = str(spec.get("value", ""))
    values: list[float] = []
    for match in re.finditer(r"(?<![A-Za-z0-9.])(\d+(?:\.\d+)?)\s*(TB|GB|T|G)\b", text, re.I):
        suffix = text[match.end():match.end() + 12]
        prefix = text[max(0, match.start() - 12):match.start()]
        if re.match(r"\s*(?:/|每)\s*s\b", suffix, re.I):
            continue
        if re.search(r"(?:速率|带宽)\s*[:：]?\s*$", prefix, re.I):
            continue
        value = float(match.group(1)) * (1024 if match.group(2).upper() in {"TB", "T"} else 1)
        if 1 <= value <= 64 * 1024:
            values.append(value)
    return values


def _slot_counts(text: str) -> list[int]:
    patterns = (
        r"(\d+)\s*(?:个|条)?\s*(?:PCI[- ]?E(?:\s*扩展)?槽|PCI[- ]?E|扩展槽)",
        r"(?:PCI[- ]?E(?:\s*扩展)?槽|扩展槽).{0,12}?(\d+)\s*(?:个|条)?",
    )
    return [int(v) for pattern in patterns for v in re.findall(pattern, text, re.I)]


def _gpu_model_evidence(db: Session, model: Model, specs: list[dict]) -> list[str]:
    """型号证据可来自明确 GPU 字段或兼容关系，但不携带数量语义。"""
    lines = [f"{s['group_name']}·{s['label']}：{s['value']}" for s in specs if _usable(s) and re.search(r"gpu|显卡|加速卡", _spec_text(s), re.I)]
    for gpu in compatible_gpus_for_model(db, model.id):
        lines.append(f"兼容显卡（本地关系）：{gpu['model_name']}")
    return lines


def _gpu_count_spec(spec: dict) -> bool:
    """数量只接受字段身份明确的整机 GPU 支持字段。"""
    field_key = str(spec.get("field_key", "")).strip().lower()
    label = re.sub(r"\s+", "", str(spec.get("label", ""))).upper()
    return field_key == "gpu_support" or bool(re.fullmatch(r"(?:整机)?(?:GPU|显卡)支持", label, re.I))


def _gpu_count_from_support_spec(spec: dict, width: str | None = None) -> list[int]:
    """拒绝从兼容型号、PCIe x16、算力、显存和其他配件数字推导整机卡数。"""
    if not _usable(spec) or not _gpu_count_spec(spec):
        return []
    # Positive capacity and explicit absence are separate facts. A phrase such as
    # “最高支持4个双宽GPU；明确不支持3个双宽GPU” must not turn the excluded
    # three-card configuration into positive capacity evidence.
    value = re.sub(
        r"(?:明确不支持|不支持|不可|不能|无法|无)\s*[^，。；;]*",
        " ",
        str(spec.get("value", "")),
        flags=re.I,
    )
    support = r"(?:最高\s*)?支持|最多|可配|最大"
    counts: list[tuple[int, str | None]] = []
    patterns = (
        rf"(?:{support}).{{0,8}}?(\d+)\s*(?:张|块|卡|个)?\s*(双宽|单宽)?.{{0,32}}?(?:GPU|显卡|加速卡)",
        rf"(?:GPU|显卡|加速卡).{{0,12}}?(?:{support}).{{0,8}}?(\d+)\s*(?:张|块|卡|个)?\s*(双宽|单宽)?",
    )
    for pattern in patterns:
        counts.extend((int(token), {"双宽": "double", "单宽": "single"}.get(token_width)) for token, token_width in re.findall(pattern, value, re.I))
    if re.search(r"GPU|显卡|加速卡", value, re.I):
        counts.extend((int(token), {"双宽": "double", "单宽": "single"}[token_width]) for token, token_width in re.findall(r"(\d+)\s*(?:张|块|卡|个|[x×])?\s*(双宽|单宽)(?=\s*(?:GPU|显卡|加速卡))", value, re.I))
    # 同一数字可能被支持语句和宽度语句同时捕获；去重后保留互斥选项各自的容量。
    unique_counts = list(dict.fromkeys(counts))
    return [count for count, token_width in unique_counts if 1 <= count <= 64 and (width is None or token_width == width)]


def _dual_socket_spec(spec: dict) -> bool:
    group = re.sub(r"\s+", "", str(spec.get("group_name", ""))).lower()
    key = str(spec.get("field_key", "")).strip().lower()
    label = re.sub(r"\s+", "", str(spec.get("label", ""))).lower()
    if key in {"selection_notes", "memory", "memory_capacity", "memory_max_capacity"} or "内存" in group or "内存" in label:
        return False
    explicit_keys = {"cpu", "cpu_count", "cpu_socket", "cpu_sockets", "processor", "processor_count", "processor_socket", "socket_count"}
    explicit_label = bool(re.fullmatch(r"(?:cpu|处理器)(?:数量|个数|插槽|插槽数|socket)?|(?:cpu|处理器)?插槽(?:数|数量)?", label, re.I))
    return group in {"处理器", "processor", "cpu"} or key in explicit_keys or explicit_label


def _interface_spec(spec: dict, kind: str) -> bool:
    identity = _spec_text(spec).lower()
    key = str(spec.get("field_key", "")).strip().lower()
    group = re.sub(r"\s+", "", str(spec.get("group_name", ""))).lower()
    label = re.sub(r"\s+", "", str(spec.get("label", ""))).lower()
    metadata = f"{group} {label}"
    # An explicit server PCIe key owns the field even if an old dictionary maps it
    # into a broad GPU display group. Conversely, explicit GPU keys stay GPU-scoped.
    if key in {"gpu_interface", "gpu_bus", "gpu_pcie_interface"}:
        gpu_owned = True
    elif key in {"pcie_interface", "pcie", "pcie_slots"}:
        gpu_owned = bool(re.search(r"gpu|显卡|加速卡", metadata, re.I)) and not bool(re.search(r"服务器|整机", str(spec.get("value", "")), re.I))
    else:
        gpu_owned = bool(re.search(r"gpu|显卡|加速卡", metadata, re.I))
    if kind == "gpu_interface":
        return gpu_owned and bool(re.search(r"pcie|pci-e|接口|bus|总线", identity, re.I))
    if gpu_owned:
        return False

    # Server PCIe evidence is deliberately metadata-scoped. A value mentioning
    # “PCIe x16” cannot turn a network/OCP, storage/RAID, or GPU field into
    # motherboard expansion-slot evidence.
    foreign_field = bool(re.search(r"网络|网卡|网络接口|\bnetwork\b|\bnic\b|\bocp\b|存储|阵列|\braid\b|显卡|加速卡|\bgpu\b", metadata, re.I))
    if foreign_field:
        return False

    explicit_server_key = key in {"pcie_interface", "pcie", "pcie_slots"}
    expansion_group = (
        bool(re.search(r"pcie|pci-e", group, re.I) and re.search(r"扩展|插槽|slot", group, re.I))
        or group in {"扩展", "扩展槽", "标准pcie插槽", "pcie", "pci-e"}
    )
    return explicit_server_key or expansion_group


def _explicit_absence_evidence(specs: list[dict], condition: dict) -> str | None:
    """Absence is confirmed only by an explicit model-local non-support statement."""
    kind = condition["kind"]
    wanted = str(condition["value"])
    for spec in specs:
        if not _usable(spec):
            continue
        text = str(spec.get("value", ""))
        if not re.search(r"(?:明确不支持|不支持|不可|不能|无法|无)\s*", text, re.I):
            continue
        if kind == "dual_socket" and _dual_socket_spec(spec) and _contains_alias(text, DOMAIN_CONCEPTS["dual_socket"]):
            return f"{spec['group_name']}·{spec['label']}：{_clip(text)}"
        if kind == "gpu_model" and re.search(r"gpu|显卡|加速卡", _spec_text(spec), re.I) and model_name_match_rank(text, wanted) > 0:
            return f"{spec['group_name']}·{spec['label']}：{_clip(text)}"
        if kind == "gpu_count" and _gpu_count_spec(spec):
            count = int(condition["value"])
            width_word = "双宽" if condition.get("width") == "double" else "单宽" if condition.get("width") == "single" else ""
            if re.search(rf"(?:明确不支持|不支持|不可|不能|无法|无)[^，。；;]{{0,16}}{count}\s*(?:个|张|块|卡)?\s*{width_word}", text, re.I):
                return f"{spec['group_name']}·{spec['label']}：{_clip(text)}"
    return None


def _evaluate_condition(db: Session, model: Model, specs: list[dict], condition: dict) -> dict:
    kind = condition["kind"]
    evidence = None
    actual = None
    if kind == "memory_capacity":
        required = float(condition["value"]) * (1024 if condition["unit"] == "TB" else 1)
        for spec in specs:
            if _usable(spec) and _memory_spec(spec):
                capacities = _memory_capacities_gb(spec)
                if capacities and max(capacities) >= required:
                    evidence, actual = f"{spec['group_name']}·{spec['label']}：{_clip(spec['value'])}", max(capacities)
                    break
    elif kind == "pcie_slots":
        for spec in specs:
            if _usable(spec) and re.search(r"pcie|pci-e|扩展槽", _spec_text(spec), re.I):
                counts = _slot_counts(spec["value"])
                if counts and max(counts) >= int(condition["value"]):
                    evidence, actual = f"{spec['group_name']}·{spec['label']}：{_clip(spec['value'])}", max(counts)
                    break
    elif kind == "redundant_power":
        for spec in specs:
            if _usable(spec) and re.search(r"power|电源", _spec_text(spec), re.I) and re.search(r"1\s*\+\s*1|双.{0,8}电源|冗余", spec["value"], re.I):
                evidence, actual = f"{spec['group_name']}·{spec['label']}：{_clip(spec['value'])}", "1+1/redundant"
                break
    elif kind == "dual_socket":
        for spec in specs:
            if _usable(spec) and _dual_socket_spec(spec) and _contains_alias(spec["value"], DOMAIN_CONCEPTS["dual_socket"]):
                evidence, actual = f"{spec['group_name']}·{spec['label']}：{_clip(spec['value'])}", 2
                break
    elif kind in {"pcie_interface", "gpu_interface"}:
        wanted_generation = condition.get("generation")
        wanted_lanes = int(condition["lanes"])
        for spec in specs:
            if not _usable(spec) or not _interface_spec(spec, kind):
                continue
            actual_tuple = _pcie_tuple(str(spec.get("value", "")))
            if not actual_tuple:
                continue
            actual_generation, actual_lanes = actual_tuple
            if actual_lanes == wanted_lanes and (wanted_generation is None or actual_generation == wanted_generation):
                evidence = f"{spec['group_name']}·{spec['label']}：{_clip(spec['value'])}"
                actual = {"generation": actual_generation, "lanes": actual_lanes}
                break
    elif kind == "gpu_expansion":
        for spec in specs:
            if _usable(spec) and re.search(r"gpu|显卡", _spec_text(spec), re.I) and re.search(r"支持|扩展|可配|最多|最高", str(spec.get("value", "")), re.I):
                evidence, actual = f"{spec['group_name']}·{spec['label']}：{_clip(spec['value'])}", True
                break
            if _usable(spec) and re.search(r"pcie|pci-e|扩展槽", _spec_text(spec), re.I) and re.search(r"gpu|显卡", str(spec.get("value", "")), re.I):
                evidence, actual = f"{spec['group_name']}·{spec['label']}：{_clip(spec['value'])}", True
                break
    elif kind in {"gpu_model", "gpu_count"}:
        if kind == "gpu_model":
            lines = _gpu_model_evidence(db, model, specs)
            if model.product_type.name == "显卡":
                lines.insert(0, f"显卡型号：{model.model_name}")
            wanted = str(condition["value"])
            for line in lines:
                if positive_model_text_match(line, wanted):
                    evidence, actual = _clip(line), condition["value"]
                    break
        else:
            required = int(condition["value"])
            width = condition.get("width")
            operator = condition.get("operator", "gte")
            for spec in specs:
                counts = _gpu_count_from_support_spec(spec, width)
                if operator == "exclude_eq":
                    if required in counts:
                        evidence = f"{spec['group_name']}·{spec['label']}：{_clip(spec['value'])}"
                        actual = required
                        break
                elif counts and max(counts) >= required:
                    evidence = f"{spec['group_name']}·{spec['label']}：{_clip(spec['value'])}"
                    actual = max(counts)
                    break
    base = {"condition_id": condition["id"], "kind": kind, "label": condition["label"], "generation": condition.get("generation"), "lanes": condition.get("lanes")}
    if condition.get("operator") == "exclude_eq":
        if evidence is not None:
            return {**base, "satisfied": False, "status": "unsatisfied", "verification_status": "conflict", "actual": actual, "evidence": f"排除冲突：{evidence}"}
        absence = _explicit_absence_evidence(specs, condition)
        if absence:
            return {**base, "satisfied": True, "status": "satisfied", "verification_status": "confirmed", "actual": "confirmed_absence", "evidence": f"明确不支持证据：{absence}"}
        return {**base, "satisfied": False, "status": "unknown", "verification_status": "unknown", "actual": None, "evidence": None}
    status = "satisfied" if evidence is not None else "unknown"
    return {**base, "satisfied": evidence is not None, "status": status, "verification_status": "confirmed" if evidence is not None else "unknown", "actual": actual, "evidence": evidence}


def _requested_type_by_brand(message: str, requested_brands: list[str], requested_types: list[str]) -> dict[str, str]:
    """跨品牌比较时按文本邻近关系绑定品牌与类型，避免笛卡尔式错配。"""
    lowered = message.lower()
    positions: dict[str, list[int]] = {}
    for type_name in requested_types:
        positions[type_name] = [match.start() for alias in TYPE_ALIASES[type_name] for match in re.finditer(re.escape(alias.lower()), lowered)]
    result: dict[str, str] = {}
    for code in requested_brands:
        brand_positions = [match.start() for alias in BRAND_ALIASES.get(code, ()) for match in re.finditer(re.escape(alias.lower()), lowered)]
        choices = [(abs(brand_pos - type_pos), type_name) for brand_pos in brand_positions for type_name, type_positions in positions.items() for type_pos in type_positions]
        if choices:
            result[code] = min(choices, key=lambda item: item[0])[1]
    return result


def _candidate_rows(db: Session, message: str) -> tuple[list[dict], dict, list[dict]]:
    requested_brands = _explicit_brands(message)
    requested_types = _explicit_types(message)
    requested_type_by_brand = _requested_type_by_brand(message, requested_brands, requested_types) if len(requested_brands) > 1 and len(requested_types) > 1 else {}
    conditions = _extract_hard_conditions(message)
    condition_kinds = {condition["kind"] for condition in conditions}
    has_gpu_requirement = bool(condition_kinds & {"gpu_model", "gpu_count", "gpu_interface", "gpu_expansion"})
    has_server_feature = bool(condition_kinds & {"dual_socket", "memory_capacity", "pcie_slots", "pcie_interface", "redundant_power"})
    server_gpu_requirement = has_gpu_requirement and (has_server_feature or ("服务器" in requested_types and "工作站" not in requested_types))
    pure_gpu_lookup = condition_kinds in ({"gpu_model"}, {"gpu_interface"}) and not requested_brands and not has_server_feature
    active_models = db.scalars(active_models_query().where((Model.lifecycle_status.is_(None)) | (Model.lifecycle_status.notin_(("eos", "eol")))).order_by(Model.id)).unique().all()
    # Once any complete model identity is present, it is the strongest recall scope;
    # brand/type metadata must not append unrelated catalog rows.
    has_exact_model_scope = not conditions and any(_model_name_match_strength(message, item.model_name) > 0 for item in active_models)
    rows: list[dict] = []
    for model in active_models:
        if has_exact_model_scope and _model_name_match_strength(message, model.model_name) == 0:
            continue
        code = model.brand.code.lower()
        if requested_brands and code not in requested_brands:
            continue
        if requested_types and model.product_type.name not in requested_types:
            continue
        if requested_type_by_brand.get(code) and model.product_type.name != requested_type_by_brand[code]:
            continue
        if server_gpu_requirement and model.product_type.name != "服务器":
            continue
        if pure_gpu_lookup and model.product_type.name != "显卡":
            continue
        specs = specs_for_model(db, model.id)
        matrix = [_evaluate_condition(db, model, specs, condition) for condition in conditions]
        # A proven exclusion conflict is removed. Unknown absence remains visible
        # only when another positive hard condition independently earns candidacy.
        if any(result["status"] == "unsatisfied" for result, condition in zip(matrix, conditions) if condition["operator"].startswith("exclude")):
            continue
        satisfied_count = sum(item["status"] == "satisfied" for item in matrix)
        positive_hits = sum(item["status"] == "satisfied" for item, condition in zip(matrix, conditions) if not condition["operator"].startswith("exclude"))
        # 排除项本身不创造候选；至少一个正向条件必须有本地证据。
        if conditions and positive_hits:
            rows.append({"model": model, "condition_results": matrix, "fully_matched": satisfied_count == len(conditions), "satisfied_count": satisfied_count})
        elif not conditions:
            model_strength = _model_name_match_strength(message, model.model_name)
            has_unverified_concept = any(_contains_alias(message, aliases) for aliases in DOMAIN_CONCEPTS.values())
            # 无硬条件只允许明确型号或“纯品牌+类型”；额外能力要求不能被类型元数据冒充证据。
            deterministic_scope = model_strength > 0 or (bool(requested_types) and not has_unverified_concept)
            if deterministic_scope:
                rows.append({
                    "model": model,
                    "condition_results": [],
                    "fully_matched": True,
                    "satisfied_count": model_strength + (1 if requested_types else 0),
                })
    rows.sort(key=lambda row: (-int(row["fully_matched"]), -row["satisfied_count"], row["model"].id))

    selected: list[dict] = []
    brand_order = requested_brands or list(dict.fromkeys(row["model"].brand.code.lower() for row in rows))
    quota = max(1, 6 // max(1, len(brand_order)))
    for code in brand_order:
        selected.extend([row for row in rows if row["model"].brand.code.lower() == code][:quota])
    selected = selected[:6]

    covered = []
    for code in requested_brands:
        if any(row["fully_matched"] and row["model"].brand.code.lower() == code for row in selected):
            covered.append(code)
    uncovered = [code for code in requested_brands if code not in covered]
    brand_results = []
    for code in requested_brands:
        brand_rows = [row for row in selected if row["model"].brand.code.lower() == code]
        brand_results.append({
            "brand_code": code,
            "brand_name": BRAND_NAMES.get(code, code),
            "status": "covered" if code in covered else "uncovered",
            "candidate_count": len(brand_rows),
            "message": f"{BRAND_NAMES.get(code, code)}有本地证据确认候选" if code in covered else f"{BRAND_NAMES.get(code, code)}无可确认候选",
        })
    coverage = {"requested_brands": requested_brands, "covered_brands": covered, "uncovered_brands": uncovered, "brand_results": brand_results}
    return selected, coverage, conditions


def _match_status(rows: list[dict], coverage: dict, conditions: list[dict], unparsed: list[str] | None = None) -> str:
    if not rows:
        return "no_match"
    if unparsed:
        return "partial_match"
    if not conditions:
        return "matched"
    fully_matched = [row for row in rows if row["fully_matched"]]
    if fully_matched and not coverage["uncovered_brands"]:
        return "matched"
    return "partial_match"


def _structured_answer(rows: list[dict], status: str, coverage: dict, conditions: list[dict]) -> str:
    if not rows:
        missing = "；".join(f"{BRAND_NAMES.get(code, code)}无可确认候选" for code in coverage["uncovered_brands"])
        return "天枢本地资料库未找到满足这些条件的候选型号。" + (f"\n品牌覆盖：{missing}" if missing else "")
    conclusion = ("本地目录按品牌、类型或完整型号确定性召回相关候选。" if not conditions
                  else "本地证据已逐型号覆盖全部明确硬条件。" if status == "matched"
                  else "仅部分硬条件有本地证据，候选均需按缺失项核验。")
    lines = [conclusion]
    if coverage["brand_results"]:
        lines.append("品牌覆盖：" + "；".join(item["message"] for item in coverage["brand_results"]))
    lines += ["", "| 品牌 | 推荐型号 | 条件覆盖 | 本地证据/缺失项 |", "| --- | --- | --- | --- |"]
    for row in rows:
        model = row["model"]
        passed = [item for item in row["condition_results"] if item["status"] == "satisfied"]
        unknown = [item["label"] for item in row["condition_results"] if item["status"] == "unknown"]
        conflicts = [item["label"] for item in row["condition_results"] if item["status"] == "unsatisfied"]
        detail = "；".join(item["evidence"] for item in passed if item["evidence"]) or "无硬条件本地证据"
        if unknown:
            detail += "；待核验：" + "、".join(unknown)
        if conflicts:
            detail += "；冲突：" + "、".join(conflicts)
        lines.append(f"| {model.brand.name} | {model.model_name} | {len(passed)}/{len(conditions)} | {detail.replace('|', '／')} |")
    return "\n".join(lines)


def _candidate_models(db: Session, message: str, brand_code: str | None = None) -> list[Model]:
    rows, _coverage, _conditions = _candidate_rows(db, message)
    return [row["model"] for row in rows]


def recommend_models(db: Session, message: str, brand_code: str | None = None) -> dict:
    candidate_rows, coverage, conditions = _candidate_rows(db, message)
    unparsed = _unparsed_conditions(message, conditions)
    if unparsed:
        # Requirement-completeness gate: do not return actionable/catalog candidates
        # when any requirement-like capability is not structurally represented.
        candidate_rows = []
        for slot in coverage["brand_results"]:
            slot.update({"status": "uncovered", "candidate_count": 0, "message": f"{slot['brand_name']}存在未解析条件，待核验"})
        coverage["covered_brands"] = []
        coverage["uncovered_brands"] = list(coverage["requested_brands"])
    status = _match_status(candidate_rows, coverage, conditions, unparsed)
    display_rows = [row for row in candidate_rows if row["fully_matched"]] if status == "matched" else candidate_rows
    rows = []
    for row in display_rows:
        summary = model_to_summary(row["model"])
        evidence = [item["evidence"] for item in row["condition_results"] if item["evidence"]]
        rows.append({**summary, "evidence": evidence, "condition_results": row["condition_results"], "fully_matched": row["fully_matched"]})
    answer = _structured_answer(display_rows, status, coverage, conditions)
    if unparsed:
        answer += "\n排除条件未能安全结构化，禁止判定完全匹配：" + "；".join(unparsed)
    source = "local"
    warning = None
    provenance = AI_NOT_AVAILABLE
    base_url, api_key, ai_model, temperature, max_tokens, enabled = _effective_ai(db)
    if enabled and base_url and api_key and ai_model:
        has_evidence = bool(rows)
        refusal = ""
        if has_evidence:
            prompt = "你是天枢售前助手。只能基于后端给出的逐型号本地证据矩阵补充风险提示，不得新增型号、参数、事实，不得改变匹配状态或使用模型常识。\n需求：" + message + "\n矩阵：" + json.dumps(rows, ensure_ascii=False)[:8000]
        else:
            refusal = UNPARSED_REFUSAL if unparsed else NO_EVIDENCE_REFUSAL
            reason = "存在未解析条件" if unparsed else "本地检索无证据"
            prompt = (
                "你是天枢售前助手。当前唯一可用事实是：" + reason + "。"
                "不得新增或复述任何型号、参数、产品事实或常识；不得推荐候选。"
                f"只能原样返回这一句话，不得添加任何字符：{refusal}"
            )
        try:
            advisory = _chat_completion(base_url, api_key, ai_model, [{"role": "user", "content": prompt}], temperature, min(max_tokens, 300))
            if has_evidence and advisory:
                answer += "\n\nAI 风险提示：" + _clip(advisory, 300)
            elif not has_evidence:
                # Allowlist no-evidence output so a disobedient provider cannot
                # introduce product facts. The provider was still genuinely called.
                answer += "\n\nAI 回复：" + (advisory if advisory == refusal else refusal)
            source = "ai"
            provenance = AI_USED_WITH_EVIDENCE if has_evidence else AI_USED_NO_EVIDENCE_REFUSAL
        except HTTPException:
            warning = PUBLIC_AI_WARNING
            provenance = AI_PROVIDER_FAILED
    return {
        "answer": answer,
        "source": source,
        "warning": warning,
        "provenance": provenance,
        "match_status": status,
        "match_basis": "none" if unparsed else "hard_conditions" if conditions else "catalog_match" if rows else "none",
        "catalog_match": bool(rows and not conditions and not unparsed),
        "unparsed_conditions": unparsed,
        "hard_conditions": conditions,
        "coverage": coverage,
        "selected_model_ids": [row["id"] for row in rows],
        "models": [{
            "id": row["id"], "model_name": row["model_name"], "brand_code": row["brand_code"],
            "brand_name": row["brand_name"], "product_type": row["product_type"], "series": row["series"],
            "reason": "本地硬条件全部满足" if row["fully_matched"] else "部分条件缺少本地证据，待核验",
            "evidence": row["evidence"], "fully_matched": row["fully_matched"], "condition_results": row["condition_results"],
        } for row in rows],
    }
