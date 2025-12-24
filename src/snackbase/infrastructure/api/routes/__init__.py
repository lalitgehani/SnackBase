"""API Routes for SnackBase."""

from snackbase.infrastructure.api.routes.auth_router import router as auth_router

__all__ = [
    "auth_router",
]
