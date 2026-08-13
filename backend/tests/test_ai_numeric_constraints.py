import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.NamedTemporaryFile(suffix='.db').name}"
os.environ["API_KEY"] = "test-key"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD_HASH"] = "sha256:" + __import__("hashlib").sha256(b"test-admin-password").hexdigest()
os.environ["ADMIN_SESSION_SECRET"] = "test-session-secret"

from sqlalchemy import select

from app.ai_service import _dual_socket_spec, _extract_hard_conditions, _gpu_count_from_support_spec, _interface_spec, _memory_capacities_gb, _model_name_match_strength, recommend_models
from app.catalog import seed_spec_template, upsert_model
from app.db import Base, SessionLocal, engine
from app.models import Brand, Model, ModelCompatibleGpu, SpecDefinition, SpecGroup
from app.schemas import AiRecommendOut, ModelWrite, SpecInput
from app.routes.public import models as public_models, search as public_search


def _seed() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_spec_template(db)
        # These keys already exist in the formal 190-field dump. Unit tests use an
        # in-memory schema, so declare them as fixtures rather than changing
        # production STANDARD_FIELDS (which is outside this delivery scope).
        groups = {row.code: row for row in db.scalars(select(SpecGroup)).all()}
        db.add_all([
            SpecDefinition(group_id=groups["pcie_expansion"].id, field_key="pcie_interface", label="PCIe接口", sort_order=20),
            SpecDefinition(group_id=groups["gpu"].id, field_key="gpu_interface", label="GPU接口", sort_order=5),
            SpecDefinition(group_id=groups["gpu"].id, field_key="compute", label="算力", sort_order=6),
            SpecDefinition(group_id=groups["gpu"].id, field_key="gpu_memory", label="显存", sort_order=7),
        ])
        for code, name in (("inspur", "浪潮"), ("lenovo", "联想"), ("dell", "戴尔")):
            if not db.scalar(select(Brand).where(Brand.code == code)):
                db.add(Brand(code=code, name=name, source_name=name))
        db.commit()
        upsert_model(db, ModelWrite(
            brand_code="inspur", brand_name="浪潮", product_type="服务器", series="NF",
            model_name="NF-EVIDENCED", title="evidenced", source_ref="test",
            specifications=[
                SpecInput(field_key="memory_max_capacity", label="内存最大容量", group="内存", value="最高支持 8 TB DDR5", source_ref="test"),
                SpecInput(field_key="pcie_slots", label="PCIe扩展槽", group="扩展", value="最多 10 个 PCIe 扩展槽", source_ref="test"),
                SpecInput(field_key="pcie_interface", label="PCIe接口", group="扩展", value="服务器支持 PCIe 4.0 x16", source_ref="test"),
                SpecInput(field_key="gpu_interface", label="GPU接口", group="GPU", value="GPU总线 PCIe Gen4 x16", source_ref="test"),
                SpecInput(field_key="power_supply", label="电源", group="电源", value="2 个热插拔电源，支持 1+1 冗余", source_ref="test"),
                SpecInput(field_key="cpu_family", label="处理器", group="处理器", value="支持双路 CPU / 双插槽", source_ref="test"),
                SpecInput(field_key="gpu_support", label="GPU支持", group="GPU", value="最高支持4个双宽GPU；支持 2 张 NVIDIA L40S GPU", source_ref="test"),
            ],
        ))
        upsert_model(db, ModelWrite(
            brand_code="lenovo", brand_name="联想", product_type="服务器", series="ThinkSystem",
            model_name="LEN-MISSING", title="missing evidence", source_ref="test",
            specifications=[SpecInput(field_key="memory", label="内存", group="内存", value="待补充", source_ref="test")],
        ))
        upsert_model(db, ModelWrite(
            brand_code="lenovo", brand_name="联想", product_type="工作站", series="ThinkStation",
            model_name="PX-GPU", title="workstation gpu expansion", source_ref="test",
            specifications=[SpecInput(field_key="pcie_slots", label="PCIe扩展", group="扩展", value="支持 GPU 扩展，4 个 PCIe 扩展槽", source_ref="test")],
        ))
        upsert_model(db, ModelWrite(
            brand_code="lenovo", brand_name="联想", product_type="服务器", series="ThinkSystem",
            model_name="SR665 V3", title="three double width", source_ref="test",
            specifications=[SpecInput(field_key="gpu_support", label="GPU支持", group="GPU", value="最高支持8个单宽GPU或3个双宽GPU", source_ref="test")],
        ))
        upsert_model(db, ModelWrite(
            brand_code="inspur", brand_name="浪潮", product_type="服务器", series="NF",
            model_name="NF5270M7", title="four double width", source_ref="test",
            specifications=[
                SpecInput(field_key="gpu_support", label="GPU支持", group="GPU", value="最高支持4个双宽GPU", source_ref="test"),
                SpecInput(field_key="pcie_slots", label="PCIe与扩展", group="PCIe与扩展", value="13个PCIe x16扩展插槽，OCP与其中1槽互斥", source_ref="test"),
            ],
        ))
        upsert_model(db, ModelWrite(
            brand_code="dell", brand_name="戴尔", product_type="服务器", series="PowerEdge",
            model_name="DELL-LOW", title="low", source_ref="test",
            specifications=[SpecInput(field_key="memory", label="内存", group="内存", value="最高 512 GB", source_ref="test")],
        ))
        upsert_model(db, ModelWrite(
            brand_code="dell", brand_name="戴尔", product_type="服务器", series="PowerEdge",
            model_name="DELL-NO3", title="confirmed no three double width", source_ref="test",
            specifications=[SpecInput(
                field_key="gpu_support", label="GPU支持", group="GPU",
                value="最高支持4个双宽GPU；明确不支持3个双宽GPU配置", source_ref="test",
            )],
        ))
        gpu_specs = [
            SpecInput(field_key="gpu_interface", label="GPU接口", group="GPU", value="PCIe Gen4 x16", source_ref="test"),
            SpecInput(field_key="compute", label="算力", group="GPU", value="AMD 61.3 TFLOPs / 123 TOPS", source_ref="test"),
            SpecInput(field_key="gpu_memory", label="显存", group="GPU", value="48GB GDDR6", source_ref="test"),
        ]
        for gpu_name in ("NVIDIA L40S", "NVIDIA L40", "L4", "RTX A6000", "NVIDIA RTX 6000 Ada Generation", "AMD Instinct MI300X"):
            upsert_model(db, ModelWrite(
                brand_code="inspur", brand_name="浪潮", product_type="显卡", series="GPU",
                model_name=gpu_name, title=gpu_name, source_ref="test", specifications=gpu_specs,
            ))
        upsert_model(db, ModelWrite(
            brand_code="inspur", brand_name="浪潮", product_type="服务器", series="NF",
            model_name="NF5280M7", title="NF5280M7", source_ref="test", specifications=[],
        ))
        for model_name, field_key, label, group, value in (
            ("TS860M7", "network_interfaces", "网络接口", "网络", "最大支持4个PCIe 5.0 x16 OCP3.0 SFF网络子卡"),
            ("HG8480", "pcie_slots", "扩展能力", "PCIe与扩展", "支持8个PCIe 5.0 x16标准扩展槽"),
            ("ST45", "pcie_slots", "标准PCIe插槽", "标准PCIe插槽", "主板提供2个PCIe 4.0 x16扩展插槽"),
        ):
            upsert_model(db, ModelWrite(
                brand_code="inspur", brand_name="浪潮", product_type="服务器", series="PCIe回归",
                model_name=model_name, title=model_name, source_ref="test",
                specifications=[SpecInput(field_key=field_key, label=label, group=group, value=value, source_ref="test")],
            ))
        upsert_model(db, ModelWrite(
            brand_code="inspur", brand_name="浪潮", product_type="服务器", series="NF",
            model_name="FALSE-DUAL", title="false dual evidence", source_ref="test",
            specifications=[
                SpecInput(field_key="memory", label="内存", group="内存", value="单颗CPU支持16条DIMM、两颗CPU支持32条DIMM", source_ref="test"),
                SpecInput(field_key="selection_notes", label="选型说明", group="选型", value="场景描述：2U双路", source_ref="test"),
            ],
        ))
        server = db.scalar(select(Model).where(Model.model_name == "LEN-MISSING"))
        l40s = db.scalar(select(Model).where(Model.model_name == "NVIDIA L40S"))
        assert server is not None and l40s is not None
        db.add(ModelCompatibleGpu(model_id=server.id, gpu_model_id=l40s.id, source_ref="test compatibility only"))
        db.commit()


