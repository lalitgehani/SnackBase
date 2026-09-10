"""Unit tests for the backup archive manifest (F1.4)."""

import pytest

from snackbase.infrastructure.backup.manifest import (
    SUPPORTED_FORMAT_VERSION,
    BackupManifest,
    CompatibilityIssue,
    fingerprint,
    fingerprints_from_settings,
    load_alembic_heads,
    running_engine,
    snackbase_version,
)


def _manifest(**overrides: object) -> BackupManifest:
    base = dict(
        format_version=2,
        created_at="2026-09-02T00:00:00+00:00",
        snackbase_version="0.11.0",
        backup_type="sqlite_physical",
        database_engine="sqlite",
        alembic_heads=["abc123"],
        database_revisions=["abc123"],
        includes_migrations=True,
        includes_files=True,
        storage_mode="local",
        encryption_key_fingerprint=fingerprint("enc-key"),
        secret_key_fingerprint=fingerprint("sec-key"),
        token_secret_fingerprint=fingerprint("tok-key"),
        table_row_counts={"users": 2},
    )
    base.update(overrides)
    return BackupManifest(**base)  # type: ignore[arg-type]


class _Settings:
    encryption_key = "enc-key"
    secret_key = "sec-key"
    token_secret = "tok-key"
    database_url = "sqlite+aiosqlite:///./sb_data/snackbase.db"


class TestFingerprint:
    def test_returns_16_lowercase_hex_characters(self) -> None:
        value = fingerprint("test-key")

        assert len(value) == 16
        assert value == value.lower()
        int(value, 16)  # raises if not hex

    def test_deterministic_across_calls(self) -> None:
        assert fingerprint("test-key") == fingerprint("test-key")

    def test_different_inputs_differ(self) -> None:
        assert fingerprint("a") != fingerprint("b")

    def test_domain_separated_from_raw_sha256(self) -> None:
        import hashlib

        raw = hashlib.sha256(b"test-key").hexdigest()[:16]
        assert fingerprint("test-key") != raw


class TestManifestSerialization:
    def test_round_trip_produces_equal_object(self) -> None:
        manifest = _manifest()

        parsed = BackupManifest.from_json(manifest.to_json())

        assert parsed == manifest

    def test_unknown_field_rejected(self) -> None:
        data = _manifest().to_dict()
        data["surprise"] = "nope"

        try:
            BackupManifest.from_dict(data)
        except ValueError as exc:
            assert "surprise" in str(exc)
        else:
            raise AssertionError("expected ValueError for unknown field")

    def test_missing_field_rejected(self) -> None:
        data = _manifest().to_dict()
        del data["alembic_heads"]

        try:
            BackupManifest.from_dict(data)
        except ValueError as exc:
            assert "alembic_heads" in str(exc)
        else:
            raise AssertionError("expected ValueError for missing field")

    def test_no_secrets_in_serialized_manifest(self) -> None:
        manifest = _manifest(
            encryption_key_fingerprint=fingerprint("super-secret-enc"),
        )

        payload = manifest.to_json()

        assert "super-secret-enc" not in payload
        assert "sec-key" not in payload
        assert "tok-key" not in payload


class TestVerifyCompatibility:
    def test_matching_settings_return_no_issues(self) -> None:
        manifest = _manifest()

        assert manifest.verify_compatibility(_Settings) == []

    def test_encryption_key_mismatch_is_blocking(self) -> None:
        manifest = _manifest(encryption_key_fingerprint=fingerprint("other"))

        issues = manifest.verify_compatibility(_Settings)

        blocking = [i for i in issues if i.severity == "blocking"]
        assert len(blocking) == 1
        assert blocking[0].type == "encryption_key_mismatch"

    def test_secret_key_mismatch_is_warning(self) -> None:
        manifest = _manifest(secret_key_fingerprint=fingerprint("other"))

        issues = manifest.verify_compatibility(_Settings)

        assert len(issues) == 1
        assert issues[0].type == "secret_key_mismatch"
        assert issues[0].severity == "warning"

    def test_token_secret_mismatch_is_warning(self) -> None:
        manifest = _manifest(token_secret_fingerprint=fingerprint("other"))

        issues = manifest.verify_compatibility(_Settings)

        assert len(issues) == 1
        assert issues[0].type == "token_secret_mismatch"
        assert issues[0].severity == "warning"

    def test_unsupported_format_version_is_blocking(self) -> None:
        manifest = _manifest(format_version=SUPPORTED_FORMAT_VERSION + 1)

        issues = manifest.verify_compatibility(_Settings)

        types = {issue.type for issue in issues}
        assert types == {"format_version_unsupported"}
        assert all(issue.severity == "blocking" for issue in issues)

    def test_engine_mismatch_is_blocking(self) -> None:
        manifest = _manifest(database_engine="postgresql")

        issues = manifest.verify_compatibility(_Settings)

        assert [issue.type for issue in issues] == ["engine_mismatch"]
        assert issues[0].severity == "blocking"


