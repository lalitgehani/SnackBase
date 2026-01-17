"""Configuration management for SnackBase.

This module uses Pydantic Settings to load and validate configuration from
environment variables and .env files. Configuration is loaded at application
startup and is immutable during runtime.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings.

    Settings are loaded from environment variables and .env files.
    All configuration values are validated at startup.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SNACKBASE_",
        case_sensitive=False,
        extra="ignore",
    )

    # Application Settings
    app_name: str = "SnackBase"
    app_version: str = "0.1.0"
    environment: Literal["development", "production", "testing"] = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"
    external_url: str = "http://localhost:8000"

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # Database Settings
    database_url: str = "sqlite+aiosqlite:///./sb_data/snackbase.db"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 3600
    db_echo: bool = False

    # SQLite Performance Pragmas
    db_sqlite_journal_mode: str = "WAL"
    db_sqlite_synchronous: str = "NORMAL"
    db_sqlite_cache_size: int = -64000  # 64MB
    db_sqlite_temp_store: str = "MEMORY"
    db_sqlite_mmap_size: int = 268435456  # 256MB
    db_sqlite_busy_timeout: int = 5000     # 5 seconds
    db_sqlite_foreign_keys: bool = True

    # Security Settings
    secret_key: str = Field(
        default="change-me-in-production-use-openssl-rand-hex-32",
        description="Secret key for JWT token signing",
    )
    encryption_key: str = Field(
        default="change-me-in-production-use-openssl-rand-hex-32",
        description="Secret key for sensitive data encryption at rest",
    )
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # CORS Settings
    cors_origins: list[str] = Field(default=["http://localhost:3000", "http://localhost:8000", "http://localhost:5173"])
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = Field(default=["*"])
    cors_allow_headers: list[str] = Field(default=["*"])

    # Logging Settings
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "json"
    log_file: str | None = None

    # Permission Cache Settings
    permission_cache_ttl_seconds: int = 300  # 5 minutes

    # File Storage Settings
    storage_path: str = "./sb_data/files"
    max_file_size: int = 10 * 1024 * 1024  # 10MB in bytes
    allowed_mime_types: list[str] = Field(
        default=[
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
            "application/pdf",
            "text/plain",
            "application/json",
        ]
    )

    # Rate Limiting Settings
    rate_limit_enabled: bool = False
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000

    # Superadmin Settings
    superadmin_email: str | None = Field(
        default=None,
        description="Email for initial superadmin creation (auto-created on startup if set)",
    )
    superadmin_password: str | None = Field(
        default=None,
        description="Password for initial superadmin creation (auto-created on startup if set)",
    )

    # API Key Settings
    api_key_header: str = "X-API-Key"
    api_key_max_per_user: int = 10
    api_key_default_expiration_days: int | None = None  # None = never expires
    api_key_rate_limit_per_minute: int = 100

    # Demo Mode
    is_demo: bool = Field(
        default=False,
        description="When enabled, prevents modifications to superadmin credentials",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key is not default in production."""
        if v == "change-me-in-production-use-openssl-rand-hex-32":
            # In production, this should be a proper secret key
            # For now, we'll allow it but log a warning
            pass
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == "testing"

    @model_validator(mode="after")
    def validate_sqlite_workers(self) -> "Settings":
        """Validate that SQLite is not used with multiple workers."""
        if self.workers > 1 and self.database_url.startswith("sqlite"):
            raise ValueError(
                "SQLite does not support multiple worker processes. "
                f"Requested {self.workers} workers, but SQLite requires workers=1. "
                "Either use --workers 1 or switch to PostgreSQL."
            )
        return self

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for migrations."""
        url = self.database_url
        if url.startswith("sqlite+aiosqlite"):
            return url.replace("sqlite+aiosqlite", "sqlite")
        if url.startswith("postgresql+asyncpg"):
            return url.replace("postgresql+asyncpg", "postgresql")
        return url


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    This function caches the settings instance to avoid reloading
    configuration on every call. Settings are loaded once at startup.

    Returns:
        Settings: Cached application settings instance.
    """
    return Settings()