def setup_module() -> None:
    _seed()


def _recommend(message: str) -> dict:
    with SessionLocal() as db:
        result = recommend_models(db, message)
        return AiRecommendOut.model_validate(result).model_dump()


def test_parser_extracts_numeric_power_and_gpu_hard_conditions() -> None:
    parsed = _extract_hard_conditions("浪潮服务器，内存至少8TB，至少10个PCIe插槽，必须1+1冗余电源，双L40S显卡")
    by_kind = {item["kind"]: item for item in parsed}
    assert by_kind["memory_capacity"]["value"] == 8
    assert by_kind["memory_capacity"]["unit"] == "TB"
    assert by_kind["pcie_slots"]["value"] == 10
    assert by_kind["redundant_power"]["value"] == "1+1"
    assert by_kind["gpu_model"]["value"] == "L40S"
    assert by_kind["gpu_count"]["value"] == 2


def test_matched_requires_same_model_local_evidence_for_every_condition() -> None:
    body = _recommend("浪潮服务器，内存至少8TB，至少10个PCIe插槽，必须1+1冗余电源，双L40S显卡")
    assert body["match_status"] == "matched"
    assert [item["model_name"] for item in body["models"]] == ["NF-EVIDENCED"]
    model = body["models"][0]
    assert model["fully_matched"] is True
    assert all(item["satisfied"] and item["evidence"] for item in model["condition_results"])


