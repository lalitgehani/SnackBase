"""API Routes for SnackBase."""

from snackbase.infrastructure.api.routes.auth_router import router as auth_router
from .accounts_router import router as accounts_router
from .admin_router import router as admin_router
from .collections_router import router as collections_router
from .dashboard_router import router as dashboard_router
from .email_templates_router import router as email_templates_router
from .files_router import router as files_router
from .groups_router import router as groups_router
from .invitations_router import router as invitations_router
from .macros_router import router as macros_router
from .migrations_router import router as migrations_router
from .permissions_router import router as permissions_router
from .records_router import router as records_router
from .roles_router import router as roles_router
from .users_router import router as users_router
from .audit_log_router import router as audit_log_router
from .oauth_router import router as oauth_router
from .saml_router import router as saml_router
from .api_keys_router import router as api_keys_router
from .realtime_router import router as realtime_router

__all__ = [
    "accounts_router",
    "admin_router",
    "auth_router",
    "collections_router",
    "dashboard_router",
    "email_templates_router",
    "files_router",
    "groups_router",
    "invitations_router",
    "macros_router",
    "migrations_router",
    "permissions_router",
    "records_router",
    "roles_router",
    "users_router",
    "audit_log_router",
    "oauth_router",
    "saml_router",
    "api_keys_router",
    "realtime_router",
]

