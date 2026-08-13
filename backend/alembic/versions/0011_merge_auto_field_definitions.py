"""apply the ten approved MERGE_AUTO lossless dictionary merges

Revision ID: 0011_merge_auto_fields
Revises: 0010_field_dictionary_guard

3998 (external interface), 4401 (device bus interface), 4269/raw_367497,
and both product-positioning domains are protected controls.
"""
from alembic import op

revision = "0011_merge_auto_fields"
down_revision = "0010_field_dictionary_guard"
branch_labels = None
depends_on = None

MERGES = (
    (5326, 12, "storage Chinese label normalization"),
    (5095, 3915, "MTBF parenthesis normalization"),
    (5076, 4272, "128KB sequential write whitespace"),
    (4289, 4273, "4KB random read whitespace"),
    (4291, 4275, "4KB read latency whitespace"),
    (5080, 4276, "4KB write latency whitespace"),
    (4308, 4281, "UBER parenthesis normalization"),
    (4287, 5059, "128KB sequential read whitespace"),
    (4290, 5062, "4KB random write whitespace"),
    (5057, 4401, "device bus interface duplicate; excludes external interface 3998 and raw 4269"),
)


def upgrade() -> None:
    op.execute("SELECT set_config('hpl.field_dictionary_migration_guard', 'approved-v1', true)")
    op.execute("""CREATE TABLE IF NOT EXISTS field_dictionary_migration_ledger (
      id bigserial PRIMARY KEY, revision varchar(64) NOT NULL,
      source_definition_id integer NOT NULL, target_definition_id integer NOT NULL,
      reason text NOT NULL, moved_values integer NOT NULL,
      executed_at timestamptz NOT NULL DEFAULT now(), UNIQUE(revision, source_definition_id))""")
    for source, target, reason in MERGES:
        safe_reason = reason.replace("'", "''")
        op.execute(f"""DO $merge$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM spec_definitions WHERE id={source})
             OR NOT EXISTS (SELECT 1 FROM spec_definitions WHERE id={target}) THEN
            RAISE EXCEPTION 'MERGE_AUTO definition id drift: {source}->{target}'; END IF;
          IF EXISTS (SELECT 1 FROM model_spec_values s JOIN model_spec_values t
             ON t.model_id=s.model_id AND t.spec_definition_id={target}
            WHERE s.spec_definition_id={source}
              AND regexp_replace(lower(trim(s.value)), '[[:space:]]+', ' ', 'g')
                  <> regexp_replace(lower(trim(t.value)), '[[:space:]]+', ' ', 'g')) THEN
            RAISE EXCEPTION 'MERGE_AUTO value conflict: {source}->{target}'; END IF;
        END $merge$""")
        # Separate statements are intentional: PostgreSQL may execute sibling data-
        # modifying CTEs in an order that violates uq_model_spec during deduplication.
        op.execute(f"""INSERT INTO field_dictionary_migration_ledger
          (revision,source_definition_id,target_definition_id,reason,moved_values)
          SELECT '0011_merge_auto_fields',{source},{target},'{safe_reason}',count(*)
            FROM model_spec_values WHERE spec_definition_id={source}
          ON CONFLICT DO NOTHING""")
        op.execute(f"""DELETE FROM model_spec_values s USING model_spec_values t
          WHERE s.spec_definition_id={source} AND t.spec_definition_id={target}
            AND s.model_id=t.model_id""")
        op.execute(f"UPDATE model_spec_values SET spec_definition_id={target} WHERE spec_definition_id={source}")
        op.execute(f"DELETE FROM spec_definitions WHERE id={source}")
    op.execute("""DO $control$ BEGIN
      IF NOT EXISTS (SELECT 1 FROM spec_definitions WHERE id=3998) THEN
        RAISE EXCEPTION 'protected external interface 3998 was modified'; END IF;
      IF NOT EXISTS (SELECT 1 FROM spec_definitions WHERE id=4401) THEN
        RAISE EXCEPTION 'protected device bus interface 4401 was modified'; END IF;
      IF NOT EXISTS (SELECT 1 FROM spec_definitions WHERE id=4269 AND field_key='raw_367497') THEN
        RAISE EXCEPTION 'protected 4269 was modified'; END IF;
      IF NOT EXISTS (SELECT 1 FROM spec_definitions WHERE field_key='product_positioning')
         OR NOT EXISTS (SELECT 1 FROM spec_definitions WHERE field_key='gpu_product_positioning') THEN
        RAISE EXCEPTION 'cross-domain product positioning was modified'; END IF;
    END $control$""")


def downgrade() -> None:
    raise RuntimeError("Restore the isolated pre-migration dump; never infer deleted definitions")
