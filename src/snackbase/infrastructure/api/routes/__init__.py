"""API Routes for SnackBase."""

from snackbase.infrastructure.api.routes.auth_router import router as auth_router
from snackbase.infrastructure.api.routes.collections_router import (
    router as collections_router,
)
from snackbase.infrastructure.api.routes.records_router import router as records_router

__all__ = [
    "auth_router",
    "collections_router",
    "records_router",
]