class TestHelpers:
    def test_fingerprints_from_settings_covers_three_secrets(self) -> None:
        prints = fingerprints_from_settings(_Settings)

        assert set(prints) == {
            "encryption_key_fingerprint",
            "secret_key_fingerprint",
            "token_secret_fingerprint",
        }
        assert prints["encryption_key_fingerprint"] == fingerprint("enc-key")

    def test_running_engine_maps_urls(self) -> None:
        assert running_engine("sqlite+aiosqlite:///./sb.db") == "sqlite"
        assert running_engine("postgresql+asyncpg://u:p@h/db") == "postgresql"
        assert running_engine("mysql+aiomysql://u:p@h/db") == "mysql"

    def test_snackbase_version_is_non_empty(self) -> None:
        assert snackbase_version()

    def test_snackbase_version_falls_back_when_package_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from importlib import metadata

        def raise_missing(name: str) -> str:
            raise metadata.PackageNotFoundError(name)

        monkeypatch.setattr(metadata, "version", raise_missing)
        assert snackbase_version() == "unknown"

    def test_load_alembic_heads_returns_heads(self) -> None:
        heads = load_alembic_heads()

        assert heads
        assert all(isinstance(head, str) for head in heads)

    def test_compatibility_issue_is_structural(self) -> None:
        issue = CompatibilityIssue(type="t", severity="warning", message="m")

        assert (issue.type, issue.severity, issue.message) == ("t", "warning", "m")


class TestManifestValidation:
    def test_invalid_json_rejected(self) -> None:
        with pytest.raises(ValueError, match="valid JSON"):
            BackupManifest.from_json("{not json")

    def test_non_object_json_rejected(self) -> None:
        with pytest.raises(ValueError, match="object"):
            BackupManifest.from_json("[1, 2]")

    def test_non_string_created_at_rejected(self) -> None:
        data = _manifest().to_dict()
        data["created_at"] = 12345

        with pytest.raises(ValueError, match="created_at"):
            BackupManifest.from_dict(data)

    def test_non_int_format_version_rejected(self) -> None:
        data = _manifest().to_dict()
        data["format_version"] = "1"

        with pytest.raises(ValueError, match="format_version"):
            BackupManifest.from_dict(data)

    def test_bool_format_version_rejected(self) -> None:
        data = _manifest().to_dict()
        data["format_version"] = True

        with pytest.raises(ValueError, match="format_version"):
            BackupManifest.from_dict(data)

    def test_non_bool_includes_files_rejected(self) -> None:
        data = _manifest().to_dict()
        data["includes_files"] = "yes"

        with pytest.raises(ValueError, match="includes_files"):
            BackupManifest.from_dict(data)

    def test_non_string_list_alembic_heads_rejected(self) -> None:
        data = _manifest().to_dict()
        data["alembic_heads"] = ["abc", 42]

        with pytest.raises(ValueError, match="alembic_heads"):
            BackupManifest.from_dict(data)

    def test_non_int_row_counts_rejected(self) -> None:
        data = _manifest().to_dict()
        data["table_row_counts"] = {"users": "many"}

        with pytest.raises(ValueError, match="table_row_counts"):
            BackupManifest.from_dict(data)
