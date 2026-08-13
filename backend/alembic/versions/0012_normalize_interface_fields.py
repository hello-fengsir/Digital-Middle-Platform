"""Sanitized lineage placeholder.

The private deployment normalized fixed production dictionary rows. Public source
initializes an empty catalog and intentionally performs no row mutation.
"""
revision = "0012_normalize_interface_fields"
down_revision = "0011_merge_auto_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
