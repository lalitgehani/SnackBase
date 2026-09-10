from snackbase.domain.services.user_field import USER_PUBLIC_KEYS, project_user_public


def test_project_user_public_exact_keys():
    row = {
        "id": "u1",
        "email": "a@example.com",
        "password_hash": "secret",
        "role_id": 1,
        "auth_provider": "password",
        "external_id": "ext",
        "profile_data": {
            "first_name": "Ada",
            "last_name": "Lovelace",
            "avatar_url": "https://example.com/a.png",
        },
    }
    projected = project_user_public(row)
    assert list(projected.keys()) == list(USER_PUBLIC_KEYS)
    assert projected == {
        "id": "u1",
        "email": "a@example.com",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "avatar_url": "https://example.com/a.png",
    }
    for key in ("password_hash", "role_id", "auth_provider", "external_id"):
        assert key not in projected
