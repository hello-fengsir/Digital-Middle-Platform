import hashlib
import os
from contextlib import contextmanager
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


DATABASE_URL = os.getenv("MIGRATION_TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="set MIGRATION_TEST_DATABASE_URL to an isolated PostgreSQL database restored at 0011",
)

EXPECTED_SOURCE = {
    3998: ("external_ports", "接口"),
    4401: ("raw_953671", "接口"),
    4269: ("raw_367497", "接口"),
}
EXPECTED_TARGET = {
    3998: ("external_ports", "外部接口"),
    4401: ("device_bus_interface", "设备总线接口"),
    4269: ("raw_367497", "接口"),
}


def _alembic_config() -> Config:
    backend = Path(__file__).parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "alembic"))
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
    return config


@contextmanager
def _migration_database_url():
    """Make env.py resolve the isolated PostgreSQL URL, then restore process state."""
    from app.config import settings

    previous_env = os.environ.get("DATABASE_URL")
    previous_setting = settings.database_url
    os.environ["DATABASE_URL"] = DATABASE_URL
    settings.database_url = DATABASE_URL
    try:
        yield
    finally:
        settings.database_url = previous_setting
        if previous_env is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_env


def _rows(connection):
    return {
        row.id: (row.field_key, row.label)
        for row in connection.execute(
            text("SELECT id, field_key, label FROM spec_definitions WHERE id IN (3998, 4401, 4269)")
        )
    }


def _value_reference_digest(connection):
    digest = hashlib.sha256()
    for row in connection.execute(
        text("SELECT id, model_id, spec_definition_id FROM model_spec_values ORDER BY id")
    ):
        digest.update(f"{row.id}:{row.model_id}:{row.spec_definition_id}\n".encode())
    return digest.hexdigest()


def test_0012_upgrade_downgrade_trigger_and_invariants():
    with _migration_database_url():
        _run_0012_upgrade_downgrade_upgrade()


def _run_0012_upgrade_downgrade_upgrade():
    engine = create_engine(DATABASE_URL)
    config = _alembic_config()

    current = engine.connect().scalar(text("SELECT version_num FROM alembic_version"))
    if current == "0012_normalize_interface_fields":
        command.downgrade(config, "0011_merge_auto_fields")
    elif current != "0011_merge_auto_fields":
        command.upgrade(config, "0011_merge_auto_fields")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0011_merge_auto_fields"
        assert _rows(connection) == EXPECTED_SOURCE
        baseline = (
            connection.scalar(text("SELECT count(*) FROM spec_definitions")),
            connection.scalar(text("SELECT count(*) FROM model_spec_values")),
            _value_reference_digest(connection),
        )
        assert baseline[:2] == (180, 6231)

        with pytest.raises(Exception, match="FIELD_DICTIONARY_LOCKED"):
            with engine.begin() as blocked:
                blocked.execute(text("UPDATE spec_definitions SET label=label WHERE id=4269"))

    command.upgrade(config, "0012_normalize_interface_fields")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0012_normalize_interface_fields"
        assert _rows(connection) == EXPECTED_TARGET
        upgraded = (
            connection.scalar(text("SELECT count(*) FROM spec_definitions")),
            connection.scalar(text("SELECT count(*) FROM model_spec_values")),
            _value_reference_digest(connection),
        )
        assert upgraded == baseline

        with pytest.raises(Exception, match="FIELD_DICTIONARY_LOCKED"):
            with engine.begin() as blocked:
                blocked.execute(text("UPDATE spec_definitions SET label=label WHERE id=4269"))

        with engine.begin() as guarded:
            guarded.execute(text("SELECT set_config('hpl.field_dictionary_migration_guard', 'approved-v1', true)"))
            guarded.execute(text("UPDATE spec_definitions SET label=label WHERE id=4269"))
        with pytest.raises(Exception, match="FIELD_DICTIONARY_LOCKED"):
            with engine.begin() as expired:
                expired.execute(text("UPDATE spec_definitions SET label=label WHERE id=4269"))

    command.downgrade(config, "0011_merge_auto_fields")
    with engine.connect() as connection:
        assert _rows(connection) == EXPECTED_SOURCE
        restored = (
            connection.scalar(text("SELECT count(*) FROM spec_definitions")),
            connection.scalar(text("SELECT count(*) FROM model_spec_values")),
            _value_reference_digest(connection),
        )
        assert restored == baseline

    command.upgrade(config, "0012_normalize_interface_fields")
    with engine.connect() as connection:
        assert _rows(connection) == EXPECTED_TARGET
        assert (
            connection.scalar(text("SELECT count(*) FROM spec_definitions")),
            connection.scalar(text("SELECT count(*) FROM model_spec_values")),
            _value_reference_digest(connection),
        ) == baseline
