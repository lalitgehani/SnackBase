"""move_saml_providers_category

Revision ID: 20261108_saml_category
Revises: 20260812_files
Create Date: 2026-11-08

SAML provider definitions used to be registered under ``auth_providers`` while
every SAML endpoint read them from ``saml_providers``, so a configured provider
was never found. Move existing rows to the category the SAML flow reads.

Rows are only moved when the target ``saml_providers`` row does not already
exist for the same account, to avoid violating
``uq_configurations_category_provider_account``. A pre-existing duplicate is
left untouched rather than deleted, so no configuration is lost.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261108_saml_category"
down_revision: str | Sequence[str] | None = "20260812_files"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SAML_PROVIDER_NAMES = ("okta", "azure_ad", "generic_saml")

MOVE_TO_READ_CATEGORY = """
UPDATE configurations
SET category = 'saml_providers'
WHERE category = 'auth_providers'
  AND provider_name IN ('okta', 'azure_ad', 'generic_saml')
  AND NOT EXISTS (
      SELECT 1
      FROM configurations AS existing
      WHERE existing.category = 'saml_providers'
        AND existing.provider_name = configurations.provider_name
        AND existing.account_id = configurations.account_id
  )
"""

MOVE_TO_WRITE_CATEGORY = """
UPDATE configurations
SET category = 'auth_providers'
WHERE category = 'saml_providers'
  AND provider_name IN ('okta', 'azure_ad', 'generic_saml')
  AND NOT EXISTS (
      SELECT 1
      FROM configurations AS existing
      WHERE existing.category = 'auth_providers'
        AND existing.provider_name = configurations.provider_name
        AND existing.account_id = configurations.account_id
  )
"""


def upgrade() -> None:
    """Move SAML provider configurations to ``saml_providers``."""
    op.execute(MOVE_TO_READ_CATEGORY)


def downgrade() -> None:
    """Move SAML provider configurations back to ``auth_providers``."""
    op.execute(MOVE_TO_WRITE_CATEGORY)
