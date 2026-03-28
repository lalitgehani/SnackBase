"""Integration tests for the ?filter= query parameter on the records list endpoint.

Tests cover:
- Each comparison operator
- IN operator
- IS NULL / IS NOT NULL
- AND / OR / parentheses grouping
- System field filtering
- Error cases (unknown field, context variables, malformed syntax)
- Breaking change: old ?field=value params return 400 with migration hint
- Pagination respects the filter (total count)
"""

import pytest
from httpx import AsyncClient


COLLECTION = "filter_test_col"
SCHEMA = [
    {"name": "title", "type": "text", "required": True},
    {"name": "price", "type": "number"},
    {"name": "status", "type": "text"},
    {"name": "is_featured", "type": "boolean"},
    {"name": "deleted_at", "type": "datetime"},
    {"name": "category", "type": "text"},
]


@pytest.fixture(autouse=True)
async def setup_collection(client: AsyncClient, superadmin_token):
    """Create the test collection and seed records before each test."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create collection with open rules
    await client.post(
        "/api/v1/collections",
        json={"name": COLLECTION, "label": "Filter Test", "schema": SCHEMA},
        headers=headers,
    )
    # Open all rules for testing
    await client.put(
        f"/api/v1/collections/{COLLECTION}/rules",
        json={
            "list_rule": "",
            "view_rule": "",
            "create_rule": "",
            "update_rule": "",
            "delete_rule": "",
        },
        headers=headers,
    )

    # Seed test records
    records = [
        {"title": "Apple", "price": 1.5, "status": "active", "is_featured": True, "category": "fruit"},
        {"title": "Banana", "price": 0.5, "status": "active", "is_featured": False, "category": "fruit"},
        {"title": "Carrot", "price": 0.8, "status": "pending", "is_featured": False, "category": "vegetable"},
        {"title": "Durian", "price": 20.0, "status": "archived", "is_featured": True, "category": "fruit"},
        {"title": "Eggplant", "price": 1.2, "status": "active", "is_featured": False, "category": "vegetable"},
    ]
    for record in records:
        r = await client.post(f"/api/v1/records/{COLLECTION}", json=record, headers=headers)
        assert r.status_code == 201, f"Failed to seed record: {r.text}"

    yield

    # Cleanup: delete collection after test
    await client.delete(f"/api/v1/collections/{COLLECTION}", headers=headers)


@pytest.mark.asyncio
async def test_filter_equality(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": 'status = "active"'},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    for item in data["items"]:
        assert item["status"] == "active"


@pytest.mark.asyncio
async def test_filter_not_equal(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": 'status != "archived"'},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    for item in data["items"]:
        assert item["status"] != "archived"


@pytest.mark.asyncio
async def test_filter_greater_than(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": "price > 1.0"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3  # Apple (1.5), Durian (20.0), Eggplant (1.2)
    for item in data["items"]:
        assert item["price"] > 1.0


@pytest.mark.asyncio
async def test_filter_less_than(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": "price < 1.0"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2  # Banana (0.5), Carrot (0.8)


@pytest.mark.asyncio
async def test_filter_greater_than_or_equal(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": "price >= 20.0"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1  # Durian


@pytest.mark.asyncio
async def test_filter_less_than_or_equal(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": "price <= 0.8"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 2  # Banana, Carrot


@pytest.mark.asyncio
async def test_filter_like(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": 'title ~ "E%"'},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1  # Eggplant


@pytest.mark.asyncio
async def test_filter_boolean(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": "is_featured = true"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 2  # Apple, Durian


@pytest.mark.asyncio
async def test_filter_in_operator(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": 'status IN ("active", "pending")'},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4  # Apple, Banana, Carrot, Eggplant
    for item in data["items"]:
        assert item["status"] in ("active", "pending")


@pytest.mark.asyncio
async def test_filter_is_null(client: AsyncClient, superadmin_token):
    """All seeded records have NULL deleted_at (not explicitly set)."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": "deleted_at IS NULL"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 5  # All records have null deleted_at


@pytest.mark.asyncio
async def test_filter_is_not_null(client: AsyncClient, superadmin_token):
    """No seeded records have a non-null deleted_at."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": "deleted_at IS NOT NULL"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_filter_and_logic(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": 'status = "active" && price > 1.0'},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2  # Apple (active, 1.5), Eggplant (active, 1.2)
    for item in data["items"]:
        assert item["status"] == "active"
        assert item["price"] > 1.0


@pytest.mark.asyncio
async def test_filter_or_logic(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": 'status = "pending" || status = "archived"'},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2  # Carrot (pending), Durian (archived)


@pytest.mark.asyncio
async def test_filter_parentheses_grouping(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": '(status = "active" || status = "pending") && price > 1.0'},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # active + price > 1.0: Apple (1.5), Eggplant (1.2)
    # pending + price > 1.0: none (Carrot is 0.8)
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_filter_system_field_created_by(client: AsyncClient, superadmin_token):
    """Filter on system field created_by works."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": 'created_by = "superadmin"'},
        headers=headers,
    )
    assert resp.status_code == 200
    # All records were created by superadmin
    assert resp.json()["total"] == 5


@pytest.mark.asyncio
async def test_filter_pagination_respects_filter(client: AsyncClient, superadmin_token):
    """Total count in pagination reflects the filtered count."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": 'category = "fruit"', "limit": 2, "skip": 0},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3  # Apple, Banana, Durian
    assert len(data["items"]) == 2  # Only 2 returned due to limit
    for item in data["items"]:
        assert item["category"] == "fruit"


@pytest.mark.asyncio
async def test_filter_pagination_second_page(client: AsyncClient, superadmin_token):
    """Second page of filtered results."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": 'category = "fruit"', "limit": 2, "skip": 2},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 1  # Only 1 remaining


@pytest.mark.asyncio
async def test_filter_unknown_field_returns_400(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": 'nonexistent_field = "value"'},
        headers=headers,
    )
    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data
    assert "nonexistent_field" in data["message"]


@pytest.mark.asyncio
async def test_filter_context_variable_returns_400(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": '@request.auth.id = "user123"'},
        headers=headers,
    )
    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_filter_malformed_syntax_returns_400(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": "title ==="},
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_old_query_param_returns_400_with_migration_hint(
    client: AsyncClient, superadmin_token
):
    """Old-style ?field=value filtering should return 400 with a migration hint."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"status": "active"},
        headers=headers,
    )
    assert resp.status_code == 400
    data = resp.json()
    assert "filter" in data["message"].lower()


@pytest.mark.asyncio
async def test_no_filter_returns_all_records(client: AsyncClient, superadmin_token):
    """Without a filter, all records are returned."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(f"/api/v1/records/{COLLECTION}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 5


@pytest.mark.asyncio
async def test_empty_filter_returns_all_records(client: AsyncClient, superadmin_token):
    """Empty filter string behaves like no filter."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": ""},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 5