def test_extreme_numeric_requirement_cannot_be_matched_by_brand_or_type_only() -> None:
    body = _recommend("浪潮服务器，内存至少100TB，至少99个PCIe插槽")
    assert body["match_status"] == "no_match"
    assert body["models"] == []
    assert "本地证据已逐型号覆盖" not in body["answer"]


def test_unknown_marker_is_not_local_capacity_evidence() -> None:
    body = _recommend("联想服务器，内存至少1GB")
    assert body["match_status"] == "no_match"
    assert body["models"] == []


def test_cross_brand_missing_dimension_is_structured_and_visible() -> None:
    body = _recommend("对比浪潮和联想服务器，内存至少8TB")
    assert body["match_status"] == "partial_match"
    assert body["coverage"]["requested_brands"] == ["lenovo", "inspur"]
    assert body["coverage"]["covered_brands"] == ["inspur"]
    assert body["coverage"]["uncovered_brands"] == ["lenovo"]
    slots = {item["brand_code"]: item for item in body["coverage"]["brand_results"]}
    assert slots["lenovo"]["message"] == "联想无可确认候选"
    assert slots["lenovo"]["status"] == "uncovered"
    assert "联想无可确认候选" in body["answer"]
    assert {item["brand_code"] for item in body["models"]} == {"inspur"}


def test_memory_request_parser_does_not_take_unrelated_or_bandwidth_numbers() -> None:
    assert not any(c["kind"] == "memory_capacity" for c in _extract_hard_conditions("GPU memory 80GB，CPU兼容512GB，带宽900GB/s，内存频率5600MHz"))
    assert not any(c["kind"] == "memory_capacity" for c in _extract_hard_conditions("内存带宽 900GB/s，同时需要服务器"))
    parsed = {c["kind"]: c for c in _extract_hard_conditions("内存至少1.5TB并且支持2张L40S")}
    assert parsed["memory_capacity"]["value"] == 1.5
    assert parsed["gpu_count"]["value"] == 2


def test_memory_evidence_is_scoped_plausible_and_normalized_to_gb() -> None:
    base = {"field_key": "memory_max_capacity", "label": "最大内存容量", "group_name": "内存"}
    assert _memory_capacities_gb({**base, "value": "最高 1.5 TB DDR5"}) == [1536]
    assert _memory_capacities_gb({**base, "value": "带宽 900 GB/s，频率 5600 MHz"}) == []
    assert _memory_capacities_gb({**base, "value": "999 TB"}) == []
    assert _memory_capacities_gb({"field_key": "gpu_memory", "label": "GPU memory", "group_name": "GPU", "value": "80GB"}) == []
    assert _memory_capacities_gb({"field_key": "cpu_family", "label": "CPU兼容列表", "group_name": "处理器", "value": "型号512GB"}) == []


def test_gpu_model_word_orders_and_chinese_connectors() -> None:
    cases = {
        "支持L40S显卡": ("L40S", None),
        "L40S GPU×2": ("L40S", 2),
        "2张L40S": ("L40S", 2),
        "内存至少8TB且支持2张L40S": ("L40S", 2),
        "内存至少8TB并且L40S GPU×2": ("L40S", 2),
        "内存至少8TB同时2张L40S": ("L40S", 2),
        "内存至少8TB以及支持L40S显卡": ("L40S", None),
    }
    for message, (model, count) in cases.items():
        parsed = {c["kind"]: c for c in _extract_hard_conditions(message)}
        assert parsed["gpu_model"]["value"] == model, message
        if "内存" in message:
            assert parsed["memory_capacity"]["value"] == 8, message
        if count is not None:
            assert parsed["gpu_count"]["value"] == count, message


