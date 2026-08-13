import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.catalog import resolve_existing_spec_definitions, write_spec_values
from app.models import Model, ModelSpecValue, SpecDefinition, SpecGroup
from app.schemas import SpecInput


def fixture_db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    group = SpecGroup(code="basic", name="基础信息", sort_order=1)
    db.add(group)
    db.flush()
    db.add_all([
        SpecDefinition(id=1, group_id=group.id, field_key="cpu_family", label="处理器", sort_order=1),
        SpecDefinition(id=2, group_id=group.id, field_key="raw_legacy", label="遗留", sort_order=2),
    ])
    db.commit()
    return db


def spec(key):
    return SpecInput(field_key=key, label="伪造标签", group="伪造分组", sort_order=999, value="v")


@pytest.mark.parametrize("key", ["unknown", "raw_new_reference"])
def test_unknown_or_raw_reference_is_422_before_write(key):
    db = fixture_db()
    before = len(db.scalars(select(SpecDefinition)).all())
    with pytest.raises(HTTPException) as exc:
        resolve_existing_spec_definitions(db, [spec(key)])
    assert exc.value.status_code == 422
    assert len(db.scalars(select(SpecDefinition)).all()) == before


def test_known_field_uses_definition_metadata_without_mutation():
    db = fixture_db()
    model = Model(id=1, brand_id=1, product_type_id=1, series_id=1, model_name="x", title="x", source_ref="t")
    db.add(model)
    db.flush()
    resolved = resolve_existing_spec_definitions(db, [spec("cpu_family")])
    write_spec_values(db, model, [spec("cpu_family")], resolved)
    db.flush()
    definition = db.get(SpecDefinition, 1)
    assert (definition.label, definition.sort_order) == ("处理器", 1)


def test_legacy_raw_requires_existing_binding():
    db = fixture_db()
    with pytest.raises(HTTPException):
        resolve_existing_spec_definitions(db, [spec("raw_legacy")], model_id=9)
    db.add(ModelSpecValue(model_id=9, spec_definition_id=2, value="old", raw_label="old", raw_value="old", source_ref="old"))
    db.flush()
    assert "raw_legacy" in resolve_existing_spec_definitions(db, [spec("raw_legacy")], model_id=9)


def test_existing_upsert_may_update_bound_raw_but_not_bind_it_to_another_model():
    db = fixture_db()
    db.add(ModelSpecValue(model_id=9, spec_definition_id=2, value="old", raw_label="old", raw_value="old", source_ref="old"))
    db.flush()
    assert "raw_legacy" in resolve_existing_spec_definitions(db, [spec("raw_legacy")], model_id=9)
    with pytest.raises(HTTPException) as exc:
        resolve_existing_spec_definitions(db, [spec("raw_legacy")], model_id=10)
    assert exc.value.status_code == 422


def test_schema_rejects_blank_field_key():
    with pytest.raises(Exception):
        spec("   ")
