# Schema

SnackBase collections support the following field types.

| Type | Storage | Notes |
|------|---------|-------|
| `text` | TEXT | Single-line string |
| `number` | REAL / DOUBLE | Numeric |
| `boolean` | INTEGER / BOOLEAN | True/false |
| `datetime` | DATETIME / timestamptz | Instant |
| `date` | DATE | Calendar date |
| `email` | TEXT | Validated email |
| `url` | TEXT | Validated URL |
| `json` | TEXT / JSONB | Arbitrary JSON |
| `reference` | TEXT (FK) | UUID of a record in another collection |
| `file` | TEXT / JSONB | File metadata |
| `computed` | virtual | Expression; no physical column |
| `user` | TEXT (FK to `users.id`) | UUID of a user in the same account |

## `user` fields

A `user` field stores a UUID and is validated against the system `users`
table, scoped to the same account. `?expand=` replaces the UUID in place
with exactly `{id, email, first_name, last_name, avatar_url}`. Password
hashes, `role_id`, and provider identifiers are never included.

`on_delete` may be `set_null` or `restrict`. `cascade` is rejected at
collection-create.

`user` fields are filterable by equality (`owner = @request.auth.id`).

## Declarative migrations

`POST /api/v1/migrations/plan` diffs a declared schema against the live
registry without applying anything. Field type changes, field removals, and
unique-constraint additions are marked `destructive: true`.

`POST /api/v1/migrations/generate` writes one Alembic revision into the
dynamic migrations directory (`sb_data/migrations`, or
`$SNACKBASE_TEST_DATA_DIR/migrations` under tests) and applies it.
Destructive plans require `{"confirm": true}`; without it the endpoint
returns 409 and writes nothing. Type changes use add-column / backfill /
drop-column rather than in-place `ALTER TYPE`. Superadmin only.