def test_gpu_count_never_comes_from_pcie_or_disk_numbers() -> None:
    for message in ("支持L40S显卡，12个PCIe插槽", "支持L40S显卡并且24块硬盘", "PCIe 8个以及L40S GPU"):
        parsed = _extract_hard_conditions(message)
        assert not any(c["kind"] == "gpu_count" for c in parsed), message
    assert {c["kind"]: c for c in _extract_hard_conditions("GPU支持4×双宽")}["gpu_count"]["value"] == 4


def test_pcie_bus_descriptor_never_pollutes_gpu_model_or_count() -> None:
    parsed = {item["kind"]: item for item in _extract_hard_conditions("浪潮服务器，支持L40S PCIe Gen4 x16")}
    assert parsed["gpu_model"]["value"] == "L40S"
    assert "gpu_count" not in parsed
    assert all(item["value"] != "GEN4" for item in parsed.values())


def test_server_and_gpu_pcie_interface_scope_accepts_original_spellings() -> None:
    server_cases = ("服务器PCIe Gen4 x16接口", "服务器PCIe 4.0 x16接口", "服务器PCIe x16接口")
    for message in server_cases:
        parsed = {item["kind"]: item for item in _extract_hard_conditions(message)}
        assert "pcie_interface" in parsed, message
        assert "gpu_interface" not in parsed, message
        assert parsed["pcie_interface"]["lanes"] == 16
        assert "gpu_count" not in parsed
    gpu = {item["kind"]: item for item in _extract_hard_conditions("GPU接口PCIe Gen4 x16")}
    assert "gpu_interface" in gpu and "pcie_interface" not in gpu
    assert gpu["gpu_interface"]["generation"] == 4
    assert gpu["gpu_interface"]["lanes"] == 16

    assert _recommend("浪潮服务器，服务器PCIe Gen4 x16接口")["match_status"] == "matched"
    assert _recommend("浪潮服务器，服务器PCIe 4.0 x16接口")["match_status"] == "matched"
    gpu_result = _recommend("需要GPU接口PCIe Gen4 x16")
    assert gpu_result["match_status"] == "matched"
    assert all(item["product_type"] == "显卡" for item in gpu_result["models"])


def test_server_pcie_interface_uses_strict_motherboard_expansion_allowlist() -> None:
    positives = (
        {"field_key": "pcie_slots", "label": "PCIe与扩展", "group_name": "PCIe与扩展", "value": "13个PCIe x16扩展插槽，OCP与其中1槽互斥"},
        {"field_key": "raw_pcie_expansion", "label": "扩展能力", "group_name": "PCIe与扩展", "value": "支持8个PCIe 5.0 x16标准扩展槽"},
        {"field_key": "pcie_interface", "label": "标准PCIe插槽", "group_name": "基础信息", "value": "主板提供2个PCIe 4.0 x16扩展插槽"},
    )
    negatives = (
        {"field_key": "network_interfaces", "label": "网络接口", "group_name": "网络", "value": "最大支持4个PCIe 5.0 x16 OCP3.0 SFF网络子卡"},
        {"field_key": "ocp_slots", "label": "OCP网卡", "group_name": "网络", "value": "OCP 3.0，PCIe Gen5 x16"},
        {"field_key": "raid_controller", "label": "RAID卡", "group_name": "存储/RAID", "value": "PCIe 4.0 x16 RAID控制器"},
        {"field_key": "gpu_interface", "label": "GPU接口", "group_name": "GPU", "value": "GPU总线PCIe Gen4 x16"},
        {"field_key": "raw_gpu_bus", "label": "显卡自身接口", "group_name": "显卡", "value": "PCIe 5.0 x16"},
    )
    assert all(_interface_spec(spec, "pcie_interface") for spec in positives)
    assert not any(_interface_spec(spec, "pcie_interface") for spec in negatives)


def test_named_server_pcie_regressions_reject_ts860_network_and_keep_slot_fields() -> None:
    body = _recommend("需要PCIe x16服务器接口")
    assert body["match_status"] == "matched"
    names = [item["model_name"] for item in body["models"]]
    assert "TS860M7" not in names
    assert names == ["NF-EVIDENCED", "NF5270M7", "HG8480", "ST45"]
    for item in body["models"]:
        evidence = item["condition_results"][0]["evidence"]
        assert evidence and "PCIe" in evidence


