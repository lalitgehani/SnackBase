"""Integration tests for the backup settings configuration category (F1.3)."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.config import get_settings
from snackbase.infrastructure.backup.destinations import (
    BackupConfigurationError,
    LocalBackupDestination,
    S3BackupDestination,
    resolve_destination,
)
from snackbase.infrastructure.configuration.providers.backup.backup_settings import (
    BackupSettingsConfiguration,
)
from snackbase.infrastructure.persistence.models.configuration import ConfigurationModel


def _register_backup_provider() -> None:
    """Attach a settings-keyed registry with the backup provider registered.

    Other test modules replace ``app.state.config_registry`` with registries
    built from different keys, so the test builds its own from ``get_settings()``
    — the same key ``resolve_destination`` uses — making it order-independent.
    """
    from snackbase.core.configuration.config_registry import ConfigurationRegistry
    from snackbase.infrastructure.api.app import app
    from snackbase.infrastructure.security.encryption import EncryptionService

    settings = get_settings()
    app.state.config_registry = ConfigurationRegistry(
        EncryptionService(settings.encryption_key)
    )
    provider = BackupSettingsConfiguration()
    app.state.config_registry.register_provider_definition(
        category=provider.category,
        provider_name=provider.provider_name,
        display_name=provider.display_name,
        logo_url=provider.logo_url,
        config_schema=provider.config_schema,
        is_builtin=provider.is_builtin,
    )


def _admin_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_backup_settings(
    client, superadmin_token: str, config: dict
) -> dict:
    response = await client.post(
        "/api/v1/admin/configuration",
        headers=_admin_headers(superadmin_token),
        json={
            "category": "backup_settings",
            "provider_name": "backup",
            "display_name": "Backup Settings",
            "config": config,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_definition_listed_for_superadmin(client, superadmin_token: str) -> None:
    _register_backup_provider()

    response = await client.get(
        "/api/v1/admin/configuration/providers",
        params={"category": "backup_settings"},
        headers=_admin_headers(superadmin_token),
    )

    assert response.status_code == 200
    providers = response.json()
    assert any(
        p["provider_name"] == "backup" and p["category"] == "backup_settings"
        for p in providers
    )


@pytest.mark.asyncio
async def test_providers_endpoint_forbidden_for_non_superadmin(
    client, regular_user_token: str
) -> None:
    response = await client.get(
        "/api/v1/admin/configuration/providers",
        params={"category": "backup_settings"},
        headers=_admin_headers(regular_user_token),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_s3_secret_stored_encrypted(
    client, superadmin_token: str, db_session: AsyncSession
) -> None:
    _register_backup_provider()

    await _create_backup_settings(
        client,
        superadmin_token,
        {
            "destination": "s3",
            "s3_bucket": "sb-backups",
            "s3_secret_access_key": "plain-text-secret",
        },
    )

    result = await db_session.execute(
        select(ConfigurationModel).where(
            ConfigurationModel.category == "backup_settings",
        )
    )
    model = result.scalar_one()
    assert model.is_system is True
    assert model.account_id == "00000000-0000-0000-0000-000000000000"
    stored = model.config
    assert stored["s3_secret_access_key"] != "plain-text-secret"
    assert "plain-text-secret" not in str(stored)

    values_response = await client.get(
        f"/api/v1/admin/configuration/{model.id}/values",
        headers=_admin_headers(superadmin_token),
    )
    assert values_response.status_code == 200
    values = values_response.json()
    assert values["s3_secret_access_key"] != "plain-text-secret"


@pytest.mark.asyncio
async def test_valid_cron_accepted_on_create(client, superadmin_token: str) -> None:
    _register_backup_provider()

    response = await client.post(
        "/api/v1/admin/configuration",
        headers=_admin_headers(superadmin_token),
        json={
            "category": "backup_settings",
            "provider_name": "backup",
            "display_name": "Backup Settings",
            "config": {"cron": "0 2 * * *", "max_keep": 3},
        },
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_invalid_cron_rejected_on_create(client, superadmin_token: str) -> None:
    _register_backup_provider()

    response = await client.post(
        "/api/v1/admin/configuration",
        headers=_admin_headers(superadmin_token),
        json={
            "category": "backup_settings",
            "provider_name": "backup",
            "display_name": "Backup Settings",
            "config": {"cron": "not a cron"},
        },
    )

    assert response.status_code == 400
    assert "cron" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_zero_max_keep_with_schedule_rejected(
    client, superadmin_token: str
) -> None:
    _register_backup_provider()

    response = await client.post(
        "/api/v1/admin/configuration",
        headers=_admin_headers(superadmin_token),
        json={
            "category": "backup_settings",
            "provider_name": "backup",
            "display_name": "Backup Settings",
            "config": {"cron": "0 2 * * *", "max_keep": 0},
        },
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_zero_max_keep_without_schedule_accepted(
    client, superadmin_token: str
) -> None:
    _register_backup_provider()

    response = await client.post(
        "/api/v1/admin/configuration",
        headers=_admin_headers(superadmin_token),
        json={
            "category": "backup_settings",
            "provider_name": "backup",
            "display_name": "Backup Settings",
            "config": {"cron": "", "max_keep": 0},
        },
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_invalid_combination_rejected_on_update(
    client, superadmin_token: str, db_session: AsyncSession
) -> None:
    _register_backup_provider()
    created = await _create_backup_settings(
        client, superadmin_token, {"cron": "0 2 * * *", "max_keep": 2}
    )

    response = await client.patch(
        f"/api/v1/admin/configuration/{created['id']}/values",
        headers=_admin_headers(superadmin_token),
        json={"cron": "0 3 * * *", "max_keep": 0},
    )

    assert response.status_code == 400
    # The invalid combination must not have been persisted.
    model = await db_session.get(ConfigurationModel, created["id"])
    assert model is not None
    assert model.config["max_keep"] == 2


@pytest.mark.asyncio
async def test_resolve_destination_s3_from_configuration(
    client, superadmin_token: str, db_session: AsyncSession
) -> None:
    _register_backup_provider()
    await _create_backup_settings(
        client,
        superadmin_token,
        {
            "destination": "s3",
            "s3_bucket": "sb-backups",
            "s3_region": "eu-west-1",
            "s3_secret_access_key": "plain-text-secret",
            "s3_key_prefix": "instances/abc",
        },
    )

    destination = await resolve_destination(db_session)

    assert isinstance(destination, S3BackupDestination)
    assert destination.bucket == "sb-backups"
    assert destination.region == "eu-west-1"
    assert destination.key_prefix == "instances/abc"
    assert destination.secret_access_key == "plain-text-secret"


@pytest.mark.asyncio
async def test_resolve_destination_s3_without_bucket_raises(
    client, superadmin_token: str, db_session: AsyncSession
) -> None:
    _register_backup_provider()
    await _create_backup_settings(
        client, superadmin_token, {"destination": "s3", "s3_region": "eu-west-1"}
    )

    with pytest.raises(BackupConfigurationError):
        await resolve_destination(db_session)


@pytest.mark.asyncio
async def test_resolve_destination_local_from_configuration(
    client, superadmin_token: str, db_session: AsyncSession
) -> None:
    _register_backup_provider()
    await _create_backup_settings(
        client,
        superadmin_token,
        {"destination": "local", "local_path": "/tmp/sb-backups-test"},
    )

    destination = await resolve_destination(db_session)

    assert isinstance(destination, LocalBackupDestination)
    assert str(destination.base_path) == "/tmp/sb-backups-test"


@pytest.mark.asyncio
async def test_resolve_destination_unknown_type_raises(
    db_session: AsyncSession,
) -> None:
    import uuid

    db_session.add(
        ConfigurationModel(
            id=str(uuid.uuid4()),
            account_id="00000000-0000-0000-0000-000000000000",
            category="backup_settings",
            provider_name="backup",
            display_name="Backup Settings",
            config={"destination": "ftp"},
            enabled=True,
            is_builtin=True,
            is_system=True,
        )
    )
    await db_session.commit()

    with pytest.raises(BackupConfigurationError):
        await resolve_destination(db_session)
