"""Backup archive manifest and key fingerprints.

Every archive carries a ``manifest.json`` at its root that makes it
self-describing: what produced it, what schema state it captured, which
secrets it was encrypted under (as fingerprints only — never the secrets
themselves), and what data it contains.

Fingerprints exist because SnackBase encrypts provider credentials at rest
with ``SNACKBASE_ENCRYPTION_KEY``. Restoring an archive taken under a
different key would otherwise produce an instance whose OAuth, SAML, SMTP,
and S3 credentials are silently undecryptable while the restore reports
success. Comparing fingerprints turns that failure into a refusal.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, fields
from importlib import metadata
from typing import Any

#: Highest manifest format version this binary can read. Version 2 added the
#: dynamic migration history to the archive (``migrations/`` members) and the
#: ``database_revisions``/``includes_migrations`` manifest fields; older
#: archives predate it and cannot be restored safely.
SUPPORTED_FORMAT_VERSION = 2

#: Lowest manifest format version this binary can restore. Archives written
#: before it carry no migration history, and restoring one would evaluate the
#: restored database's ``alembic_version`` against a script directory that
#: belongs to a different point in the instance's history.
MIN_FORMAT_VERSION = 2

#: Domain separation prefix so a fingerprint cannot be replayed against
#: another fingerprinting scheme (or used as a verifier for the secret).
_FINGERPRINT_DOMAIN = b"snackbase-backup-fingerprint-v1"

FORMAT_VERSION = "format_version"
CREATED_AT = "created_at"
SNACKBASE_VERSION = "snackbase_version"
BACKUP_TYPE = "backup_type"
DATABASE_ENGINE = "database_engine"
ALEMBIC_HEADS = "alembic_heads"
DATABASE_REVISIONS = "database_revisions"
INCLUDES_MIGRATIONS = "includes_migrations"
INCLUDES_FILES = "includes_files"
STORAGE_MODE = "storage_mode"
ENCRYPTION_KEY_FINGERPRINT = "encryption_key_fingerprint"
SECRET_KEY_FINGERPRINT = "secret_key_fingerprint"
TOKEN_SECRET_FINGERPRINT = "token_secret_fingerprint"
TABLE_ROW_COUNTS = "table_row_counts"


def fingerprint(secret: str) -> str:
    """Fingerprint a secret as 16 hex characters of a domain-separated SHA-256.

    Truncated so the value is not a verifier for the secret itself, and
    domain-separated so it cannot be replayed in another scheme.
    """
    digest = hashlib.sha256(_FINGERPRINT_DOMAIN + secret.encode("utf-8")).hexdigest()
    return digest[:16]


def fingerprints_from_settings(settings: Any) -> dict[str, str]:
    """Fingerprint the three deployment secrets relevant to an archive."""
    return {
        ENCRYPTION_KEY_FINGERPRINT: fingerprint(settings.encryption_key),
        SECRET_KEY_FINGERPRINT: fingerprint(settings.secret_key),
        TOKEN_SECRET_FINGERPRINT: fingerprint(settings.token_secret),
    }


def snackbase_version() -> str:
    """The installed SnackBase version, from package metadata."""
    try:
        return metadata.version("snackbase")
    except metadata.PackageNotFoundError:
        return "unknown"


def running_engine(database_url: str) -> str:
    """Map a database URL to the engine name recorded in manifests."""
    if database_url.startswith("sqlite"):
        return "sqlite"
    if database_url.startswith("postgres"):
        return "postgresql"
    return database_url.split("+", 1)[0].split(":", 1)[0]


def load_alembic_heads() -> list[str]:
    """Resolve all Alembic branch heads (core and dynamic) from the scripts.

    Uses the same multi-branch resolution the CLI's ``migrate upgrade``
    targets (``heads``, not ``head``), reading the script directory rather
    than the database so an archive records the schema state the binary
    would apply, not whatever the database happens to be at.

    This is a display-only field: the authoritative revision state of an
    archive lives in its ``database_revisions``, read from the snapshot's
    ``alembic_version`` table. The script-directory heads and the database
    revisions diverge whenever a migration file exists but is unapplied.
    """
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    alembic_cfg = Config("alembic.ini")
    script_directory = ScriptDirectory.from_config(alembic_cfg)
    return sorted(script_directory.get_heads())


class UnsupportedFormatVersionError(ValueError):
    """The manifest's format version is outside what this binary restores.

    Raised at parse time — before any unknown-field validation — so an
    archive from a different SnackBase generation is reported with the
    upgrade guidance rather than a confusing schema complaint.
    """

    def __init__(self, version: int) -> None:
        if version < MIN_FORMAT_VERSION:
            message = (
                f"Archive manifest format version {version} predates migration "
                f"history in archives (version {MIN_FORMAT_VERSION}). Archives "
                "this old cannot be restored safely; create a new backup with "
                "this SnackBase version."
            )
        else:
            message = (
                f"Archive manifest format version {version} is newer than the "
                f"supported version {SUPPORTED_FORMAT_VERSION}. Upgrade "
                "SnackBase to restore this archive."
            )
        super().__init__(message)
        self.version = version


@dataclass(frozen=True)
class CompatibilityIssue:
    """One reason an archive may not restore cleanly.

    ``severity`` is ``blocking`` (restore must refuse; never overridable) or
    ``warning`` (restore may proceed when explicitly forced). Returning a
    structured list rather than raising lets callers choose how to present
    the result.
    """

    type: str
    severity: str  # "blocking" | "warning"
    message: str


@dataclass
class BackupManifest:
    """Self-describing metadata stored as ``manifest.json`` at the archive root."""

    format_version: int
    created_at: str  # ISO-8601 UTC
    snackbase_version: str
    backup_type: str  # "sqlite_physical" | "logical"
    database_engine: str  # "sqlite" | "postgresql"
    alembic_heads: list[str]
    includes_files: bool
    storage_mode: str  # "local" | "s3"
    encryption_key_fingerprint: str
    secret_key_fingerprint: str
    token_secret_fingerprint: str
    table_row_counts: dict[str, int] = field(default_factory=dict)
    #: Ephemeral tables deliberately absent from logical exports (F5.1).
    excluded_tables: list[str] = field(default_factory=list)
    #: The snapshot's actual ``alembic_version`` rows — the authoritative
    #: revision state of the archived database, as opposed to
    #: ``alembic_heads`` which describes the producing binary's scripts.
    database_revisions: list[str] = field(default_factory=list)
    #: Whether the archive carries the ``migrations/`` member: the dynamic
    #: collection-migration scripts that give ``database_revisions`` meaning.
    includes_migrations: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the exact documented field set, in field order."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialize to pretty-printed JSON for the archive."""
        return json.dumps(self.to_dict(), indent=2) + "\n"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BackupManifest:
        """Parse and validate a manifest dictionary.

        The format version is checked before anything else: an archive from
        a different SnackBase generation must be refused with upgrade
        guidance even when its field set is unknown to this binary.

        Raises:
            UnsupportedFormatVersionError: When the format version is outside
                the supported range.
            ValueError: When a field is missing, of the wrong type, or when
                the dict carries fields outside the documented schema.
        """
        known = {f.name for f in fields(cls)}
        version = data.get(FORMAT_VERSION)
        if isinstance(version, bool) or not isinstance(version, int):
            raise ValueError(f"Manifest field {FORMAT_VERSION!r} must be an integer")
        if version < MIN_FORMAT_VERSION or version > SUPPORTED_FORMAT_VERSION:
            raise UnsupportedFormatVersionError(version)
        unknown = sorted(set(data) - known)
        if unknown:
            raise ValueError(f"Unknown manifest fields: {', '.join(unknown)}")
        optional = {"excluded_tables", DATABASE_REVISIONS, INCLUDES_MIGRATIONS}
        missing = sorted((known - set(data)) - optional)
        if missing:
            raise ValueError(f"Missing manifest fields: {', '.join(missing)}")

        str_fields = (
            CREATED_AT,
            SNACKBASE_VERSION,
            BACKUP_TYPE,
            DATABASE_ENGINE,
            STORAGE_MODE,
            ENCRYPTION_KEY_FINGERPRINT,
            SECRET_KEY_FINGERPRINT,
            TOKEN_SECRET_FINGERPRINT,
        )
        for name in str_fields:
            if not isinstance(data[name], str):
                raise ValueError(f"Manifest field {name!r} must be a string")
        if not isinstance(data[INCLUDES_FILES], bool):
            raise ValueError(f"Manifest field {INCLUDES_FILES!r} must be a boolean")
        heads = data[ALEMBIC_HEADS]
        if not (isinstance(heads, list) and all(isinstance(item, str) for item in heads)):
            raise ValueError(f"Manifest field {ALEMBIC_HEADS!r} must be a list of strings")
        counts = data.get(TABLE_ROW_COUNTS, {})
        if not (
            isinstance(counts, dict)
            and all(isinstance(k, str) and isinstance(v, int) for k, v in counts.items())
        ):
            raise ValueError(
                f"Manifest field {TABLE_ROW_COUNTS!r} must be an object of integers"
            )
        excluded = data.get("excluded_tables", [])
        if not (
            isinstance(excluded, list)
            and all(isinstance(item, str) for item in excluded)
        ):
            raise ValueError(
                "Manifest field 'excluded_tables' must be a list of strings"
            )
        revisions = data.get(DATABASE_REVISIONS, [])
        if not (
            isinstance(revisions, list)
            and all(isinstance(item, str) for item in revisions)
        ):
            raise ValueError(
                f"Manifest field {DATABASE_REVISIONS!r} must be a list of strings"
            )
        includes_migrations = data.get(INCLUDES_MIGRATIONS, False)
        if not isinstance(includes_migrations, bool):
            raise ValueError(
                f"Manifest field {INCLUDES_MIGRATIONS!r} must be a boolean"
            )

        return cls(
            format_version=version,
            created_at=data[CREATED_AT],
            snackbase_version=data[SNACKBASE_VERSION],
            backup_type=data[BACKUP_TYPE],
            database_engine=data[DATABASE_ENGINE],
            alembic_heads=heads,
            includes_files=data[INCLUDES_FILES],
            storage_mode=data[STORAGE_MODE],
            encryption_key_fingerprint=data[ENCRYPTION_KEY_FINGERPRINT],
            secret_key_fingerprint=data[SECRET_KEY_FINGERPRINT],
            token_secret_fingerprint=data[TOKEN_SECRET_FINGERPRINT],
            table_row_counts=counts,
            excluded_tables=excluded,
            database_revisions=revisions,
            includes_migrations=includes_migrations,
        )

    @classmethod
    def from_json(cls, payload: str) -> BackupManifest:
        """Parse a manifest from JSON text.

        Raises:
            ValueError: When the payload is not JSON or fails validation.
        """
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError(f"manifest.json is not valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("manifest.json must be a JSON object")
        return cls.from_dict(data)

    def verify_compatibility(
        self,
        settings: Any,
        *,
        current_storage_mode: str | None = None,
    ) -> list[CompatibilityIssue]:
        """Check this archive against the running deployment's settings.

        Returns every incompatibility found; an empty list means the archive
        can restore. Blocking issues are refusals that ``force`` cannot
        override; warnings invalidate sessions but do not corrupt data.

        ``current_storage_mode``, when provided, enables the
        ``storage_mode_mismatch`` warning: restoring an S3-mode archive (no
        ``files/`` members) onto a local-storage instance would leave the
        instance's local files tree in place while the restored database
        references objects in S3, and vice versa. The caller supplies it
        when a database session is available to read the storage
        configuration; the boot-time executor has no session and omits it.
        """
        issues: list[CompatibilityIssue] = []

        if self.format_version > SUPPORTED_FORMAT_VERSION:
            issues.append(
                CompatibilityIssue(
                    type="format_version_unsupported",
                    severity="blocking",
                    message=(
                        f"Archive manifest format version {self.format_version} is newer "
                        f"than the supported version {SUPPORTED_FORMAT_VERSION}. "
                        "Upgrade SnackBase to restore this archive."
                    ),
                )
            )
        elif self.format_version < MIN_FORMAT_VERSION:
            issues.append(
                CompatibilityIssue(
                    type="format_version_unsupported",
                    severity="blocking",
                    message=(
                        f"Archive manifest format version {self.format_version} predates "
                        f"migration history in archives (version {MIN_FORMAT_VERSION}). "
                        "Create a new backup with this SnackBase version."
                    ),
                )
            )

        engine = running_engine(settings.database_url)
        if self.backup_type == "logical":
            issues.append(
                CompatibilityIssue(
                    type="logical_archive_not_restorable",
                    severity="blocking",
                    message=(
                        "Logical archives are portable exports, not restore "
                        "artifacts in this release. On PostgreSQL, configure "
                        "disaster recovery on the database itself (managed "
                        "snapshots or operator-run pg_dump)."
                    ),
                )
            )
        if self.database_engine != engine:
            issues.append(
                CompatibilityIssue(
                    type="engine_mismatch",
                    severity="blocking",
                    message=(
                        f"Archive was taken on {self.database_engine} but this instance "
                        f"runs {engine}. Cross-engine restore is not supported."
                    ),
                )
            )
        if current_storage_mode is not None and self.storage_mode != current_storage_mode:
            if self.storage_mode == "s3":
                detail = (
                    "The restored database references files the archive "
                    "does not contain."
                )
            else:
                detail = (
                    "The archive contains files locally, while newer uploads "
                    "live in S3."
                )
            issues.append(
                CompatibilityIssue(
                    type="storage_mode_mismatch",
                    severity="warning",
                    message=(
                        f"Archive was taken with {self.storage_mode} file storage but "
                        f"this instance currently uses {current_storage_mode}. {detail}"
                    ),
                )
            )

        current = fingerprints_from_settings(settings)
        if self.encryption_key_fingerprint != current[ENCRYPTION_KEY_FINGERPRINT]:
            issues.append(
                CompatibilityIssue(
                    type="encryption_key_mismatch",
                    severity="blocking",
                    message=(
                        "Archive was taken with a different SNACKBASE_ENCRYPTION_KEY. "
                        "Restoring it would leave every stored provider credential "
                        "undecryptable."
                    ),
                )
            )
        if self.secret_key_fingerprint != current[SECRET_KEY_FINGERPRINT]:
            issues.append(
                CompatibilityIssue(
                    type="secret_key_mismatch",
                    severity="warning",
                    message=(
                        "Archive was taken with a different SNACKBASE_SECRET_KEY. "
                        "Existing sessions and signed values will be invalidated."
                    ),
                )
            )
        if self.token_secret_fingerprint != current[TOKEN_SECRET_FINGERPRINT]:
            issues.append(
                CompatibilityIssue(
                    type="token_secret_mismatch",
                    severity="warning",
                    message=(
                        "Archive was taken with a different SNACKBASE_TOKEN_SECRET. "
                        "Existing tokens and API keys will be invalidated."
                    ),
                )
            )

        return issues
