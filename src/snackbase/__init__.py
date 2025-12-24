"""SnackBase - Open-source Backend-as-a-Service.

A self-hosted alternative to PocketBase with multi-tenancy,
row-level security, and GxP-compliant audit logging.
"""

__version__ = "0.1.0"

from snackbase.infrastructure.api.app import app

__all__ = ["app", "__version__"]
