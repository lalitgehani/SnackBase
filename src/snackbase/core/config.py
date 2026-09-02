"""Configuration management for SnackBase.

This module uses Pydantic Settings to load and validate configuration from
environment variables and .env files. Configuration is loaded at application
startup and is immutable during runtime.
"""

import ipaddress
import json
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cached_property, lru_cache
from typing import Annotated, Any, Literal

from pydantic import BeforeValidator, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import DotEnvSettingsSource, EnvSettingsSource

# The placeholder shipped in `.env.example`, `docker-compose.yml` and the docs.
# Production refuses to boot on it — see `validate_production_signing_secrets`.
DEFAULT_SIGNING_SECRET = "change-me-in-production-use-openssl-rand-hex-32"


def _decode_complex_value(value: Any) -> Any:
    """Leniently decode an env-provided value for a complex field.

    Accepts JSON arrays/objects (when a deployment tool forwards a stringified
    structure) and plain comma-separated strings (the 12-factor convention).
    Native Python collections are passed through unchanged.
    """
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if stripped and stripped[0] in "[{":
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass
    return [item.strip() for item in stripped.split(",") if item.strip()]


class _LenientEnvSettingsSource(EnvSettingsSource):
    """Env source that decodes complex fields from JSON *or* comma-separated values."""

    def decode_complex_value(self, field_name: str, field: Any, value: Any) -> Any:
        return _decode_complex_value(value)


class _LenientDotEnvSettingsSource(DotEnvSettingsSource):
    """Dotenv source that decodes complex fields from JSON *or* comma-separated values."""

    def decode_complex_value(self, field_name: str, field: Any, value: Any) -> Any:
        return _decode_complex_value(value)


# A list[str] field that tolerates a CSV string or JSON array when set directly
# (env/dotenv loading is handled by the lenient settings sources above).
CommaSepList = Annotated[list[str], BeforeValidator(_decode_complex_value)]

#: A ``trusted_proxies`` entry meaning "trust whatever peer connects", the same
#: escape hatch as ``uvicorn --forwarded-allow-ips '*'``.
TRUSTED_PROXY_WILDCARD = "*"

IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


@dataclass(frozen=True)
class TrustedProxies:
    """Which socket peers may have their forwarding headers believed.

    Entries are parsed once — ``get_client_ip`` runs on every API request — and
    an unparseable entry is a startup failure rather than a silent skip, because
    a dropped entry produces exactly the shared-bucket misattribution the setting
    exists to prevent.
    """

    trust_any: bool
    networks: tuple[IPNetwork, ...]

    def matches(self, peer: str) -> bool:
        """Return whether this peer address is a configured trusted proxy.

        Args:
            peer: The socket peer address.

        Returns:
            True when the peer is trusted and its forwarding headers may be used.
        """
        if self.trust_any:
            return True

        try:
            address = ipaddress.ip_address(peer)
        except ValueError:
            return False

        return any(address in network for network in self.networks)


