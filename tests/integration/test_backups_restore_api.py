"""Integration tests for the restore request endpoint (F3.1) and status (F3.3)."""

import io
import json
import zipfile
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.config import get_settings
from snackbase.infrastructure.backup.archive import MANIFEST_MEMBER
from snackbase.infrastructure.backup.lock import LOCK_FILENAME
from snackbase.infrastructure.backup.manifest import (
    BackupManifest,
    fingerprint,
)
from snackbase.infrastructure.persistence.models.configuration import ConfigurationModel

SNAP_DB_BYTES = b"SQLite format 3\x00" + b"\0" * 32


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _manifest(**overrides: object) -> BackupManifest:
    settings = get_settings()
    data = dict(
        format_version=1,
        created_at="2026-09-02T00:00:00+00:00",
        snackbase_version="0.11.0",
        backup_type="sqlite_physical",
        database_engine="sqlite",
        alembic_heads=["abc"],
        includes_files=False,
        storage_mode="local",
        encryption_key_fingerprint=fingerprint(settings.encryption_key),
        secret_key_fingerprint=fingerprint(settings.secret_key),
        token_secret_fingerprint=fingerprint(settings.token_secret),
        table_row_counts={},
    )
    data.update(overrides)
    return BackupManifest(**data)  # type: ignore[arg-type]


def _archive_bytes(manifest: BackupManifest, *, with_data_db: bool = True) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(MANIFEST_MEMBER, manifest.to_json())
        if with_data_db:
            archive.writestr("data.db", SNAP_DB_BYTES)
    return buffer.getvalue()


def _place_archive(
    backup_dir: Path,
    name: str,
    payload: bytes,
) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    (backup_dir / name).write_bytes(payload)


async def _configure_local_backup(db_session: AsyncSession, local_path: Path) -> None:
    import uuid

    db_session.add(
        ConfigurationModel(
            id=str(uuid.uuid4()),
            account_id="00000000-0000-0000-0000-000000000000",
            category="backup_settings",
            provider_name="backup",
            display_name="Backup Settings",
            config={"destination": "local", "local_path": str(local_path)},
            enabled=True,
            is_builtin=True,
            is_system=True,
        )
    )
    await db_session.commit()


@pytest.fixture
async def restore_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    db_session: AsyncSession,
    local_backup_dir: Path,
) -> Path:
    """Point settings at a scratch data dir and silence the restart."""
    import importlib

    router_module = importlib.import_module(
        "snackbase.infrastructure.api.routes.backups_router"
    )
    data_directory = tmp_path / "sb_data"
    data_directory.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        get_settings(),
        "database_url",
        f"sqlite+aiosqlite:///{data_directory / 'snackbase.db'}",
    )
    restarts: list[dict] = []
    monkeypatch.setattr(
        router_module,
        "schedule_restart",
        lambda *args, **kwargs: restarts.append({"args": args, "kwargs": kwargs}),
    )
    monkeypatch.setattr(router_module, "_restarts_recorded", restarts, raising=False)
    await _configure_local_backup(db_session, local_backup_dir)
    return local_backup_dir


@pytest.fixture
def local_backup_dir(tmp_path: Path) -> Path:
    return tmp_path / "backups"


@pytest.mark.asyncio
async def test_valid_restore_returns_202_and_writes_marker(
    client,
    superadmin_token: str,
    restore_env: Path,
    tmp_path: Path,
) -> None:
    _place_archive(
        restore_env, "good.zip", _archive_bytes(_manifest())
    )

    response = await client.post(
        "/api/v1/backups/good.zip/restore",
        headers=_auth(superadmin_token),
        json={},
    )

    assert response.status_code == 202, response.text
    body = response.json()
    assert body["archive_name"] == "good.zip"
    marker = tmp_path / "sb_data" / ".restore-pending.json"
    assert marker.exists()
    stored = json.loads(marker.read_text())
    assert stored["archive_name"] == "good.zip"
    assert stored["requested_by"] == "superadmin"
    assert "manifest_fingerprints" in stored
    # The UI is told the instance will restart.
    assert "requested_at" in stored


@pytest.mark.asyncio
async def test_restore_absent_archive_returns_404_and_writes_no_marker(
    client, superadmin_token: str, restore_env: Path, tmp_path: Path
) -> None:
    response = await client.post(
        "/api/v1/backups/absent.zip/restore",
        headers=_auth(superadmin_token),
        json={},
    )

    assert response.status_code == 404
    assert not (tmp_path / "sb_data" / ".restore-pending.json").exists()


@pytest.mark.asyncio
async def test_restore_zip_without_data_db_returns_400(
    client, superadmin_token: str, restore_env: Path, tmp_path: Path
) -> None:
    _place_archive(
        restore_env, "nodb.zip", _archive_bytes(_manifest(), with_data_db=False)
    )

    response = await client.post(
        "/api/v1/backups/nodb.zip/restore",
        headers=_auth(superadmin_token),
        json={},
    )

    assert response.status_code == 400
    assert "data.db" in response.json()["detail"]
    assert not (tmp_path / "sb_data" / ".restore-pending.json").exists()