def test_gpu_model_matching_uses_complete_normalized_token() -> None:
    l40 = _recommend("L40显卡")
    assert [item["model_name"] for item in l40["models"]] == ["NVIDIA L40"]
    assert "NVIDIA L40S" not in [item["model_name"] for item in l40["models"]]

    l40s = _recommend("NVIDIA L40S")
    assert [item["model_name"] for item in l40s["models"]] == ["NVIDIA L40S"]
    assert l40s["models"][0]["product_type"] == "显卡"


def test_prefixed_gpu_bare_aliases_are_exact_token_sequences_only() -> None:
    assert _model_name_match_strength("L40S", "NVIDIA L40S") == 2
    assert _model_name_match_strength("NVIDIA L40S", "NVIDIA L40S") == 3
    assert _model_name_match_strength("L40", "NVIDIA L40S") == 0
    assert _model_name_match_strength("RTX 6000 Ada", "NVIDIA RTX 6000 Ada Generation") == 2
    assert _model_name_match_strength("RTX 6000", "NVIDIA RTX 6000 Ada Generation") == 0
    assert _model_name_match_strength("Instinct MI300X", "AMD Instinct MI300X") == 2
    assert _model_name_match_strength("EPYC 9654", "AMD EPYC 9654") == 0
    assert _model_name_match_strength("Xeon 8592", "Intel Xeon 8592") == 0
    # 服务器型号保持原有完整型号精确合同，不因 GPU 厂商别名规则放宽。
    assert _model_name_match_strength("NF5280M7", "NF5280M7") == 3
    assert _model_name_match_strength("NF5280", "NF5280M7") == 0


def test_public_models_search_and_ai_share_exact_gpu_identity_contract() -> None:
    expected = {
        "L40": ["NVIDIA L40"],
        "L40S": ["NVIDIA L40S"],
        "RTX 6000 Ada": ["NVIDIA RTX 6000 Ada Generation"],
        "RTX6000Ada": ["NVIDIA RTX 6000 Ada Generation"],
    }
    with SessionLocal() as db:
        for query, names in expected.items():
            model_names = [item["model_name"] for item in public_models(brand="inspur", keyword=query, db=db)]
            search_names = [item["model_name"] for item in public_search(q=query, brand="inspur", db=db)]
            ai_names = [item["model_name"] for item in recommend_models(db, query)["models"]]
            assert model_names == search_names == ai_names == names, query
        assert _model_name_match_strength("NF5280", "NF5280M7") == 0


def test_dual_socket_evidence_field_allowlist_positive_and_negative() -> None:
    assert _dual_socket_spec({"field_key": "cpu_count", "label": "CPU数量", "group_name": "处理器", "value": "支持两颗CPU"})
    assert _dual_socket_spec({"field_key": "processor", "label": "处理器", "group_name": "处理器", "value": "双路"})
    assert not _dual_socket_spec({"field_key": "memory", "label": "内存", "group_name": "内存", "value": "两颗CPU支持32条DIMM"})
    assert not _dual_socket_spec({"field_key": "selection_notes", "label": "选型说明", "group_name": "选型", "value": "2U双路"})
    body = _recommend("双路CPU服务器")
    assert "NF-EVIDENCED" in [item["model_name"] for item in body["models"]]
    assert "FALSE-DUAL" not in [item["model_name"] for item in body["models"]]


def test_structured_negative_cpu_and_gpu_remove_conflicting_candidates() -> None:
    cpu = _recommend("不要双路CPU的服务器")
    assert any(item["kind"] == "dual_socket" and item["operator"] == "exclude_eq" for item in cpu["hard_conditions"])
    assert "NF-EVIDENCED" not in [item["model_name"] for item in cpu["models"]]
    assert cpu["selected_model_ids"] == [item["id"] for item in cpu["models"]]
    gpu = _recommend("不接受L40S显卡")
    assert any(item["kind"] == "gpu_model" and item["operator"] == "exclude_eq" for item in gpu["hard_conditions"])
    assert "NVIDIA L40S" not in [item["model_name"] for item in gpu["models"]]
    assert gpu["selected_model_ids"] == [item["id"] for item in gpu["models"]]


