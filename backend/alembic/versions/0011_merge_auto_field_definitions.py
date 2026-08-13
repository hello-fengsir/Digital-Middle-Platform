"""Sanitized lineage placeholder.

The private deployment merged fixed production dictionary rows. Public source
initializes an empty catalog and intentionally performs no row mutation.
"""
revision = "0011_merge_auto_fields"
down_revision = "0010_field_dictionary_guard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
