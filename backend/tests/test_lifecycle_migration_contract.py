import importlib.util
from pathlib import Path


def _migration_module():
    path = Path(__file__).parents[1] / "alembic" / "versions" / "0009_controlled_lifecycle_tags.py"
    spec = importlib.util.spec_from_file_location("lifecycle_0009", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module, path.read_text()


def test_nullable_migration_has_null_default_and_exact_formal_source_count_closure() -> None:
    migration, source = _migration_module()
    assert migration.LEGACY_LIFECYCLE_EXPECTED_COUNTS == {
        "npi": 22, "rts": 41, "rtq": 8, "eos": 17, "eol": 2,
    }
    assert sum(migration.LEGACY_LIFECYCLE_EXPECTED_COUNTS.values()) == 90
    assert 'nullable=True, server_default=sa.null()' in source
    assert 'nullable=False, server_default="rts"' not in source
    assert 'ELSE NULL' in source
    assert "d.field_key = 'lifecycle_status'" in source
    for legacy in (
        "NPI (新产品导入)", "RTS（可销售）", "RTQ（可报价）",
        "EOS（停止接单）", "EOL（生命周期终止）",
    ):
        assert legacy in source
