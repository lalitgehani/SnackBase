"""API Routes for SnackBase."""

from snackbase.infrastructure.api.routes.auth_router import router as auth_router
from .collections_router import router as collections_router
from .groups_router import router as groups_router
from .invitations_router import router as invitations_router
from .macros_router import router as macros_router
from .permissions_router import router as permissions_router
from .records_router import router as records_router

__all__ = [
    "auth_router",
    "collections_router",
    "invitations_router",
    "macros_router",
    "permissions_router",
    "records_router",
]