def test_original_negative_phrases_are_structured_without_false_match() -> None:
    cases = {
        "浪潮服务器，内存至少8TB，不支持双路": {("dual_socket", "2")},
        "浪潮服务器，内存至少8TB，不支持L40S": {("gpu_model", "L40S")},
        "浪潮服务器，内存至少8TB，排除L40S和L40": {("gpu_model", "L40S"), ("gpu_model", "L40")},
        "浪潮服务器，内存至少8TB，不要A10/A30": {("gpu_model", "A10"), ("gpu_model", "A30")},
    }
    for message, expected in cases.items():
        body = _recommend(message)
        exclusions = {(item["kind"], str(item["value"])) for item in body["hard_conditions"] if item["operator"] == "exclude_eq"}
        assert expected <= exclusions, message
        assert body["match_status"] != "matched", message
        assert all(not any(result["status"] == "unsatisfied" for result in model["condition_results"]) for model in body["models"]), message


def test_unparsed_negative_never_uses_opposite_condition_to_create_candidates() -> None:
    body = _recommend("不要无法识别的神秘拓扑")
    assert body["unparsed_conditions"] == ["不要无法识别的神秘拓扑"]
    assert body["models"] == []
    assert body["selected_model_ids"] == []


def test_bare_prefixed_gpu_models_are_deterministically_retrieved() -> None:
    assert [item["model_name"] for item in _recommend("L40S")["models"]] == ["NVIDIA L40S"]
    assert [item["model_name"] for item in _recommend("RTX 6000 Ada")["models"]] == ["NVIDIA RTX 6000 Ada Generation"]
    assert [item["model_name"] for item in _recommend("Instinct MI300X")["models"]] == ["AMD Instinct MI300X"]


def test_deterministic_non_numeric_queries_are_bounded_and_never_brand_fallback() -> None:
    brand_type = _recommend("浪潮服务器")
    assert brand_type["match_status"] == "matched"
    assert 1 <= len(brand_type["models"]) <= 6
    assert all(item["brand_code"] == "inspur" and item["product_type"] == "服务器" for item in brand_type["models"])

    exact_model = _recommend("推荐NF5280M7")
    assert [item["model_name"] for item in exact_model["models"]] == ["NF5280M7"]

    brand_only = _recommend("浪潮")
    assert brand_only["match_status"] == "no_match"
    assert brand_only["models"] == []


def test_gpu_count_evidence_requires_whole_machine_support_field_and_semantics() -> None:
    false_specs = (
        {"field_key": "pcie_interface", "label": "GPU接口", "group_name": "GPU", "value": "L40S PCIe Gen4 x16"},
        {"field_key": "compute", "label": "L4 GPU算力", "group_name": "GPU", "value": "30.3 TFLOPs / 121 TOPS"},
        {"field_key": "gpu_memory", "label": "RTX A6000显存", "group_name": "GPU", "value": "48GB GDDR6"},
        {"field_key": "compute", "label": "AMD GPU算力", "group_name": "GPU", "value": "61.3 TFLOPs"},
        {"field_key": "storage", "label": "硬盘与PCIe", "group_name": "扩展", "value": "24块硬盘，PCIe x16"},
        {"field_key": "compatible_gpu", "label": "兼容显卡", "group_name": "兼容性", "value": "兼容4张L40S GPU"},
    )
    assert all(_gpu_count_from_support_spec(spec) == [] for spec in false_specs)
    real = {"field_key": "gpu_support", "label": "GPU支持", "group_name": "扩展", "value": "最高支持4个双宽GPU"}
    assert _gpu_count_from_support_spec(real) == [4]


def test_gpu_count_width_is_parsed_and_evidence_is_width_scoped() -> None:
    parsed = {c["kind"]: c for c in _extract_hard_conditions("服务器最高支持4个双宽GPU")}
    assert parsed["gpu_count"]["value"] == 4
    assert parsed["gpu_count"]["width"] == "double"
    assert parsed["gpu_count"]["label"] == "GPU至少4张双宽"

    alternatives = {"field_key": "gpu_support", "label": "GPU支持", "group_name": "GPU", "value": "最高支持8个单宽GPU或3个双宽GPU"}
    assert max(_gpu_count_from_support_spec(alternatives)) == 8
    assert _gpu_count_from_support_spec(alternatives, "single") == [8]
    assert _gpu_count_from_support_spec(alternatives, "double") == [3]


def test_real_gpu_width_requirement_rejects_sr665_and_matches_nf5270m7() -> None:
    body = _recommend("服务器最高支持4个双宽GPU")
    assert body["match_status"] == "matched"
    names = [item["model_name"] for item in body["models"]]
    assert "NF5270M7" in names
    assert "SR665 V3" not in names


