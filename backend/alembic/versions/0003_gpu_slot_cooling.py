"""add gpu slot width and cooling display fields

Revision ID: 0003_gpu_slot_cooling
Revises: 0002_cpu_compatibility
"""
from alembic import op

revision = "0003_gpu_slot_cooling"
down_revision = "0002_cpu_compatibility"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    WITH gpu_group AS (SELECT id FROM spec_groups WHERE code='gpu' LIMIT 1)
    INSERT INTO spec_definitions(group_id, field_key, label, sort_order)
    SELECT id, 'gpu_slot_width', '槽宽', 85 FROM gpu_group
    ON CONFLICT (field_key) DO UPDATE SET label=excluded.label, sort_order=excluded.sort_order;
    """)
    op.execute("""
    WITH gpu_group AS (SELECT id FROM spec_groups WHERE code='gpu' LIMIT 1)
    INSERT INTO spec_definitions(group_id, field_key, label, sort_order)
    SELECT id, 'gpu_cooling_type', '散热方式', 86 FROM gpu_group
    ON CONFLICT (field_key) DO UPDATE SET label=excluded.label, sort_order=excluded.sort_order;
    """)


def downgrade() -> None:
    op.execute("DELETE FROM model_spec_values WHERE spec_definition_id IN (SELECT id FROM spec_definitions WHERE field_key IN ('gpu_slot_width','gpu_cooling_type'))")
    op.execute("DELETE FROM spec_definitions WHERE field_key IN ('gpu_slot_width','gpu_cooling_type')")
