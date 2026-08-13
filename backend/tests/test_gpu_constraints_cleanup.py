import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.models import ModelCompatibleGpu


def test_model_compatible_gpu_rejects_self_reference() -> None:
    with SessionLocal() as db:
        db.add(ModelCompatibleGpu(model_id=1, gpu_model_id=1, source_ref="test"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_postgres_migration_has_cross_table_and_lifecycle_guards() -> None:
    migration = Path(__file__).parents[1] / "alembic" / "versions" / "0005_gpu_relation_constraints_acceptance_cleanup.py"
    text = migration.read_text(encoding="utf-8")
    assert "CREATE TRIGGER trg_validate_model_compatible_gpu" in text
    assert "target must be accessory/gpu_card/显卡" in text
    assert "CREATE TRIGGER trg_guard_related_model_update" in text
    assert "NOT EXISTS (SELECT 1 FROM models m WHERE m.series_id=s.id)" in text
    assert "model_spec_values v" in text
    assert "model_id <> gpu_model_id" in text


def test_cleanup_allowlist_preserves_formal_unused_fields() -> None:
    migration = Path(__file__).parents[1] / "alembic" / "versions" / "0005_gpu_relation_constraints_acceptance_cleanup.py"
    text = migration.read_text(encoding="utf-8")
    allowlist = text.split("DISPOSABLE_UNUSED_FIELDS = (", 1)[1].split(")", 1)[0]
    for preserved in ("source_material_type", "source_title", "gpu_market_reference_price"):
        assert preserved not in allowlist


def private_data_migration_omitted_0006_guards_gpu_relation_parents_and_scopes_whitepaper_cleanup() -> None:
    migration = Path(__file__).parents[1] / "alembic" / "versions" / "0006_gpu_parent_guard_import_trim_whitepaper.py"
    text = migration.read_text(encoding="utf-8")
    assert 'down_revision = "0005_gpu_rel_cleanup"' in text
    assert "BEFORE UPDATE OF code,name,status,deleted_at OR DELETE ON brands" in text
    assert "BEFORE UPDATE OF code,name,status,deleted_at OR DELETE ON product_types" in text
    assert "model_compatible_gpus" in text
    cleanup_sql = text.split("# Confirmed bad mapping only:", 1)[1].split("def downgrade", 1)[0]
    assert "sd.field_key = 'whitepaper_url'" in cleanup_sql
    assert "'NF5468M7'" in cleanup_sql
    assert "NF[[:space:]_-]*5468[[:space:]_-]*A7" in cleanup_sql
    assert "official_params_url" not in cleanup_sql


def private_data_migration_omitted_0007_nf5468a7_cleanup_is_evidence_bounded(tmp_path: Path) -> None:
    migration_path = Path(__file__).parents[1] / "alembic" / "versions" / "0007_nf5468a7_cross_platform_cleanup.py"
    spec = importlib.util.spec_from_file_location("migration_0007", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = create_engine(f"sqlite:///{tmp_path / 'migration.db'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE models (id INTEGER PRIMARY KEY, model_name TEXT NOT NULL)"))
        connection.execute(text("CREATE TABLE spec_definitions (id INTEGER PRIMARY KEY, field_key TEXT NOT NULL)"))
        connection.execute(text("""CREATE TABLE model_spec_values (
            id INTEGER PRIMARY KEY, model_id INTEGER NOT NULL, spec_definition_id INTEGER NOT NULL,
            value TEXT NOT NULL, raw_value TEXT NOT NULL DEFAULT '', raw_label TEXT NOT NULL DEFAULT '',
            source_ref TEXT NOT NULL DEFAULT '')"""))
        keys = ["cpu_compatibility_list", "cpu_socket", "cpu_notes", "chipset", "cpu_family", "official_params_url"]
        values_sql = ",".join(f"({index},'{key}')" for index, key in enumerate(keys, 1))
        connection.execute(text("INSERT INTO spec_definitions(id, field_key) VALUES " + values_sql))
        connection.execute(text("INSERT INTO models(id, model_name) VALUES (1,'NF5468A7'),(2,'NF5468M7'),(3,'NF5468-A7')"))

        rows = [
            (1, 1, 1, "同NF5280M7 CPU兼容列表"),
            (2, 1, 2, "LGA4677"),
            (3, 1, 3, "Intel Xeon CPU notes"),
            (4, 1, 4, "Intel C741 chipset"),
            (5, 1, 5, "AMD EPYC 9005"),
            (6, 1, 6, "https://example.com"),
            # Similar but not confirmed values on A7 must survive.
            (7, 1, 1, "A7兼容列表待官方确认"),
            (8, 1, 2, "SP5"),
            (9, 1, 3, "AMD平台说明"),
            (10, 1, 4, "AMD chipset待官网确认"),
            # Exact contaminated values on the Intel sibling must survive.
            (11, 2, 1, "同NF5280M7 CPU兼容列表"),
            (12, 2, 2, "LGA4677"),
            (13, 2, 3, "Intel Xeon CPU notes"),
            (14, 2, 4, "Intel C741 chipset"),
            # Normalized A7 spelling is intentionally in scope.
            (15, 3, 2, "LGA4677"),
        ]
        connection.execute(
            text("INSERT INTO model_spec_values(id,model_id,spec_definition_id,value) VALUES (:id,:model,:definition,:value)"),
            [{"id": row[0], "model": row[1], "definition": row[2], "value": row[3]} for row in rows],
        )

        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()

        remaining = set(connection.execute(text("SELECT id FROM model_spec_values")).scalars())
        assert {1, 2, 3, 4, 15}.isdisjoint(remaining)
        assert {5, 6, 7, 8, 9, 10, 11, 12, 13, 14} <= remaining


def private_data_migration_omitted_0007_contract_never_infers_amd_replacements() -> None:
    migration = Path(__file__).parents[1] / "alembic" / "versions" / "0007_nf5468a7_cross_platform_cleanup.py"
    text_value = migration.read_text(encoding="utf-8")
    cleanup_sql = text_value.split('op.execute("""', 1)[1].split('""")', 1)[0]
    assert 'down_revision = "0006_gpu_parent_guard"' in text_value
    assert "DELETE FROM model_spec_values" in cleanup_sql
    assert "cpu_family" not in cleanup_sql
    assert "official_params_url" not in cleanup_sql
    assert "INSERT" not in cleanup_sql.upper()


def private_data_migration_omitted_0008_nf5468a7_chinese_cpu_notes_cleanup_is_strictly_bounded(tmp_path: Path) -> None:
    migration_path = Path(__file__).parents[1] / "alembic" / "versions" / "0008_nf5468a7_cn_cpu_notes_cleanup.py"
    spec = importlib.util.spec_from_file_location("migration_0008", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = create_engine(f"sqlite:///{tmp_path / 'migration-0008.db'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE models (id INTEGER PRIMARY KEY, model_name TEXT NOT NULL)"))
        connection.execute(text("CREATE TABLE spec_definitions (id INTEGER PRIMARY KEY, field_key TEXT NOT NULL)"))
        connection.execute(text("""CREATE TABLE model_spec_values (
            id INTEGER PRIMARY KEY, model_id INTEGER NOT NULL, spec_definition_id INTEGER NOT NULL,
            value TEXT, raw_value TEXT, raw_label TEXT NOT NULL DEFAULT '', source_ref TEXT NOT NULL DEFAULT '')"""))
        keys = ["cpu_notes", "cpu_family", "official_params_url"]
        values_sql = ",".join(f"({index},'{key}')" for index, key in enumerate(keys, 1))
        connection.execute(text("INSERT INTO spec_definitions(id, field_key) VALUES " + values_sql))
        connection.execute(text("""INSERT INTO models(id, model_name) VALUES
            (1,'NF5468A7'),(2,'NF5468M7'),(3,'NF5468-A7'),(4,'NF5688A7')"""))

        rows = [
            # Confirmed pollution variants: marker may occur in value or raw_value.
            (1, 1, 1, "第四代/第五代英特尔至强可扩展处理器", ""),
            (2, 1, 1, "英特尔第四代处理器", ""),
            (3, 1, 1, "英特尔第五代处理器", ""),
            (4, 1, 1, "英特尔至强可扩展处理器", ""),
            (5, 1, 1, "来源待核验", "第五代英特尔处理器"),
            # Both columns together can satisfy the conjunction.
            (6, 1, 1, "英特尔平台", "第四代处理器"),
            # Near matches on target A7 must survive: missing one side of the predicate.
            (7, 1, 1, "第四代/第五代处理器", ""),
            (8, 1, 1, "英特尔平台说明", ""),
            (9, 1, 1, "AMD EPYC 9004/9005", ""),
            (10, 1, 1, None, None),
            # Explicitly preserved fields on the target model.
            (11, 1, 2, "AMD EPYC 9004/9005", "第四代/第五代英特尔至强"),
            (12, 1, 3, "https://example.com", "英特尔至强"),
            # Same contaminated note on sibling/other models must survive.
            (13, 2, 1, "第四代/第五代英特尔至强可扩展处理器", ""),
            (14, 4, 1, "第四代/第五代英特尔至强可扩展处理器", ""),
            # Normalized NF5468-A7 spelling remains in scope.
            (15, 3, 1, "第四代/第五代英特尔至强可扩展处理器", ""),
        ]
        connection.execute(
            text("""INSERT INTO model_spec_values
                (id,model_id,spec_definition_id,value,raw_value)
                VALUES (:id,:model,:definition,:value,:raw_value)"""),
            [
                {"id": row[0], "model": row[1], "definition": row[2], "value": row[3], "raw_value": row[4]}
                for row in rows
            ],
        )

        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()

        remaining = set(connection.execute(text("SELECT id FROM model_spec_values")).scalars())
        assert {1, 2, 3, 4, 5, 6, 15}.isdisjoint(remaining)
        assert {7, 8, 9, 10, 11, 12, 13, 14} <= remaining


def private_data_migration_omitted_0008_contract_only_deletes_cpu_notes_and_never_infers_amd() -> None:
    migration = Path(__file__).parents[1] / "alembic" / "versions" / "0008_nf5468a7_cn_cpu_notes_cleanup.py"
    text_value = migration.read_text(encoding="utf-8")
    cleanup_sql = text_value.split('op.execute("""', 1)[1].split('""")', 1)[0]
    assert 'down_revision = "0007_nf5468a7_cleanup"' in text_value
    assert "DELETE FROM model_spec_values" in cleanup_sql
    assert "sd.field_key = 'cpu_notes'" in cleanup_sql
    assert "英特尔" in cleanup_sql
    for marker in ("第四代", "第五代", "至强"):
        assert marker in cleanup_sql
    assert "cpu_family" not in cleanup_sql
    assert "official_params_url" not in cleanup_sql
    assert "NF5468M7" not in cleanup_sql
    assert "NF5688A7" not in cleanup_sql
    assert "INSERT" not in cleanup_sql.upper()
    assert "UPDATE" not in cleanup_sql.upper()
