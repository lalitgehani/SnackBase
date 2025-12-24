"""Infrastructure layer - External dependencies and implementations.

This layer contains all external dependencies including:
- Database adapters (SQLAlchemy)
- API routes (FastAPI)
- Authentication (JWT, OAuth, SAML)
- Realtime (WebSocket, SSE)
- Storage (filesystem, S3)

The infrastructure layer implements interfaces defined in the
application and domain layers.
"""

from snackbase.infrastructure.persistence.database import (
    Base,
    DatabaseManager,
    close_database,
    get_db_manager,
    get_db_session,
    init_database,
)

__all__ = [
    "Base",
    "DatabaseManager",
    "get_db_manager",
    "get_db_session",
    "init_database",
    "close_database",
]
