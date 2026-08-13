from pathlib import Path


def test_public_data_only_revisions_are_documented_noops() -> None:
    versions = Path(__file__).parents[1] / "alembic" / "versions"
    expected = {
        "0007_nf5468a7_cross_platform_cleanup.py": "0006_gpu_parent_guard_import_trim_whitepaper",
        "0008_nf5468a7_cn_cpu_notes_cleanup.py": "0007_nf5468a7_cross_platform_cleanup",
        "0011_merge_auto_field_definitions.py": "0010_field_dictionary_guard",
        "0012_normalize_interface_fields.py": "0011_merge_auto_fields",
    }
    for filename, down_revision in expected.items():
        source = (versions / filename).read_text(encoding="utf-8")
        assert f'down_revision = "{down_revision}"' in source
        assert "def upgrade()" in source and "def downgrade()" in source
        assert "pass" in source
        upper = source.upper()
        assert "INSERT INTO" not in upper
        assert "UPDATE " not in upper
        assert "DELETE FROM" not in upper
