"""FastAPI application factory and configuration.

This module provides the application factory function for creating
and configuring the FastAPI application with all middleware, routes,
and lifecycle handlers.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from snackbase.core.config import get_settings
from snackbase.core.hooks import HookDecorator, HookEvent, HookRegistry
from snackbase.core.logging import configure_logging, get_logger
from snackbase.domain.entities.hook_context import HookContext
from snackbase.infrastructure.hooks import register_builtin_hooks
from snackbase.infrastructure.persistence.database import (
    close_database,
    init_database,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown events for the application.

    Args:
        app: FastAPI application instance.

    Yields:
        None: Control is yielded to the application during its lifetime.
    """
    settings = get_settings()
    logger = get_logger(__name__)

    # Startup
    logger.info(
        "Starting SnackBase",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )

    # Configure logging
    configure_logging(settings)

    # Create storage directory for file uploads
    storage_path = Path(settings.storage_path)
    storage_path.mkdir(parents=True, exist_ok=True)
    logger.info("Storage directory created", path=str(storage_path))

    # Initialize database
    try:
        await init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise

    # Register built-in hooks
    if hasattr(app.state, "hook_registry"):
        register_builtin_hooks(app.state.hook_registry)
        logger.info("Built-in hooks registered")

        # Trigger ON_BOOTSTRAP hook
        bootstrap_context = HookContext(app=app)
        await app.state.hook_registry.trigger(
            event=HookEvent.ON_BOOTSTRAP,
            context=bootstrap_context,
        )
        logger.info("ON_BOOTSTRAP hooks triggered")

        # Trigger ON_SERVE hook (app is ready to serve)
        await app.state.hook_registry.trigger(
            event=HookEvent.ON_SERVE,
            context=bootstrap_context,
        )
        logger.info("ON_SERVE hooks triggered")

    yield

    # Shutdown
    logger.info("Shutting down SnackBase")

    # Trigger ON_TERMINATE hook
    if hasattr(app.state, "hook_registry"):
        terminate_context = HookContext(app=app)
        await app.state.hook_registry.trigger(
            event=HookEvent.ON_TERMINATE,
            context=terminate_context,
        )
        logger.info("ON_TERMINATE hooks triggered")

    await close_database()
    logger.info("Database connection closed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    This function creates the FastAPI application with all middleware,
    routes, and configuration.

    Returns:
        FastAPI: Configured FastAPI application instance.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Open-source Backend-as-a-Service (BaaS)",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    # Initialize hook system
    # The hook registry is the core of the extensibility system
    hook_registry = HookRegistry()
    hook_decorator = HookDecorator(hook_registry)

    # Store on app state for access throughout the application
    app.state.hook_registry = hook_registry
    app.state.hook = hook_decorator

    logger.info("Hook system initialized")

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Register health check endpoint
    register_health_check(app)

    # Register API routes
    register_routes(app)

    # Register exception handlers
    register_exception_handlers(app)

    # Register middleware
    register_middleware(app)

    return app


def register_health_check(app: FastAPI) -> None:
    """Register health check endpoints.

    Args:
        app: FastAPI application instance.
    """

    @app.get("/health", tags=["health"])
    async def health_check():
        """Basic health check endpoint.

        Returns 200 if the service is running. Does not check
        database connectivity or other dependencies.
        """
        return {
            "status": "healthy",
            "service": "SnackBase",
            "version": get_settings().app_version,
        }

    @app.get("/ready", tags=["health"])
    async def readiness_check():
        """Readiness check endpoint.

        Returns 200 if the service is ready to accept requests,
        including database connectivity check.
        """
        from snackbase.infrastructure.persistence.database import get_db_manager

        db = get_db_manager()
        db_healthy = await db.check_connection()

        if db_healthy:
            return {
                "status": "ready",
                "service": "SnackBase",
                "version": get_settings().app_version,
                "database": "connected",
            }
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "service": "SnackBase",
                    "database": "disconnected",
                },
            )

    @app.get("/live", tags=["health"])
    async def liveness_check():
        """Liveness check endpoint.

        Returns 200 if the service is alive. This is a simple check
        that the service is running and responding to requests.
        """
        return {
            "status": "alive",
            "service": "SnackBase",
            "version": get_settings().app_version,
        }


def register_routes(app: FastAPI) -> None:
    """Register API routes.

    Args:
        app: FastAPI application instance.
    """
    from snackbase.infrastructure.api.routes import (
        auth_router,
        collections_router,
        invitations_router,
        permissions_router,
        records_router,
    )

    settings = get_settings()

    # API v1 routes
    # Register auth routes
    app.include_router(auth_router, prefix=f"{settings.api_prefix}/auth", tags=["auth"])

    # Register collections routes
    app.include_router(
        collections_router, prefix=f"{settings.api_prefix}/collections", tags=["collections"]
    )

    # Register invitations routes (must be before dynamic record routes)
    app.include_router(
        invitations_router, prefix=f"{settings.api_prefix}/invitations", tags=["invitations"]
    )

    # Register permissions routes
    app.include_router(
        permissions_router, prefix=f"{settings.api_prefix}/permissions", tags=["permissions"]
    )

    # Register dynamic record routes (must be last to avoid capturing specific routes)
    app.include_router(
        records_router, prefix=settings.api_prefix, tags=["records"]
    )

    # These will be registered as we implement features
    # For now, just add a placeholder
    @app.get(settings.api_prefix, tags=["root"])
    async def api_root():
        """API root endpoint."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "api_version": "v1",
        }


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers.

    Args:
        app: FastAPI application instance.
    """

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """Handle uncaught exceptions."""
        logger.error(
            "Unhandled exception",
            path=str(request.url),
            method=request.method,
            error=str(exc),
            exc_type=type(exc).__name__,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if get_settings().debug else "An unexpected error occurred",
            },
        )


def register_middleware(app: FastAPI) -> None:
    """Register custom middleware.

    Args:
        app: FastAPI application instance.
    """

    @app.middleware("http")
    async def logging_middleware(request, call_next):
        """Middleware to log all requests and add correlation ID."""
        import uuid

        from snackbase.core.logging import bind_correlation_id, clear_context, get_logger

        logger = get_logger(__name__)

        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", f"cid_{uuid.uuid4().hex[:12]}")
        bind_correlation_id(correlation_id)

        # Log request
        logger.info(
            "Request started",
            method=request.method,
            path=str(request.url.path),
            correlation_id=correlation_id,
        )

        try:
            response = await call_next(request)
            # Log response
            logger.info(
                "Request completed",
                method=request.method,
                path=str(request.url.path),
                status_code=response.status_code,
                correlation_id=correlation_id,
            )
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        finally:
            # Clear context to prevent leakage
            clear_context()


# Create the application instance
app = create_app()
