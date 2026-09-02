# Backups

SnackBase can back up its database (and locally stored files) into portable zip
archives and restore them. This page is the configuration reference for the
`backup_settings` category. See the operations section for the API and CLI, and
the restore runbook for how restore works.

Backup archives are instance-level. They are distinct from collection export
(F3.14) and records export (F3.15), which operate at collection scope.
Per-account (tenant-scoped) backup is not supported.

## Configuring backups

Backup settings live in the `backup_settings` configuration category (provider
`backup`) and are managed by a superadmin from **System Settings → Backup**, or
through the configuration API. Values changed here take effect without
restarting the instance.

```
POST /api/v1/admin/configuration
{
  "category": "backup_settings",
  "provider_name": "backup",
  "display_name": "Backup Settings",
  "config": { ... }
}
```

### Configuration keys

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `destination` | string enum | `local` | Where archives are stored: `local` or `s3`. |
| `local_path` | string | `./sb_data/backups` | Directory for archives when `destination` is `local`. Created automatically. |
| `s3_bucket` | string | — | Bucket for archives when `destination` is `s3`. Required for S3. |
| `s3_region` | string | — | AWS region of the bucket. |
| `s3_access_key_id` | string | — | AWS access key ID. Leave empty to use the environment credential chain (for example, an instance role). |
| `s3_secret_access_key` | string (secret) | — | AWS secret access key. Stored encrypted at rest and never returned by the API. |
| `s3_key_prefix` | string | — | Optional key prefix so archives can share a bucket with other content. |
| `s3_endpoint_url` | string | — | Optional custom endpoint for S3-compatible stores (MinIO, R2, LocalStack). |
| `cron` | string (cron) | `""` (empty) | 5-field cron expression for automatic backups, for example `0 2 * * *` (daily at 02:00 UTC). Empty disables scheduled backups. |
| `max_keep` | integer (min 1) | `3` | How many automatic (`@auto_`-prefixed) archives to keep. Older ones are pruned after each scheduled backup. |

Validation on write:

- `cron` must parse as a 5-field cron expression (`minute hour day-of-month
  month day-of-week`, with `*`, steps, ranges, lists, and `MON`-style names).
  An invalid expression is rejected with HTTP 400 and the parser's message.
- `max_keep` below `1` is rejected while a schedule (`cron`) is configured.

### Destinations

- **Local** — archives are written under `local_path`. Local archives share the
  volume with the database: they protect against data mistakes, not against
  losing the volume.
- **S3** — archives are uploaded with boto3's managed transfer API (multipart,
  retry), so archive size is not limited by memory. Any S3-compatible endpoint
  works via `s3_endpoint_url`. Credentials are decrypted from the encrypted
  configuration at use time.

The S3 secret is stored with the same encryption-at-rest path as every other
provider credential. Rotating `SNACKBASE_ENCRYPTION_KEY` invalidates it, along
with all other stored credentials.

## Archives and manifests

Every archive is a zip containing a `manifest.json` at its root. The manifest
records the format version, creation time, SnackBase version, backup type,
database engine, Alembic branch heads captured, whether the local `files/` tree
is included, storage mode, per-table row counts, and — importantly —
fingerprints of the three deployment secrets the archive was taken under
(`SNACKBASE_ENCRYPTION_KEY`, `SNACKBASE_SECRET_KEY`, `SNACKBASE_TOKEN_SECRET`).

A fingerprint is the first 16 hex characters of a domain-separated SHA-256 of
the secret. It is not reversible and is not a verifier for the secret; it only
answers "was this archive taken under the same key?". No secret material is
ever written into the manifest.

Restore checks these fingerprints before touching anything: a mismatched
encryption key is a hard refusal (the archive's stored credentials would be
undecryptable), while signing-key mismatches are warnings an operator can
override knowingly. An archive whose manifest format is newer than the running
SnackBase supports is refused rather than misread.
