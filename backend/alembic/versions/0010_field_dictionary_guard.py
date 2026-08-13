"""hard-lock field dictionary DML behind a transaction-local migration guard

Revision ID: 0010_field_dictionary_guard
Revises: 0009_controlled_lifecycle_tags
"""
from alembic import op

revision = "0010_field_dictionary_guard"
down_revision = "0009_controlled_lifecycle_tags"
branch_labels = None
depends_on = None

GUARD_KEY = "hpl.field_dictionary_migration_guard"
GUARD_VALUE = "approved-v1"


def enable_dictionary_migration_guard() -> None:
    """Controlled exception, valid only for the current DB transaction."""
    op.execute(f"SELECT set_config('{GUARD_KEY}', '{GUARD_VALUE}', true)")


def upgrade() -> None:
    op.execute("""
    CREATE OR REPLACE FUNCTION hpl_reject_dictionary_dml()
    RETURNS trigger LANGUAGE plpgsql AS $guard$
    BEGIN
      IF current_setting('hpl.field_dictionary_migration_guard', true) IS DISTINCT FROM 'approved-v1' THEN
        RAISE EXCEPTION 'FIELD_DICTIONARY_LOCKED' USING ERRCODE = '55006';
      END IF;
      RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
    END
    $guard$;
    CREATE TRIGGER trg_spec_groups_dictionary_lock BEFORE INSERT OR UPDATE OR DELETE ON spec_groups
      FOR EACH ROW EXECUTE FUNCTION hpl_reject_dictionary_dml();
    CREATE TRIGGER trg_spec_definitions_dictionary_lock BEFORE INSERT OR UPDATE OR DELETE ON spec_definitions
      FOR EACH ROW EXECUTE FUNCTION hpl_reject_dictionary_dml();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_spec_definitions_dictionary_lock ON spec_definitions")
    op.execute("DROP TRIGGER IF EXISTS trg_spec_groups_dictionary_lock ON spec_groups")
    op.execute("DROP FUNCTION IF EXISTS hpl_reject_dictionary_dml()")
