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

## Creating and managing backups

### Admin API

All endpoints require superadmin access and live under `/api/v1/backups`.

| Endpoint | Purpose |
| --- | --- |
| `POST /api/v1/backups` | Start creating an archive; returns 202. Body `{"name": "my_backup.zip"}` is optional — without it the archive is named `snackbase_backup_<UTC yyyymmddHHMMSS>.zip`. |
| `GET /api/v1/backups` | List every archive (newest first) with `name`, `size`, `modified`, and `is_automatic`, plus the `active` in-flight operation when one is running. |
| `DELETE /api/v1/backups/{name}` | Delete an archive (204). Returns 404 for an absent name and 409 while it is being written. |
| `GET /api/v1/backups/{name}/download` | Stream the archive as `application/zip` attachment. |
| `POST /api/v1/backups/upload` | Multipart upload of an archive taken elsewhere. The payload must be a readable zip carrying a parsable `manifest.json`. |

Manual archive names must match `^[a-z0-9_-]{1,150}\.zip$`. The `@` character is
reserved: automatic backups are named `@auto_…`, and a manual name can never
collide with the retention prefix. Duplicate names answer 409, as does a create
while another backup or restore is in flight (the response names the running
operation). Uploads are exempt from the user-file `max_file_size` limit —
archives are legitimately large.

Only one backup or restore runs at a time. In-flight state is kept in memory
plus a lock file at the backup directory, never in the database, so no backup
job row can be captured by its own snapshot and restored as a stuck `running`
job.

### CLI

```bash
uv run python -m snackbase backup create [--name TEXT]
uv run python -m snackbase backup list
uv run python -m snackbase backup delete NAME [--yes]
```

The commands talk to the configured destination directly and work without a
running server, so they can be driven by an external cron. `backup delete`
prompts for confirmation unless `--yes` is passed. Every backup event —
`backup.create.started`, `backup.create.completed`, `backup.create.failed`,
`backup.delete` — is appended to the immutable audit log, recording the archive
name, destination type, byte size on completion, and the acting user (`system`
for CLI and scheduled runs).

### Disk space

Creating a backup needs roughly **2× the database size** of free disk space at
the backup location: the `VACUUM INTO` snapshot plus the compressed archive
coexist during the build. The snapshot and its staging archive are deleted on
both success and failure.

### How consistency works

SQLite snapshots use `VACUUM INTO`, which writes a transactionally consistent
copy of the database under a brief lock — a backup taken under heavy write
load captures a coherent state with no partial transactions. The snapshot
passes `PRAGMA integrity_check` and is independent of the live WAL. The
archive layout is:

```
manifest.json        self-describing metadata (see above)
data.db              the VACUUM INTO snapshot
files/<account_id>/… the tree under settings.storage_path (local storage only)
```

When the active file storage provider is S3, the `files/` tree is not archived
(files live in the bucket, not on the volume) and the manifest records
`includes_files: false` and `storage_mode: "s3"`. The backup directory itself
is never included in an archive.
