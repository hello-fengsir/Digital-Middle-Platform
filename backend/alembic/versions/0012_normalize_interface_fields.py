"""normalize the two approved interface field definitions

Revision ID: 0012_normalize_interface_fields
Revises: 0011_merge_auto_fields
"""
from alembic import op

revision = "0012_normalize_interface_fields"
down_revision = "0011_merge_auto_fields"
branch_labels = None
depends_on = None

GUARD_KEY = "hpl.field_dictionary_migration_guard"
GUARD_VALUE = "approved-v1"

EXPECTED_SOURCE = (
    (3998, "external_ports", "接口"),
    (4401, "raw_953671", "接口"),
    (4269, "raw_367497", "接口"),
)
EXPECTED_TARGET = (
    (3998, "external_ports", "外部接口"),
    (4401, "device_bus_interface", "设备总线接口"),
    (4269, "raw_367497", "接口"),
)


def _enable_guard() -> None:
    # The third argument is deliberately true: the bypass expires with this transaction.
    op.execute(f"SELECT set_config('{GUARD_KEY}', '{GUARD_VALUE}', true)")


def _assert_rows(rows: tuple[tuple[int, str, str], ...], phase: str) -> None:
    values = ", ".join(
        f"({definition_id}, '{field_key}', '{label}')"
        for definition_id, field_key, label in rows
    )
    op.execute(f"""
        DO $assert_{phase}$
        DECLARE
          mismatch text;
        BEGIN
          SELECT string_agg(
                   format('id=%s expected=(%s,%s) actual=(%s,%s)',
                          expected.id, expected.field_key, expected.label,
                          actual.field_key, actual.label),
                   '; ' ORDER BY expected.id)
            INTO mismatch
            FROM (VALUES {values}) AS expected(id, field_key, label)
            LEFT JOIN spec_definitions AS actual ON actual.id = expected.id
           WHERE actual.id IS NULL
              OR actual.field_key IS DISTINCT FROM expected.field_key
              OR actual.label IS DISTINCT FROM expected.label;
          IF mismatch IS NOT NULL THEN
            RAISE EXCEPTION '0012 interface field {phase} state drift: %', mismatch;
          END IF;
        END
        $assert_{phase}$;
    """)


def _assert_key_available(field_key: str, owner_id: int, phase: str) -> None:
    op.execute(f"""
        DO $key_{phase}$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM spec_definitions
             WHERE field_key = '{field_key}' AND id <> {owner_id}
          ) THEN
            RAISE EXCEPTION '0012 field_key conflict during {phase}: {field_key}';
          END IF;
        END
        $key_{phase}$;
    """)


def upgrade() -> None:
    _enable_guard()
    _assert_rows(EXPECTED_SOURCE, "upgrade_source")
    _assert_key_available("device_bus_interface", 4401, "upgrade")

    op.execute("UPDATE spec_definitions SET label = '外部接口' WHERE id = 3998")
    op.execute("""
        UPDATE spec_definitions
           SET field_key = 'device_bus_interface', label = '设备总线接口'
         WHERE id = 4401
    """)

    _assert_rows(EXPECTED_TARGET, "upgrade_target")


def downgrade() -> None:
    _enable_guard()
    _assert_rows(EXPECTED_TARGET, "downgrade_source")
    _assert_key_available("raw_953671", 4401, "downgrade")

    op.execute("UPDATE spec_definitions SET label = '接口' WHERE id = 3998")
    op.execute("""
        UPDATE spec_definitions
           SET field_key = 'raw_953671', label = '接口'
         WHERE id = 4401
    """)

    _assert_rows(EXPECTED_SOURCE, "downgrade_target")