def test_exclusion_unknown_cannot_match_and_confirmed_absence_can() -> None:
    unknown = _recommend("浪潮服务器，需要支持4个双宽GPU，排除3个双宽GPU配置")
    assert unknown["match_status"] == "partial_match"
    assert unknown["models"]
    assert all(model["fully_matched"] is False for model in unknown["models"])
    exclusion_results = [
        result for model in unknown["models"] for result in model["condition_results"]
        if result["label"] == "排除3个双宽GPU配置"
    ]
    assert exclusion_results
    assert all(result["status"] == "unknown" and result["verification_status"] == "unknown" and result["satisfied"] is False for result in exclusion_results)

    confirmed = _recommend("戴尔服务器，需要支持4个双宽GPU，排除3个双宽GPU配置")
    assert confirmed["match_status"] == "matched"
    assert [item["model_name"] for item in confirmed["models"]] == ["DELL-NO3"]
    result = next(item for item in confirmed["models"][0]["condition_results"] if item["label"] == "排除3个双宽GPU配置")
    assert result["status"] == "satisfied"
    assert result["verification_status"] == "confirmed"
    assert result["actual"] == "confirmed_absence"
    assert result["evidence"].startswith("明确不支持证据：")


def test_unspecified_gpu_width_uses_max_compatible_option_not_sum() -> None:
    body = _recommend("联想服务器最高支持8个GPU")
    assert body["match_status"] == "matched"
    assert [item["model_name"] for item in body["models"]] == ["SR665 V3"]
    result = next(item for item in body["models"][0]["condition_results"] if item["kind"] == "gpu_count")
    assert result["actual"] == 8


def test_compatibility_proves_gpu_model_only_and_false_count_cannot_create_partial() -> None:
    model_only = _recommend("联想服务器，要求L40S显卡")
    assert model_only["match_status"] == "matched"
    assert [item["model_name"] for item in model_only["models"]] == ["LEN-MISSING"]

    count_and_model = _recommend("联想服务器，要求L40S显卡，最多可配4张GPU")
    assert count_and_model["match_status"] == "partial_match"
    result = {item["kind"]: item for item in count_and_model["models"][0]["condition_results"]}
    assert result["gpu_model"]["satisfied"] is True
    assert result["gpu_count"]["satisfied"] is False

    false_count_only = _recommend("浪潮服务器，要求最多可配16张GPU")
    assert false_count_only["match_status"] == "no_match"
    assert false_count_only["models"] == []


def test_gpu_accessories_are_never_server_requirement_candidates() -> None:
    body = _recommend("浪潮服务器，要求L40S显卡")
    assert all(item["product_type"] == "服务器" for item in body["models"])
    assert "L40S" not in [item["model_name"] for item in body["models"]]


def test_server_feature_plus_gpu_implicitly_scopes_candidates_to_servers() -> None:
    for message in (
        "双路CPU并且支持2张L40S显卡",
        "内存至少8TB并且支持2张L40S显卡",
        "至少10个PCIe插槽并且支持L40S显卡",
        "1+1冗余电源并且支持L40S显卡",
    ):
        body = _recommend(message)
        assert all(item["product_type"] == "服务器" for item in body["models"]), message
        assert "L40S" not in [item["model_name"] for item in body["models"]], message


def test_pure_l40s_accessory_query_remains_available() -> None:
    body = _recommend("L40S显卡")
    l40s = next(item for item in body["models"] if item["model_name"] == "NVIDIA L40S")
    assert l40s["product_type"] == "显卡"


def test_bare_l40s_is_catalog_match_not_hard_condition_match() -> None:
    body = _recommend("L40S")
    assert body["match_status"] == "matched"
    assert body["match_basis"] == "catalog_match"
    assert body["catalog_match"] is True
    assert body["hard_conditions"] == []
    assert [item["model_name"] for item in body["models"]] == ["NVIDIA L40S"]


def test_pcie_interface_capability_is_retrieved_without_fake_gpu_count() -> None:
    body = _recommend("需要PCIe Gen4 x16接口的GPU")
    parsed = {item["kind"]: item for item in body["hard_conditions"]}
    assert parsed["gpu_interface"]["value"] == "PCIe Gen4 x16"
    assert "gpu_count" not in parsed
    assert body["match_status"] == "matched"
    assert body["models"]
    assert all(item["product_type"] == "显卡" for item in body["models"])


def test_cross_brand_typed_gpu_expansion_has_per_brand_coverage() -> None:
    body = _recommend("比较联想工作站和浪潮服务器，要求GPU扩展")
    assert body["match_status"] == "matched"
    assert body["coverage"]["requested_brands"] == ["lenovo", "inspur"]
    assert body["coverage"]["covered_brands"] == ["lenovo", "inspur"]
    assert {(item["brand_code"], item["product_type"]) for item in body["models"]} == {
        ("lenovo", "工作站"), ("inspur", "服务器"),
    }


