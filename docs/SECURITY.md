# Security

## User field expansion

Expanding a `user` field returns a redacted projection:

```
{id, email, first_name, last_name, avatar_url}
```

The following keys are never present: `password_hash`, `role_id`,
`auth_provider`, `external_id`. Cross-account user ids fail validation on
write (`invalid_reference`) and expand to `null` on read.

## In-process transport

`snackbase.embedded.InProcessClient` is a transport swap, not an
authorization bypass. Calls dispatch through the mounted FastAPI app via
`httpx.ASGITransport` with the caller's bearer token. There is no
service-role or superadmin parameter.

## Admin panel

The admin SPA is served at `/_/`. Set `SNACKAPP_ADMIN=off` to return 404
for `/_` and everything beneath it. The site root is reserved for a mounted
application.