def parse_trusted_proxies(entries: Sequence[str]) -> TrustedProxies:
    """Parse trusted-proxy entries into a matcher.

    Each entry may be a bare address (``127.0.0.1``), a CIDR network
    (``10.0.0.0/8``), or the literal ``*``.

    Args:
        entries: The configured entries.

    Raises:
        ValueError: If an entry is neither an address, a network, nor ``*``.

    Returns:
        A matcher over the parsed entries.
    """
    networks: list[IPNetwork] = []
    trust_any = False

    for entry in entries:
        candidate = entry.strip()
        if not candidate:
            continue
        if candidate == TRUSTED_PROXY_WILDCARD:
            trust_any = True
            continue
        try:
            networks.append(ipaddress.ip_network(candidate, strict=False))
        except ValueError as exc:
            raise ValueError(
                f"SNACKBASE_TRUSTED_PROXIES entry {entry!r} is not a valid IP address, "
                f"CIDR network, or '*': {exc}"
            ) from exc

    return TrustedProxies(trust_any=trust_any, networks=tuple(networks))


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

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        file_secret_settings: Any,
    ) -> tuple[Any, ...]:
        """Load settings from lenient sources that accept JSON or CSV list values."""
        return (
            init_settings,
            _LenientEnvSettingsSource(settings_cls),
            _LenientDotEnvSettingsSource(settings_cls),
            file_secret_settings,
        )

    # Application Settings
    app_name: str = "SnackBase"
    app_version: str = "0.11.0"
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
    db_sqlite_busy_timeout: int = 5000  # 5 seconds
    db_sqlite_foreign_keys: bool = True

    # Security Settings
    secret_key: str = Field(
        default=DEFAULT_SIGNING_SECRET,
        description="Secret key for JWT token signing (legacy)",
    )
    token_secret: str = Field(
        default=DEFAULT_SIGNING_SECRET,
        description="Secret key for all SnackBase tokens (JWT, API Keys, etc.)",
    )
    encryption_key: str = Field(
        default="change-me-in-production-use-openssl-rand-hex-32",
        description="Secret key for sensitive data encryption at rest (SNACKBASE_ENCRYPTION_KEY)",
    )
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # CORS Settings
    cors_origins: CommaSepList = Field(
        default=["http://localhost:3000", "http://localhost:8000", "http://localhost:5173"]
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: CommaSepList = Field(default=["*"])
    cors_allow_headers: CommaSepList = Field(default=["*"])

    # Logging Settings
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "json"
    log_file: str | None = None

    # File Storage Settings
    storage_path: str = "./sb_data/files"
    max_file_size: int = 10 * 1024 * 1024  # 10MB in bytes
    allowed_mime_types: CommaSepList = Field(
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
    # On by default: a throttle an operator has to discover and switch on is not
    # a throttle. Raise the numbers rather than turning this off.
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60
    rate_limit_burst_multiplier: float = Field(
        default=1.0,
        description=(
            "Burst ceiling expressed as a multiple of the per-minute allowance. "
            "1.0 lets a client spend a full minute's budget at once; the bucket "
            "then refills at the per-minute rate."
        ),
    )
    rate_limit_authenticated_per_minute: int = 120
    rate_limit_endpoints: dict[str, int] = Field(default_factory=dict)
    trusted_proxies: CommaSepList = Field(
        default=["127.0.0.1", "::1"],
        description=(
            "Peers whose X-Forwarded-For or CF-Connecting-IP header may be trusted "
            "for client-IP derivation. Each entry is a bare address (127.0.0.1), a "
            "CIDR network (10.0.0.0/8), or the literal '*' to trust any peer. "
            "Anything else collapses every proxied client into one rate-limit "
            "bucket, or lets a client forge its own identity. Use '*' on a managed "
            "platform whose edge address is not stable, but only when the "
            "application is not directly reachable from the internet."
        ),
    )

    # Login Brute-Force Protection
    # The per-IP throttle must trip before the per-account lockout, so that
    # hammering one victim locks out the attacker's address rather than the
    # victim's account.
    login_rate_limit_per_minute: int = Field(
        default=10,
        description="Failed logins allowed per client IP per minute.",
    )
    login_lockout_threshold: int = Field(
        default=20,
        description="Consecutive failed logins before an account is locked.",
    )
    login_lockout_seconds: int = Field(
        default=900,
        description="Base lockout duration; doubles for each further lockout.",
    )

    # SAML Settings
    saml_clock_skew_seconds: int = Field(
        default=60,
        description=(
            "Tolerance applied to SAML assertion NotBefore/NotOnOrAfter. Widen "
            "only as far as your clock drift demands: it directly extends the "
            "window in which a captured assertion stays usable."
        ),
    )

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

    # Security Headers Settings
    security_headers_enabled: bool = Field(
        default=True,
        description="Enable security headers middleware",
    )
    hsts_max_age: int = Field(
        default=31536000,  # 1 year in seconds
        description="HSTS max-age in seconds (only applied in production)",
    )
    csp_policy: str = Field(
        default="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'",
        description="Content Security Policy header value",
    )
    permissions_policy: str = Field(
        default="geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=(), gyroscope=(), accelerometer=()",
        description="Permissions-Policy header value",
    )
    https_redirect_enabled: bool = Field(
        default=False,
        description="Redirect HTTP to HTTPS in production (requires reverse proxy for actual HTTPS)",
    )

    # Single-Tenant Mode Settings
    single_tenant_mode: bool = Field(
        default=False,
        description="Enable single-tenant mode (all registrations join pre-configured account)",
    )
    single_tenant_account: str | None = Field(
        default=None,
        description="Account slug for single-tenant mode (required when mode=true)",
    )
    single_tenant_account_name: str | None = Field(
        default=None,
        description="Display name for single-tenant account (defaults to slug)",
    )

    # Platform (Trusted Issuer) Authentication Settings
    # Optional federated access: leave unset for default-off behaviour identical to
    # instances that have never heard of an external issuer.
    platform_issuer: str | None = Field(
        default=None,
        description="Trusted JWT issuer URL (SNACKBASE_PLATFORM_ISSUER)",
    )
    platform_jwks_url: str | None = Field(
        default=None,
        description="JWKS endpoint for the trusted issuer (SNACKBASE_PLATFORM_JWKS_URL)",
    )
    platform_audience: str | None = Field(
        default=None,
        description="Expected aud claim for platform tokens (SNACKBASE_PLATFORM_AUDIENCE)",
    )
    platform_role_claim: str = Field(
        default="snackbase_role",
        description="JWT claim carrying the SnackBase role name (SNACKBASE_PLATFORM_ROLE_CLAIM)",
    )
    platform_email_claim: str = Field(
        default="email",
        description="JWT claim carrying the user email (SNACKBASE_PLATFORM_EMAIL_CLAIM)",
    )
    platform_jwks_cache_seconds: int = Field(
        default=300,
        description="JWKS signing-key cache TTL in seconds (SNACKBASE_PLATFORM_JWKS_CACHE_SECONDS)",
    )
    platform_max_token_age_seconds: int = Field(
        default=300,
        description=(
            "Reject platform tokens whose iat is older than this many seconds "
            "(SNACKBASE_PLATFORM_MAX_TOKEN_AGE_SECONDS)"
        ),
    )
    platform_socket_max_lifetime_seconds: int = Field(
        default=3600,
        description=(
            "Maximum open realtime socket lifetime for platform principals "
            "(SNACKBASE_PLATFORM_SOCKET_MAX_LIFETIME_SECONDS)"
        ),
    )

    # Audit Logging Settings
    audit_logging_enabled: bool = Field(
        default=True,
        description="Enable GxP-compliant audit logging for CREATE/UPDATE/DELETE operations",
    )

    # Reference Expansion Settings
    max_expand_depth: int = Field(
        default=3,
        description="Maximum nesting depth for ?expand= reference expansion",
    )

    # Batch Operations Settings
    batch_max_size: int = Field(
        default=100,
        description="Maximum records per batch create/update/delete (SNACKBASE_BATCH_MAX_SIZE)",
    )

    # Webhook Settings
    max_webhooks_per_account: int = Field(
        default=20,
        description="Maximum number of webhooks per account (SNACKBASE_MAX_WEBHOOKS_PER_ACCOUNT)",
    )
    webhook_timeout_seconds: int = Field(
        default=30,
        description="HTTP timeout for webhook delivery in seconds",
    )

    # Job Queue Settings
    job_retention_days: int = Field(
        default=7,
        description="Days to retain completed jobs before deletion (SNACKBASE_JOB_RETENTION_DAYS)",
    )
    job_worker_poll_interval: float = Field(
        default=1.0,
        description="Worker poll interval in seconds (SNACKBASE_JOB_WORKER_POLL_INTERVAL)",
    )
    job_execution_timeout: int = Field(
        default=300,
        description="Job execution timeout in seconds, default 5 minutes (SNACKBASE_JOB_EXECUTION_TIMEOUT)",
    )
    job_worker_enabled: bool = Field(
        default=True,
        description="Enable background job worker within FastAPI lifespan (SNACKBASE_JOB_WORKER_ENABLED)",
    )

    # Backup & Restore Settings
    restore_retain_old_data_hours: int = Field(
        default=24,
        description=(
            "Hours to keep the pre-restore data under .restore_old/ after a "
            "restore, giving an operator a window to recover manually "
            "(SNACKBASE_RESTORE_RETAIN_OLD_DATA_HOURS)"
        ),
    )

    # Scheduler Settings
    scheduler_enabled: bool = Field(
        default=True,
        description="Enable cron scheduler within FastAPI lifespan (SNACKBASE_SCHEDULER_ENABLED)",
    )
    scheduler_poll_interval: float = Field(
        default=30.0,
        description="Scheduler poll interval in seconds (SNACKBASE_SCHEDULER_POLL_INTERVAL)",
    )
    max_scheduled_hooks_per_account: int = Field(
        default=10,
        description="Maximum schedule-type hooks per account (SNACKBASE_MAX_SCHEDULED_HOOKS_PER_ACCOUNT)",
    )

    # Custom Endpoints Settings (F8.2)
    max_endpoints_per_account: int = Field(
        default=20,
        description="Maximum custom endpoints per account (SNACKBASE_MAX_ENDPOINTS_PER_ACCOUNT)",
    )
    endpoint_execution_timeout_seconds: int = Field(
        default=30,
        description="Custom endpoint execution timeout in seconds (SNACKBASE_ENDPOINT_EXECUTION_TIMEOUT_SECONDS)",
    )

    # Functions Settings (tenant-deployed Python FaaS)
    function_execution_timeout_seconds: int = Field(
        default=30,
        description="Function subprocess timeout in seconds (SNACKBASE_FUNCTION_EXECUTION_TIMEOUT_SECONDS)",
    )
    max_functions_per_account: int = Field(
        default=20,
        description="Maximum functions per account (SNACKBASE_MAX_FUNCTIONS_PER_ACCOUNT)",
    )
    max_function_source_bytes: int = Field(
        default=512_000,
        description="Max total source bytes per deploy (SNACKBASE_MAX_FUNCTION_SOURCE_BYTES)",
    )
    max_function_request_body_bytes: int = Field(
        default=1_048_576,
        description="Max invoke request body bytes (SNACKBASE_MAX_FUNCTION_REQUEST_BODY_BYTES)",
    )
    max_concurrent_function_invokes_per_account: int = Field(
        default=5,
        description="Per-account concurrent invoke cap (SNACKBASE_MAX_CONCURRENT_FUNCTION_INVOKES_PER_ACCOUNT)",
    )
    max_concurrent_function_invokes_global: int = Field(
        default=32,
        description="Global concurrent invoke cap (SNACKBASE_MAX_CONCURRENT_FUNCTION_INVOKES_GLOBAL)",
    )
    function_dependency_mode: Literal["open_pinned", "allowlist"] = Field(
        default="allowlist",
        description=(
            "Dependency pin mode: allowlist (default, fail-closed) or open_pinned, "
            "which lets a function deploy install any pinned PyPI package "
            "(SNACKBASE_FUNCTION_DEPENDENCY_MODE)"
        ),
    )
    function_sandbox_mode: Literal["auto", "required", "disabled"] = Field(
        default="auto",
        description=(
            "OS-level confinement for function invokes. 'auto' sandboxes wherever "
            "bubblewrap is available and is treated as 'required' in production; "
            "'required' refuses to invoke without it; 'disabled' runs unconfined "
            "(SNACKBASE_FUNCTION_SANDBOX_MODE)"
        ),
    )
    function_memory_limit_mb: int = Field(
        default=512,
        description="Address-space limit for a function invoke child in MB",
    )
    function_env_base_path: str = Field(
        default="./sb_data/function_envs",
        description="Base path for per-version function venvs (SNACKBASE_FUNCTION_ENV_BASE_PATH)",
    )
    function_env_disk_quota_mb: int = Field(
        default=1024,
        description="Disk quota for function envs in MB (SNACKBASE_FUNCTION_ENV_DISK_QUOTA_MB)",
    )
    max_function_versions_retained: int = Field(
        default=20,
        description="Max versions retained per function (SNACKBASE_MAX_FUNCTION_VERSIONS_RETAINED)",
    )
    function_cors_origins: CommaSepList = Field(
        default_factory=lambda: ["*"],
        description="CORS origins for function invoke (SNACKBASE_FUNCTION_CORS_ORIGINS)",
    )
    function_dependency_allowlist: CommaSepList = Field(
        default_factory=list,
        description="Allowed package names when dependency mode is allowlist",
    )
    function_stdout_max_bytes: int = Field(
        default=65_536,
        description="Max captured stdout/stderr bytes per execution",
    )
    function_nested_invoke_limit_per_minute: int = Field(
        default=30,
        description="Nested function invoke budget per root invoke per minute",
    )
    function_worker_pool_size: int = Field(
        default=4,
        description="Dedicated function worker pool size (SNACKBASE_FUNCTION_WORKER_POOL_SIZE)",
    )
    function_streaming_timeout_seconds: int = Field(
        default=120,
        description="Streaming response timeout in seconds",
    )
    function_execution_retention_days: int = Field(
        default=30,
        description="Days to retain function execution logs",
    )
    max_function_secrets_per_account: int = Field(
        default=100,
        description="Maximum function secrets per account",
    )

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

    @property
    def has_non_default_encryption_key(self) -> bool:
        """True when SNACKBASE_ENCRYPTION_KEY is not the built-in default."""
        from snackbase.infrastructure.security.encryption import DEFAULT_ENCRYPTION_KEY

        return bool(self.encryption_key != DEFAULT_ENCRYPTION_KEY)

    @model_validator(mode="after")
    def validate_production_encryption_key(self) -> Settings:
        """Reject the default encryption key in production (fail-closed)."""
        from snackbase.infrastructure.security.encryption import DEFAULT_ENCRYPTION_KEY

        if self.environment == "production" and self.encryption_key == DEFAULT_ENCRYPTION_KEY:
            raise ValueError(
                "SNACKBASE_ENCRYPTION_KEY must be set to a non-default value in production. "
                "Generate one with: openssl rand -hex 32"
            )
        return self

    @model_validator(mode="after")
    def validate_production_signing_secrets(self) -> Settings:
        """Reject the default signing secrets in production (fail-closed).

        `secret_key` signs every JWT and `token_secret` signs API keys, so a
        deployment left on the shipped placeholder is forgeable by anyone who
        has read the repository.
        """
        if self.environment != "production":
            return self

        defaulted = [
            env_var
            for env_var, value in (
                ("SNACKBASE_SECRET_KEY", self.secret_key),
                ("SNACKBASE_TOKEN_SECRET", self.token_secret),
            )
            if value == DEFAULT_SIGNING_SECRET
        ]
        if defaulted:
            raise ValueError(
                f"{' and '.join(defaulted)} must be set to a non-default value in "
                "production. Generate one with: openssl rand -hex 32"
            )
        return self

    @model_validator(mode="after")
    def validate_sqlite_workers(self) -> Settings:
        """Validate that SQLite is not used with multiple workers."""
        if self.workers > 1 and self.database_url.startswith("sqlite"):
            raise ValueError(
                "SQLite does not support multiple worker processes. "
                f"Requested {self.workers} workers, but SQLite requires workers=1. "
                "Either use --workers 1 or switch to PostgreSQL."
            )
        return self

    @model_validator(mode="after")
    def validate_single_tenant_config(self) -> Settings:
        """Validate single-tenant mode configuration."""
        if self.single_tenant_mode and not self.single_tenant_account:
            raise ValueError(
                "SNACKBASE_SINGLE_TENANT_ACCOUNT is required when SNACKBASE_SINGLE_TENANT_MODE=true"
            )
        return self

    @model_validator(mode="after")
    def validate_platform_auth_config(self) -> Settings:
        """Validate trusted-issuer (platform) authentication settings."""
        if self.platform_issuer is None:
            return self

        missing: list[str] = []
        if not self.platform_jwks_url:
            missing.append("platform_jwks_url")
        if not self.platform_audience:
            missing.append("platform_audience")
        if missing:
            raise ValueError(
                f"When platform_issuer is set, {', '.join(missing)} must also be configured"
            )

        if (
            self.environment == "production"
            and self.platform_jwks_url
            and not self.platform_jwks_url.startswith("https://")
        ):
            raise ValueError(
                "platform_jwks_url must use https:// when SNACKBASE_ENVIRONMENT=production"
            )

        return self

    @property
    def platform_auth_enabled(self) -> bool:
        """True when a trusted external issuer is configured."""
        return self.platform_issuer is not None

    @cached_property
    def trusted_proxy_matcher(self) -> TrustedProxies:
        """The parsed `trusted_proxies` entries, computed once per settings object."""
        return parse_trusted_proxies(self.trusted_proxies)

    @model_validator(mode="after")
    def validate_trusted_proxies(self) -> Settings:
        """Parse the trusted-proxy entries eagerly so a bad one fails at startup."""
        _ = self.trusted_proxy_matcher
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