def test_excluded_configuration_prevents_matched() -> None:
    body = _recommend("需要支持4个双宽GPU的服务器，不接受4个双宽GPU")
    assert body["match_status"] == "no_match"
    assert any(item["operator"] == "exclude_eq" for item in body["hard_conditions"])
    assert body["models"] == []
    assert body["selected_model_ids"] == []


def test_unparsed_negative_clause_blocks_matched() -> None:
    body = _recommend("浪潮服务器，不能采用低级配置")
    assert body["match_status"] != "matched"
    assert "不能采用低级配置" in body["unparsed_conditions"]


def test_unparsed_hot_swap_fan_and_ipmi_requirements_gate_all_candidates() -> None:
    for message, marker in (("浪潮服务器，要求热插拔风扇", "热插拔风扇"), ("浪潮服务器，要求IPMI管理", "IPMI")):
        body = _recommend(message)
        assert marker in body["unparsed_conditions"], message
        assert body["match_status"] == "no_match"
        assert body["models"] == []
        assert body["selected_model_ids"] == []


def test_nf5280_m7_complete_separator_variants_and_prefix_negative() -> None:
    for query in ("NF5280M7", "NF5280-M7", "NF5280 M7", "推荐完整型号 NF5280-M7 服务器"):
        assert _model_name_match_strength(query, "NF5280M7") > 0, query
        assert [item["model_name"] for item in _recommend(query)["models"]] == ["NF5280M7"], query
    for query in ("NF5280", "推荐NF5280服务器"):
        assert _model_name_match_strength(query, "NF5280M7") == 0, query
        assert "NF5280M7" not in [item["model_name"] for item in _recommend(query)["models"]], query


def test_partial_candidates_have_at_least_one_hard_hit_and_coverage_always_exists() -> None:
    partial = _recommend("浪潮服务器，内存至少8TB并且GPU至少8张")
    assert partial["match_status"] == "partial_match"
    assert partial["models"]
    assert all(any(result["satisfied"] for result in model["condition_results"]) for model in partial["models"])
    no_evidence = _recommend("联想和戴尔服务器，内存至少60TB")
    assert no_evidence["models"] == []
    assert no_evidence["coverage"]["requested_brands"] == ["lenovo", "dell"]
    assert no_evidence["coverage"]["brand_results"]


def test_no_named_brand_candidate_keeps_uncovered_slot() -> None:
    body = _recommend("对比浪潮和示例品牌服务器，内存至少8TB")
    assert body["match_status"] == "partial_match"
    assert "generic" in body["coverage"]["uncovered_brands"]
    slot = next(item for item in body["coverage"]["brand_results"] if item["brand_code"] == "generic")
    assert slot["candidate_count"] == 0
    assert slot["message"] == "示例品牌无可确认候选"


def test_public_warning_redacts_provider_detail(monkeypatch) -> None:
    import app.ai_service as service
    from fastapi import HTTPException

    monkeypatch.setattr(service, "_effective_ai", lambda db: ("https://example.com", "secret-key", "model", 0.2, 100, True))
    monkeypatch.setattr(service, "_chat_completion", lambda *args, **kwargs: (_ for _ in ()).throw(HTTPException(status_code=502, detail="secret-key raw upstream body")))
    body = _recommend("浪潮服务器，内存至少8TB")
    assert body["warning"] == service.PUBLIC_AI_WARNING
    assert "secret" not in body["warning"]


def test_chat_completion_timeout_is_bounded_and_http_body_is_redacted(monkeypatch) -> None:
    import io
    import urllib.error
    import app.ai_service as service
    from fastapi import HTTPException

    seen = {}
    monkeypatch.setattr(service.settings, "ai_total_timeout_seconds", 3.0)

    def fail(req, timeout):
        seen["timeout"] = timeout
        raise urllib.error.HTTPError(req.full_url, 502, "bad", {}, io.BytesIO(b"private upstream body"))

    monkeypatch.setattr(service.urllib.request, "urlopen", fail)
    try:
        service._chat_completion("https://example.com", "key", "model", [{"role": "user", "content": "x"}])
    except HTTPException as exc:
        assert exc.status_code == 502
        assert "private upstream body" not in str(exc)
    else:
        raise AssertionError("expected sanitized upstream error")
    assert 0 < seen["timeout"] <= 3.0
