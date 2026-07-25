"""remove_builtin_regions_seed

Revision ID: 20260725_no_default_regions
Revises: 20260725_codelists
Create Date: 2026-07-25

Removes the temporary platform-default ``regions`` / ``eu-01`` seed rows if present.
Codelists start empty; product seeds (e.g. control-plane) create catalogs as needed.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260725_no_default_regions"
down_revision: str | Sequence[str] | None = "20260725_codelists"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Fixed IDs used by the removed seed (safe to delete only these rows)
REGIONS_CODELIST_ID = "00000000-0000-0000-0000-00000000c001"
EU01_VALUE_ID = "00000000-0000-0000-0000-00000000c0e1"
EU01_LABEL_EN_ID = "00000000-0000-0000-0000-00000000c1e1"


def upgrade() -> None:
    """Delete fixed builtin regions seed rows if they still exist."""
    # Order: labels → values → codelist (FK)
    op.execute(
        f"DELETE FROM codelist_value_labels WHERE id = '{EU01_LABEL_EN_ID}'"
    )
    op.execute(f"DELETE FROM codelist_values WHERE id = '{EU01_VALUE_ID}'")
    op.execute(f"DELETE FROM codelists WHERE id = '{REGIONS_CODELIST_ID}'")


def downgrade() -> None:
    """No re-seed: platform does not restore a default regions dictionary."""
    pass