@pytest.mark.asyncio
async def test_restore_with_blocking_issue_refused_even_with_force(
    client, superadmin_token: str, restore_env: Path, tmp_path: Path
) -> None:
    _place_archive(
        restore_env,
        "foreign.zip",
        _archive_bytes(
            _manifest(encryption_key_fingerprint=fingerprint("another-key"))
        ),
    )

    for payload in ({}, {"force": True}):
        response = await client.post(
            "/api/v1/backups/foreign.zip/restore",
            headers=_auth(superadmin_token),
            json=payload,
        )
        assert response.status_code == 400, payload
        detail = response.json()["detail"]
        issues = detail["issues"] if isinstance(detail, dict) else []
        assert any(i["type"] == "encryption_key_mismatch" for i in issues)
    assert not (tmp_path / "sb_data" / ".restore-pending.json").exists()


@pytest.mark.asyncio
async def test_restore_with_warning_requires_force(
    client, superadmin_token: str, restore_env: Path, tmp_path: Path
) -> None:
    _place_archive(
        restore_env,
        "warned.zip",
        _archive_bytes(_manifest(secret_key_fingerprint=fingerprint("other-key"))),
    )

    without_force = await client.post(
        "/api/v1/backups/warned.zip/restore",
        headers=_auth(superadmin_token),
        json={},
    )
    assert without_force.status_code == 400
    assert "force" in json.dumps(without_force.json()["detail"])

    with_force = await client.post(
        "/api/v1/backups/warned.zip/restore",
        headers=_auth(superadmin_token),
        json={"force": True},
    )
    assert with_force.status_code == 202
    assert (tmp_path / "sb_data" / ".restore-pending.json").exists()


@pytest.mark.asyncio
async def test_restore_forbidden_for_non_superadmin(
    client,
    regular_user_token: str,
    restore_env: Path,
    tmp_path: Path,
) -> None:
    _place_archive(restore_env, "good.zip", _archive_bytes(_manifest()))

    response = await client.post(
        "/api/v1/backups/good.zip/restore",
        headers=_auth(regular_user_token),
        json={},
    )

    assert response.status_code == 403
    assert not (tmp_path / "sb_data" / ".restore-pending.json").exists()


@pytest.mark.asyncio
async def test_restore_while_operation_in_flight_returns_409(
    client, superadmin_token: str, restore_env: Path, tmp_path: Path
) -> None:
    import os

    _place_archive(restore_env, "good.zip", _archive_bytes(_manifest()))
    (restore_env / LOCK_FILENAME).write_text(
        json.dumps(
            {
                "operation": "backup",
                "name": "running.zip",
                "pid": os.getpid(),
                "started_at": "2026-09-02T00:00:00",
            }
        )
    )

    response = await client.post(
        "/api/v1/backups/good.zip/restore",
        headers=_auth(superadmin_token),
        json={},
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["active"]["name"] == "running.zip"
    assert not (tmp_path / "sb_data" / ".restore-pending.json").exists()


@pytest.mark.asyncio
async def test_restore_request_audit_and_status_endpoint(
    client,
    superadmin_token: str,
    restore_env: Path,
    tmp_path: Path,
    db_session: AsyncSession,
) -> None:
    """A successful request writes the restore-status and audit plumbing."""
    from snackbase.infrastructure.backup.restore import (
        RestoreResult,
        mark_audit_pending,
        record_last_restore,
    )

    _place_archive(restore_env, "good.zip", _archive_bytes(_manifest()))
    response = await client.post(
        "/api/v1/backups/good.zip/restore",
        headers=_auth(superadmin_token),
        json={},
    )
    assert response.status_code == 202

    # Simulate the boot that completes the restore, then check the status
    # endpoint reports the outcome.
    record_last_restore(
        get_settings(),
        RestoreResult(
            archive_name="good.zip",
            status="completed",
            completed_at="2026-09-02T01:00:00+00:00",
        ),
    )
    mark_audit_pending(get_settings(), "backup.restore.completed", "good.zip")

    status = await client.get(
        "/api/v1/backups/restore-status", headers=_auth(superadmin_token)
    )
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "completed"
    assert body["archive_name"] == "good.zip"

    forbidden = await client.get(
        "/api/v1/backups/restore-status", headers=_auth("x")
    )
    assert forbidden.status_code in (401, 403)


@pytest.mark.asyncio
async def test_restore_status_404_when_never_restored(
    client, superadmin_token: str, restore_env: Path
) -> None:
    response = await client.get(
        "/api/v1/backups/restore-status", headers=_auth(superadmin_token)
    )
    assert response.status_code == 404
