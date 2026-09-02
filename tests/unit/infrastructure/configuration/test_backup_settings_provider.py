"""Unit tests for the backup settings configuration provider (F1.3)."""

import pytest

from snackbase.infrastructure.backup.destinations import (
    BACKUP_SETTINGS_CATEGORY,
    BACKUP_SETTINGS_PROVIDER_NAME,
    DEFAULT_BACKUP_DIR,
)
from snackbase.infrastructure.configuration.providers.backup.backup_settings import (
    BackupSettingsConfiguration,
    validate_backup_settings,
)


class TestBackupSettingsConfiguration:
    def test_identity(self) -> None:
        provider = BackupSettingsConfiguration()

        assert provider.category == BACKUP_SETTINGS_CATEGORY == "backup_settings"
        assert provider.provider_name == BACKUP_SETTINGS_PROVIDER_NAME == "backup"
        assert provider.is_builtin is True

    def test_schema_declares_defaults(self) -> None:
        schema = BackupSettingsConfiguration().config_schema
        properties = schema["properties"]

        assert properties["destination"]["enum"] == ["local", "s3"]
        assert properties["destination"]["default"] == "local"
        assert properties["local_path"]["default"] == DEFAULT_BACKUP_DIR
        assert properties["cron"]["default"] == ""
        assert properties["max_keep"]["default"] == 3
        assert properties["max_keep"]["minimum"] == 1

    def test_schema_marks_s3_secret_as_write_only_secret(self) -> None:
        schema = BackupSettingsConfiguration().config_schema
        secret = schema["properties"]["s3_secret_access_key"]

        assert secret["writeOnly"] is True
        assert secret["secret"] is True


class TestValidateBackupSettings:
    def test_valid_cron_passes(self) -> None:
        validate_backup_settings({"cron": "0 2 * * *", "max_keep": 3})

    def test_invalid_cron_raises_parser_message(self) -> None:
        from snackbase.core.cron.parser import validate_cron

        _, expected_message = validate_cron("not a cron")

        with pytest.raises(ValueError, match="cron"):
            validate_backup_settings({"cron": "not a cron"})

    def test_max_keep_below_one_with_schedule_rejected(self) -> None:
        with pytest.raises(ValueError, match="max_keep"):
            validate_backup_settings({"cron": "0 2 * * *", "max_keep": 0})

    def test_max_keep_below_one_without_schedule_allowed(self) -> None:
        validate_backup_settings({"cron": "", "max_keep": 0})

    def test_invalid_destination_rejected(self) -> None:
        with pytest.raises(ValueError, match="destination"):
            validate_backup_settings({"destination": "ftp"})

    def test_empty_values_pass(self) -> None:
        validate_backup_settings({})
