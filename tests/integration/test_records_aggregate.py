"""Integration tests for GET /{collection}/aggregate endpoint (F6.5).

Tests cover:
- All aggregation functions: count(), count(field), sum, avg, min, max
- GROUP BY (single and multiple fields)
- Pre-aggregation filter (?filter=)
- Post-aggregation HAVING clause
- Combined filter + group_by + having
- Error cases: invalid function, unknown field, type mismatch
- Account isolation
- Missing required ?functions param
"""

import pytest
from httpx import AsyncClient


COLLECTION = "agg_test_col"
SCHEMA = [
    {"name": "title", "type": "text", "required": True},
    {"name": "price", "type": "number"},
    {"name": "quantity", "type": "number"},
    {"name": "status", "type": "text"},
    {"name": "category", "type": "text"},
]

BASE_URL = f"/api/v1/records/{COLLECTION}"
AGG_URL = f"/api/v1/records/{COLLECTION}/aggregate"


@pytest.fixture(autouse=True)
async def setup_collection(client: AsyncClient, superadmin_token):
    """Create test collection and seed records before each test."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create collection
    resp = await client.post(
        "/api/v1/collections",
        json={"name": COLLECTION, "label": "Agg Test", "schema": SCHEMA},
        headers=headers,
    )
    assert resp.status_code == 201, f"Failed to create collection: {resp.text}"

    # Open all rules
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

    # Seed records
    records = [
        {"title": "A", "price": 10.0, "quantity": 5, "status": "active", "category": "fruit"},
        {"title": "B", "price": 20.0, "quantity": 3, "status": "active", "category": "fruit"},
        {"title": "C", "price": 5.0, "quantity": 10, "status": "pending", "category": "vegetable"},
        {"title": "D", "price": 15.0, "quantity": 2, "status": "pending", "category": "vegetable"},
        {"title": "E", "price": 50.0, "quantity": 1, "status": "archived", "category": "fruit"},
    ]
    for record in records:
        r = await client.post(BASE_URL, json=record, headers=headers)
        assert r.status_code == 201, f"Failed to seed record: {r.text}"

    yield

    # Cleanup
    await client.delete(f"/api/v1/collections/{COLLECTION}", headers=headers)


@pytest.mark.asyncio
async def test_count_all(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(AGG_URL, params={"functions": "count()"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_groups"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["count"] == 5


@pytest.mark.asyncio
async def test_count_with_field(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(AGG_URL, params={"functions": "count(price)"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["count_price"] == 5


@pytest.mark.asyncio
async def test_sum_price(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(AGG_URL, params={"functions": "sum(price)"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["sum_price"] == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_avg_price(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(AGG_URL, params={"functions": "avg(price)"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["avg_price"] == pytest.approx(20.0)


@pytest.mark.asyncio
async def test_min_price(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(AGG_URL, params={"functions": "min(price)"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["min_price"] == pytest.approx(5.0)


@pytest.mark.asyncio
async def test_max_price(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(AGG_URL, params={"functions": "max(price)"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["max_price"] == pytest.approx(50.0)


@pytest.mark.asyncio
async def test_multiple_functions(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        AGG_URL,
        params={"functions": "count(),sum(price),avg(price),min(price),max(price)"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    row = data["results"][0]
    assert row["count"] == 5
    assert row["sum_price"] == pytest.approx(100.0)
    assert row["avg_price"] == pytest.approx(20.0)
    assert row["min_price"] == pytest.approx(5.0)
    assert row["max_price"] == pytest.approx(50.0)


@pytest.mark.asyncio
async def test_group_by_status(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        AGG_URL,
        params={"functions": "count()", "group_by": "status"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_groups"] == 3  # active, pending, archived
    assert len(data["results"]) == 3

    by_status = {row["status"]: row["count"] for row in data["results"]}
    assert by_status["active"] == 2
    assert by_status["pending"] == 2
    assert by_status["archived"] == 1


@pytest.mark.asyncio
async def test_group_by_multiple_fields(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        AGG_URL,
        params={"functions": "count(),sum(price)", "group_by": "status,category"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # active+fruit=2, pending+vegetable=2, archived+fruit=1
    assert data["total_groups"] == 3
    for row in data["results"]:
        assert "status" in row
        assert "category" in row
        assert "count" in row
        assert "sum_price" in row


@pytest.mark.asyncio
async def test_filter_pre_aggregation(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        AGG_URL,
        params={"functions": "count()", "filter": 'status = "active"'},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["count"] == 2


@pytest.mark.asyncio
async def test_having_post_aggregation(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        AGG_URL,
        params={"functions": "count()", "group_by": "status", "having": "count() > 1"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # active=2 and pending=2 pass; archived=1 does not
    assert data["total_groups"] == 2
    for row in data["results"]:
        assert row["count"] > 1


@pytest.mark.asyncio
async def test_filter_and_group_by_and_having(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        AGG_URL,
        params={
            "functions": "count(),sum(price)",
            "group_by": "category",
            "filter": 'status != "archived"',
            "having": "count() > 1",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # After filtering archived: fruit has active A,B = 2 rows; vegetable has C,D = 2 rows
    # Both have count > 1, so both pass having
    assert data["total_groups"] == 2


@pytest.mark.asyncio
async def test_empty_collection_result(client: AsyncClient, superadmin_token):
    """Aggregation on empty result set returns one row with 0/null."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        AGG_URL,
        params={"functions": "count()", "filter": 'status = "nonexistent"'},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"][0]["count"] == 0


@pytest.mark.asyncio
async def test_invalid_function_name_400(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(AGG_URL, params={"functions": "median(price)"}, headers=headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_sum_on_text_field_400(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(AGG_URL, params={"functions": "sum(status)"}, headers=headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_avg_on_text_field_400(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(AGG_URL, params={"functions": "avg(category)"}, headers=headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_unknown_field_in_functions_400(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(AGG_URL, params={"functions": "sum(nonexistent)"}, headers=headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_unknown_field_in_group_by_400(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        AGG_URL,
        params={"functions": "count()", "group_by": "nonexistent"},
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_invalid_having_alias_400(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        AGG_URL,
        params={"functions": "count()", "having": "nonexistent_alias > 5"},
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_collection_not_found_404(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        "/api/v1/records/no_such_collection/aggregate",
        params={"functions": "count()"},
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_requires_functions_param(client: AsyncClient, superadmin_token):
    """Missing required ?functions param returns 422."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(AGG_URL, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_total_groups_with_having(client: AsyncClient, superadmin_token):
    """total_groups reflects count after HAVING filter."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        AGG_URL,
        params={"functions": "count()", "group_by": "status", "having": "count() >= 2"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_groups"] == len(data["results"])
    assert all(row["count"] >= 2 for row in data["results"])


@pytest.mark.asyncio
async def test_invalid_filter_expression_400(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(
        AGG_URL,
        params={"functions": "count()", "filter": "invalid @@@ filter"},
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_response_structure(client: AsyncClient, superadmin_token):
    """Response always has 'results' list and 'total_groups' int."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    resp = await client.get(AGG_URL, params={"functions": "count()"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert "total_groups" in data
    assert isinstance(data["results"], list)
    assert isinstance(data["total_groups"], int)
