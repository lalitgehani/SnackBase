"""Migrate existing collection field values when encryption state changes.

Enabling encryption encrypts all non-null account-scoped values for a field.
Disabling encryption decrypts them back to plaintext. Failures leave the
schema unchanged so operators can retry; no secret values are logged.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.infrastructure.persistence.table_builder import TableBuilder
from snackbase.infrastructure.security.encryption import (
    DecryptionError,
    EncryptionService,
)
from snackbase.infrastructure.security.field_encryption import (
    decrypt_value_for_field,
    encrypt_value_for_field,
)

logger = get_logger(__name__)

DEFAULT_BATCH_SIZE = 200


@dataclass
class EncryptionMigrationResult:
    """Outcome of an encryption-state data migration."""

    field_name: str
    direction: str  # "encrypt" | "decrypt"
    rows_processed: int = 0
    rows_converted: int = 0
    rows_skipped_null: int = 0
    failed_ids: list[str] = field(default_factory=list)
    success: bool = True
    error: str | None = None


class EncryptionMigrationService:
    """Batch convert collection field values between plaintext and ciphertext."""

    def __init__(
        self,
        session: AsyncSession,
        encryption: EncryptionService,
        *,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self.session = session
        self.encryption = encryption
        self.batch_size = batch_size

    async def count_non_null_values(
        self,
        collection_name: str,
        field_name: str,
        *,
        account_id: str | None = None,
        exclude_account_id: str | None = None,
    ) -> int:
        """Count non-null values for a field (optionally account-scoped).

        Used to refuse schema flips when unconverted rows would remain.
        Never returns or logs field values.
        """
        table = TableBuilder.generate_table_name(collection_name)
        where = f'"{field_name}" IS NOT NULL'
        params: dict[str, Any] = {}
        if account_id is not None:
            where += " AND account_id = :account_id"
            params["account_id"] = account_id
        if exclude_account_id is not None:
            where += " AND account_id != :exclude_account_id"
            params["exclude_account_id"] = exclude_account_id
        sql = f'SELECT COUNT(*) FROM "{table}" WHERE {where}'
        result = await self.session.execute(text(sql), params)
        count = result.scalar_one()
        return int(count or 0)

    async def migrate_field(
        self,
        collection_name: str,
        field_name: str,
        field_type: str,
        *,
        enable_encryption: bool,
        account_id: str | None = None,
    ) -> EncryptionMigrationResult:
        """Encrypt or decrypt all non-null values for a field.

        Args:
            collection_name: Collection name (logical).
            field_name: Field to convert.
            field_type: Logical type (text or json).
            enable_encryption: True to encrypt plaintext → ciphertext.
            account_id: Optional account scope; when None processes all accounts
                (operator path for full collection conversion).

        Returns:
            EncryptionMigrationResult with counts; success=False on hard failure.
        """
        direction = "encrypt" if enable_encryption else "decrypt"
        result = EncryptionMigrationResult(field_name=field_name, direction=direction)
        table = TableBuilder.generate_table_name(collection_name)

        where = f'"{field_name}" IS NOT NULL'
        params: dict[str, Any] = {}
        if account_id is not None:
            where += " AND account_id = :account_id"
            params["account_id"] = account_id

        offset = 0
        try:
            while True:
                select_sql = (
                    f'SELECT id, "{field_name}" AS val FROM "{table}" '
                    f"WHERE {where} ORDER BY id "
                    f"LIMIT :limit OFFSET :offset"
                )
                qparams = {**params, "limit": self.batch_size, "offset": offset}
                rows = (await self.session.execute(text(select_sql), qparams)).fetchall()
                if not rows:
                    break

                for row in rows:
                    record_id, value = row[0], row[1]
                    result.rows_processed += 1
                    if value is None:
                        result.rows_skipped_null += 1
                        continue
                    try:
                        new_value = self._convert_value(
                            value, field_type, enable_encryption=enable_encryption
                        )
                    except (DecryptionError, ValueError, TypeError, json.JSONDecodeError):
                        result.failed_ids.append(str(record_id))
                        result.success = False
                        result.error = "conversion_failed"
                        logger.error(
                            "Encryption migration value conversion failed",
                            collection=collection_name,
                            field=field_name,
                            record_id=record_id,
                            direction=direction,
                        )
                        # Do not continue partially marking success
                        await self.session.rollback()
                        return result

                    update_sql = (
                        f'UPDATE "{table}" SET "{field_name}" = :val WHERE id = :id'
                    )
                    await self.session.execute(
                        text(update_sql), {"val": new_value, "id": record_id}
                    )
                    result.rows_converted += 1

                offset += self.batch_size
                await self.session.flush()

            await self.session.commit()
            logger.info(
                "Encryption migration completed",
                collection=collection_name,
                field=field_name,
                direction=direction,
                rows_converted=result.rows_converted,
                rows_processed=result.rows_processed,
            )
            return result
        except Exception as e:
            await self.session.rollback()
            result.success = False
            result.error = type(e).__name__
            logger.error(
                "Encryption migration aborted",
                collection=collection_name,
                field=field_name,
                direction=direction,
                error=type(e).__name__,
            )
            return result

    def _convert_value(
        self, value: Any, field_type: str, *, enable_encryption: bool
    ) -> Any:
        ft = field_type.lower()
        if enable_encryption:
            # JSON columns may already be dict/list from driver
            if ft == "json" and isinstance(value, str):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    # Treat as plain string payload
                    pass
            encrypted = encrypt_value_for_field(value, ft, self.encryption)
            if ft == "json" and encrypted is not None:
                # Store as JSON string (matches record repository JSON path)
                return json.dumps(encrypted) if not isinstance(encrypted, str) else encrypted
            return encrypted

        # Decrypt path
        raw = value
        if ft == "json" and isinstance(value, str):
            # Stored as JSON string of ciphertext
            try:
                parsed = json.loads(value)
                if isinstance(parsed, str):
                    raw = parsed
            except json.JSONDecodeError:
                raw = value
        if not isinstance(raw, str):
            raise DecryptionError("Decryption failed")
        decrypted = decrypt_value_for_field(raw, ft, self.encryption)
        if ft == "json":
            return json.dumps(decrypted)
        return decrypted
