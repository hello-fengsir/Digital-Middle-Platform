"""constrain compatible GPU relations and remove confirmed acceptance residue

Revision ID: 0005_gpu_rel_cleanup
Revises: 0004_ai_config_compatible_gpu

No GPU compatibility business data is populated by this migration.
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_gpu_rel_cleanup"
down_revision = "0004_ai_config_compatible_gpu"
branch_labels = None
depends_on = None

ACCEPTANCE_SERIES = ("管理页验收", "管理页认证验收", "参数保存验收", "登录保存验收", "OCADMIN-TEST-SERIES")
DISPOSABLE_UNUSED_FIELDS = (
    "admin_smoke_cpu", "admin_smoke_memory",
    "raw_b57b87f1f740", "raw_ab1fb7a7c5b3", "raw_af08cd59eb2e", "raw_ad77191a3de2",
)


def upgrade() -> None:
    bind = op.get_bind()
    op.create_check_constraint("ck_model_compatible_gpu_not_self", "model_compatible_gpus", "model_id <> gpu_model_id")

    if bind.dialect.name == "postgresql":
        # PostgreSQL CHECK/FK cannot express cross-table predicates. Trigger is the
        # final race-safe guard, complementing the API's friendly validation.
        op.execute("""
        CREATE FUNCTION hpl_validate_model_compatible_gpu()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE source_is_gpu boolean; source_is_active boolean;
                target_is_gpu boolean; target_is_active boolean;
        BEGIN
          SELECT (lower(b.code)='accessory' OR lower(pt.code)='gpu_card' OR pt.name='显卡'),
                 (m.deleted_at IS NULL AND m.status='active' AND b.deleted_at IS NULL AND b.status='active'
                  AND pt.deleted_at IS NULL AND pt.status='active')
            INTO source_is_gpu,source_is_active
            FROM models m JOIN brands b ON b.id=m.brand_id JOIN product_types pt ON pt.id=m.product_type_id
           WHERE m.id=NEW.model_id;
          SELECT (lower(b.code)='accessory' AND lower(pt.code)='gpu_card' AND pt.name='显卡'),
                 (m.deleted_at IS NULL AND m.status='active' AND b.deleted_at IS NULL AND b.status='active'
                  AND pt.deleted_at IS NULL AND pt.status='active')
            INTO target_is_gpu,target_is_active
            FROM models m JOIN brands b ON b.id=m.brand_id JOIN product_types pt ON pt.id=m.product_type_id
           WHERE m.id=NEW.gpu_model_id;
          IF NOT coalesce(source_is_active,false) THEN RAISE EXCEPTION 'compatible GPU source model must be active and not deleted'; END IF;
          IF coalesce(source_is_gpu,true) THEN RAISE EXCEPTION 'compatible GPU source model must not be a GPU/accessory model'; END IF;
          IF NOT coalesce(target_is_active,false) THEN RAISE EXCEPTION 'compatible GPU target model must be active and not deleted'; END IF;
          IF NOT coalesce(target_is_gpu,false) THEN RAISE EXCEPTION 'compatible GPU target must be accessory/gpu_card/显卡'; END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_validate_model_compatible_gpu
        BEFORE INSERT OR UPDATE OF model_id,gpu_model_id ON model_compatible_gpus
        FOR EACH ROW EXECUTE FUNCTION hpl_validate_model_compatible_gpu();
        """)
        # Do not let later soft-delete/reclassification invalidate an existing edge.
        op.execute("""
        CREATE FUNCTION hpl_guard_related_model_update()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF EXISTS (SELECT 1 FROM model_compatible_gpus r WHERE r.model_id=NEW.id OR r.gpu_model_id=NEW.id)
             AND (NEW.deleted_at IS NOT NULL OR NEW.status<>'active'
                  OR NEW.brand_id IS DISTINCT FROM OLD.brand_id OR NEW.product_type_id IS DISTINCT FROM OLD.product_type_id)
          THEN RAISE EXCEPTION 'remove compatible GPU relations before deleting or reclassifying model %',NEW.id;
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER trg_guard_related_model_update
        BEFORE UPDATE OF deleted_at,status,brand_id,product_type_id ON models
        FOR EACH ROW EXECUTE FUNCTION hpl_guard_related_model_update();
        """)

    bind.execute(sa.text("""DELETE FROM series s WHERE s.name IN :names
        AND NOT EXISTS (SELECT 1 FROM models m WHERE m.series_id=s.id)""").bindparams(sa.bindparam("names", expanding=True)),
        {"names": list(ACCEPTANCE_SERIES)})
    bind.execute(sa.text("""DELETE FROM spec_definitions sd WHERE sd.field_key IN :keys
        AND NOT EXISTS (SELECT 1 FROM model_spec_values v WHERE v.spec_definition_id=sd.id)""").bindparams(sa.bindparam("keys", expanding=True)),
        {"keys": list(DISPOSABLE_UNUSED_FIELDS)})
    bind.execute(sa.text("DELETE FROM model_spec_values WHERE btrim(coalesce(value,''))=''"))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_guard_related_model_update ON models")
        op.execute("DROP FUNCTION IF EXISTS hpl_guard_related_model_update()")
        op.execute("DROP TRIGGER IF EXISTS trg_validate_model_compatible_gpu ON model_compatible_gpus")
        op.execute("DROP FUNCTION IF EXISTS hpl_validate_model_compatible_gpu()")
    op.drop_constraint("ck_model_compatible_gpu_not_self", "model_compatible_gpus", type_="check")
    # Deleted acceptance residue is intentionally irreversible; restore the mandatory pre-migration dump if needed.
