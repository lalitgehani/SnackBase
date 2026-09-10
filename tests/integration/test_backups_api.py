"""Integration tests for the backup management API (F2.3, F2.4)."""

import asyncio
import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.backup.archive import MANIFEST_MEMBER
from snackbase.infrastructure.backup.manifest import BackupManifest
from snackbase.infrastructure.persistence.models.configuration import ConfigurationModel

ADMIN = "superadmin"
USER = "regular"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _configure_local_backup(
    db_session: AsyncSession, local_path: Path
) -> None:
    """Point backup_settings at a scratch directory for this test."""
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


def _valid_archive_bytes(name: str = "uploaded.zip") -> bytes:
    manifest = BackupManifest(
        format_version=2,
        created_at="2026-09-02T00:00:00+00:00",
        snackbase_version="0.11.0",
        backup_type="sqlite_physical",
        database_engine="sqlite",
        alembic_heads=["abc"],
        includes_files=True,
        database_revisions=["abc123"],
        includes_migrations=True,
        storage_mode="local",
        encryption_key_fingerprint="e",
        secret_key_fingerprint="s",
        token_secret_fingerprint="t",
        table_row_counts={},
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(MANIFEST_MEMBER, manifest.to_json())
        archive.writestr("data.db", b"sqlite-bytes")
    del name
    return buffer.getvalue()


async def _wait_for_archive(client, token: str, name: str) -> dict:
    headers = _auth(token)
    for _ in range(100):
        response = await client.get("/api/v1/backups", headers=headers)
        assert response.status_code == 200
        body = response.json()
        for entry in body["backups"]:
            if entry["name"] == name:
                return entry
        await asyncio.sleep(0.05)
    raise AssertionError(f"Archive {name} never appeared in the list")


@pytest.fixture
def local_backup_dir(tmp_path: Path) -> Path:
    return tmp_path / "backups"


@pytest.mark.asyncio
async def test_create_list_delete_round_trip(
    client, superadmin_token: str, db_session: AsyncSession, local_backup_dir: Path
) -> None:
    await _configure_local_backup(db_session, local_backup_dir)
    headers = _auth(superadmin_token)

    create = await client.post(
        "/api/v1/backups", headers=headers, json={"name": "my_backup.zip"}
    )
    assert create.status_code == 202, create.text
    assert create.json()["name"] == "my_backup.zip"

    entry = await _wait_for_archive(client, superadmin_token, "my_backup.zip")
    assert entry["size"] > 0
    assert entry["is_automatic"] is False
    assert "modified" in entry

    delete = await client.delete("/api/v1/backups/my_backup.zip", headers=headers)
    assert delete.status_code == 204
    listing = await client.get("/api/v1/backups", headers=headers)
    assert all(b["name"] != "my_backup.zip" for b in listing.json()["backups"])


@pytest.mark.asyncio
async def test_create_without_name_autogenerates(
    client, superadmin_token: str, db_session: AsyncSession, local_backup_dir: Path
) -> None:
    import re

    await _configure_local_backup(db_session, local_backup_dir)
    headers = _auth(superadmin_token)

    create = await client.post("/api/v1/backups", headers=headers)
    assert create.status_code == 202
    name = create.json()["name"]
    assert re.fullmatch(r"snackbase_backup_\d{14}\.zip", name)
    await _wait_for_archive(client, superadmin_token, name)


@pytest.mark.asyncio
async def test_create_rejects_invalid_names(
    client, superadmin_token: str, db_session: AsyncSession, local_backup_dir: Path
) -> None:
    await _configure_local_backup(db_session, local_backup_dir)
    headers = _auth(superadmin_token)

    for bad_name in ("My Backup.zip", "@auto_x.zip", "../x.zip", "a/b.zip", "x"):
        response = await client.post(
            "/api/v1/backups", headers=headers, json={"name": bad_name}
        )
        assert response.status_code == 400, bad_name


@pytest.mark.asyncio
async def test_create_duplicate_name_conflicts(
    client, superadmin_token: str, db_session: AsyncSession, local_backup_dir: Path
) -> None:
    await _configure_local_backup(db_session, local_backup_dir)
    headers = _auth(superadmin_token)

    first = await client.post(
        "/api/v1/backups", headers=headers, json={"name": "dup.zip"}
    )
    assert first.status_code == 202
    await _wait_for_archive(client, superadmin_token, "dup.zip")

    second = await client.post(
        "/api/v1/backups", headers=headers, json={"name": "dup.zip"}
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_endpoints_require_superadmin(
    client, regular_user_token: str, db_session: AsyncSession, local_backup_dir: Path
) -> None:
    await _configure_local_backup(db_session, local_backup_dir)
    headers = _auth(regular_user_token)

    assert (
        await client.post("/api/v1/backups", headers=headers)
    ).status_code == 403
    assert (await client.get("/api/v1/backups", headers=headers)).status_code == 403
    assert (
        await client.delete("/api/v1/backups/x.zip", headers=headers)
    ).status_code == 403
    download = await client.get(
        "/api/v1/backups/x.zip/download", headers=headers
    )
    assert download.status_code == 403
    upload = await client.post(
        "/api/v1/backups/upload", headers=headers, files={"file": ("x.zip", b"")}
    )
    assert upload.status_code == 403


@pytest.mark.asyncio
async def test_delete_absent_archive_not_found(
    client, superadmin_token: str, db_session: AsyncSession, local_backup_dir: Path
) -> None:
    await _configure_local_backup(db_session, local_backup_dir)

    response = await client.delete(
        "/api/v1/backups/absent.zip", headers=_auth(superadmin_token)
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_download_round_trips_identical_bytes(
    client, superadmin_token: str, db_session: AsyncSession, local_backup_dir: Path
) -> None:
    await _configure_local_backup(db_session, local_backup_dir)
    headers = _auth(superadmin_token)

    create = await client.post(
        "/api/v1/backups", headers=headers, json={"name": "dl.zip"}
    )
    assert create.status_code == 202
    await _wait_for_archive(client, superadmin_token, "dl.zip")

    download = await client.get("/api/v1/backups/dl.zip/download", headers=headers)
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("application/zip")
    assert 'filename="dl.zip"' in download.headers["content-disposition"]

    stored = (local_backup_dir / "dl.zip").read_bytes()
    assert hashlib.sha256(download.content).hexdigest() == hashlib.sha256(
        stored
    ).hexdigest()

    absent = await client.get(
        "/api/v1/backups/absent.zip/download", headers=headers
    )
    assert absent.status_code == 404


@pytest.mark.asyncio
async def test_upload_valid_archive_appears_in_list(
    client, superadmin_token: str, db_session: AsyncSession, local_backup_dir: Path
) -> None:
    await _configure_local_backup(db_session, local_backup_dir)
    headers = _auth(superadmin_token)
    payload = _valid_archive_bytes()

    response = await client.post(
        "/api/v1/backups/upload",
        headers=headers,
        files={"file": ("uploaded.zip", payload, "application/zip")},
    )
    assert response.status_code == 201, response.text

    listing = await client.get("/api/v1/backups", headers=headers)
    assert any(
        b["name"] == "uploaded.zip" for b in listing.json()["backups"]
    )
    assert (local_backup_dir / "uploaded.zip").read_bytes() == payload


@pytest.mark.asyncio
async def test_upload_rejects_non_zip(
    client, superadmin_token: str, db_session: AsyncSession, local_backup_dir: Path
) -> None:
    await _configure_local_backup(db_session, local_backup_dir)

    response = await client.post(
        "/api/v1/backups/upload",
        headers=_auth(superadmin_token),
        files={"file": ("notes.zip", b"this is not a zip")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_rejects_zip_without_manifest(
    client, superadmin_token: str, db_session: AsyncSession, local_backup_dir: Path
) -> None:
    await _configure_local_backup(db_session, local_backup_dir)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("data.db", b"sqlite-bytes")

    response = await client.post(
        "/api/v1/backups/upload",
        headers=_auth(superadmin_token),
        files={"file": ("nomanifest.zip", buffer.getvalue(), "application/zip")},
    )
    assert response.status_code == 400
    assert "manifest" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_rejects_invalid_manifest(
    client, superadmin_token: str, db_session: AsyncSession, local_backup_dir: Path
) -> None:
    await _configure_local_backup(db_session, local_backup_dir)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(MANIFEST_MEMBER, json.dumps({"unexpected": "shape"}))

    response = await client.post(
        "/api/v1/backups/upload",
        headers=_auth(superadmin_token),
        files={"file": ("badmanifest.zip", buffer.getvalue(), "application/zip")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_duplicate_name_conflicts(
    client, superadmin_token: str, db_session: AsyncSession, local_backup_dir: Path
) -> None:
    await _configure_local_backup(db_session, local_backup_dir)
    headers = _auth(superadmin_token)
    payload = _valid_archive_bytes()

    first = await client.post(
        "/api/v1/backups/upload",
        headers=headers,
        files={"file": ("uploaded.zip", payload, "application/zip")},
    )
    assert first.status_code == 201
    second = await client.post(
        "/api/v1/backups/upload",
        headers=headers,
        files={"file": ("uploaded.zip", payload, "application/zip")},
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_upload_exceeding_max_file_size_succeeds(
    client, superadmin_token: str, db_session: AsyncSession, local_backup_dir: Path
) -> None:
    """A 30 MB archive uploads fine while settings.max_file_size is 10 MB."""
    await _configure_local_backup(db_session, local_backup_dir)
    headers = _auth(superadmin_token)

    manifest = BackupManifest(
        format_version=2,
        created_at="2026-09-02T00:00:00+00:00",
        snackbase_version="0.11.0",
        backup_type="sqlite_physical",
        database_engine="sqlite",
        alembic_heads=[],
        includes_files=False,
        database_revisions=["abc123"],
        includes_migrations=True,
        storage_mode="local",
        encryption_key_fingerprint="e",
        secret_key_fingerprint="s",
        token_secret_fingerprint="t",
        table_row_counts={},
    )
    big_buffer = io.BytesIO()
    with zipfile.ZipFile(big_buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr(MANIFEST_MEMBER, manifest.to_json())
        archive.writestr("data.db", b"z" * (30 * 1024 * 1024))

    response = await client.post(
        "/api/v1/backups/upload",
        headers=headers,
        files={"file": ("big.zip", big_buffer.getvalue(), "application/zip")},
    )
    assert response.status_code == 201, response.text
    assert (local_backup_dir / "big.zip").exists()


@pytest.mark.asyncio
async def test_create_while_operation_in_flight_conflicts(
    client, superadmin_token: str, db_session: AsyncSession, local_backup_dir: Path
) -> None:
    """A held lock makes a create answer 409 naming the in-flight operation."""
    import json as json_module
    import os

    from snackbase.infrastructure.backup.lock import LOCK_FILENAME

    await _configure_local_backup(db_session, local_backup_dir)
    headers = _auth(superadmin_token)
    local_backup_dir.mkdir(parents=True, exist_ok=True)
    (local_backup_dir / LOCK_FILENAME).write_text(
        json_module.dumps(
            {
                "operation": "backup",
                "name": "running.zip",
                "pid": os.getpid(),
                "started_at": "2026-09-02T00:00:00",
            }
        )
    )

    response = await client.post(
        "/api/v1/backups", headers=headers, json={"name": "slow.zip"}
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["active"]["name"] == "running.zip"
    assert detail["active"]["operation"] == "backup"

    # The list endpoint reports the in-flight operation too.
    listing = await client.get("/api/v1/backups", headers=headers)
    assert listing.json()["active"]["name"] == "running.zip"


@pytest.mark.asyncio
async def test_list_reports_scheduler_health(
    client, superadmin_token: str, db_session: AsyncSession, local_backup_dir: Path
) -> None:
    """consecutive_failures/last_error come from the scheduler when present."""
    from snackbase.infrastructure.backup.alerting import BackupAlertManager

    await _configure_local_backup(db_session, local_backup_dir)
    headers = _auth(superadmin_token)

    idle = await client.get("/api/v1/backups", headers=headers)
    assert idle.status_code == 200
    body = idle.json()
    assert body["consecutive_failures"] == 0
    assert body["last_error"] is None

    # Simulate a scheduler that has seen failures.
    from snackbase.infrastructure.api.app import app

    scheduler = type("S", (), {"alerts": BackupAlertManager()})()
    scheduler.alerts.record_failure("s3 unreachable")
    scheduler.alerts.record_failure("s3 unreachable")
    app.state.backup_scheduler = scheduler
    try:
        failing = await client.get("/api/v1/backups", headers=headers)
        assert failing.status_code == 200
        body = failing.json()
        assert body["consecutive_failures"] == 2
        assert body["last_error"] == "s3 unreachable"
    finally:
        del app.state.backup_scheduler
