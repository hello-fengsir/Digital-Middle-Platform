from pathlib import Path


def test_public_lifecycle_migration_is_schema_only() -> None:
    migration = Path(__file__).parents[1] / "alembic" / "versions" / "0009_controlled_lifecycle_tags.py"
    source = migration.read_text(encoding="utf-8")
    assert 'nullable=True, server_default=sa.null()' in source
    assert 'nullable=False, server_default="rts"' not in source
    assert 'op.create_table(' in source
    assert '"model_business_tags"' in source
    # Public migrations must not copy/seed/repair catalog rows.
    upper = source.upper()
    assert "OP.EXECUTE" not in upper
    assert "INSERT INTO" not in upper
    assert "UPDATE MODELS" not in upper
    assert "MODEL_NAME =" not in upper
