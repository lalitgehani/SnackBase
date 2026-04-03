"""Integration tests for computed/virtual fields.

Tests cover:
- Collection creation validation (valid and invalid computed field definitions)
- Records list and single-record GET return computed field values
- Computed field values update when source fields change (truly derived, not stored)
- Cannot write to a computed field directly
- Filter by computed field
- Sort by computed field
- Edge cases: no computed fields, null source values
"""

import pytest
from httpx import AsyncClient


COLLECTION = "computed_test_col"

SCHEMA = [
    {"name": "first_name", "type": "text", "required": True},
    {"name": "last_name", "type": "text", "required": True},
    {"name": "price", "type": "number"},
    {"name": "quantity", "type": "number"},
    {
        "name": "full_name",
        "type": "computed",
        "expression": "concat(first_name, ' ', last_name)",
        "return_type": "text",
    },
    {
        "name": "total_price",
        "type": "computed",
        "expression": "price * quantity",
        "return_type": "number",
    },
]

# Seed data → full_name / total_price
# Alice Smith  → "Alice Smith" / 30.0
# Bob Jones    → "Bob Jones"   / 20.0
# Carol Smith  → "Carol Smith" / 20.0
SEED_RECORDS = [
    {"first_name": "Alice", "last_name": "Smith", "price": 10.0, "quantity": 3},
    {"first_name": "Bob", "last_name": "Jones", "price": 5.0, "quantity": 4},
    {"first_name": "Carol", "last_name": "Smith", "price": 20.0, "quantity": 1},
]


@pytest.fixture(autouse=True)
async def setup_collection(client: AsyncClient, superadmin_token):
    """Create the test collection and seed records before each test."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    await client.post(
        "/api/v1/collections",
        json={"name": COLLECTION, "label": "Computed Test", "schema": SCHEMA},
        headers=headers,
    )
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
    for record in SEED_RECORDS:
        r = await client.post(
            f"/api/v1/records/{COLLECTION}", json=record, headers=headers
        )
        assert r.status_code == 201, f"Failed to seed record: {r.text}"

    yield

    await client.delete(f"/api/v1/collections/{COLLECTION}", headers=headers)


# ── Collection Creation Validation ────────────────────────────────────────────
# These tests manage their own collection and do NOT rely on the autouse fixture.

@pytest.mark.asyncio
async def test_create_collection_with_computed_field_valid(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    schema = [
        {"name": "price", "type": "number"},
        {"name": "quantity", "type": "number"},
        {
            "name": "total",
            "type": "computed",
            "expression": "price * quantity",
            "return_type": "number",
        },
    ]
    r = await client.post(
        "/api/v1/collections",
        json={"name": "valid_computed_col", "label": "Valid", "schema": schema},
        headers=headers,
    )
    assert r.status_code == 201
    field_names = [f["name"] for f in r.json()["schema"]]
    assert "total" in field_names
    await client.delete("/api/v1/collections/valid_computed_col", headers=headers)


@pytest.mark.asyncio
async def test_create_computed_field_without_expression_returns_400(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    schema = [
        {"name": "price", "type": "number"},
        {"name": "bad", "type": "computed", "return_type": "number"},
    ]
    r = await client.post(
        "/api/v1/collections",
        json={"name": "invalid_col_expr", "label": "Invalid", "schema": schema},
        headers=headers,
    )
    assert r.status_code == 400
    assert "expression" in r.json()["message"]


@pytest.mark.asyncio
async def test_create_computed_field_without_return_type_returns_400(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    schema = [
        {"name": "price", "type": "number"},
        {"name": "bad", "type": "computed", "expression": "price * 2"},
    ]
    r = await client.post(
        "/api/v1/collections",
        json={"name": "invalid_col_rt", "label": "Invalid", "schema": schema},
        headers=headers,
    )
    assert r.status_code == 400
    assert "return_type" in r.json()["message"]


@pytest.mark.asyncio
async def test_create_computed_field_with_invalid_return_type_returns_400(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    schema = [
        {"name": "price", "type": "number"},
        {
            "name": "bad",
            "type": "computed",
            "expression": "price * 2",
            "return_type": "blob",
        },
    ]
    r = await client.post(
        "/api/v1/collections",
        json={"name": "invalid_col_rt2", "label": "Invalid", "schema": schema},
        headers=headers,
    )
    assert r.status_code == 400
    assert "blob" in r.json()["message"]


@pytest.mark.asyncio
async def test_create_computed_field_with_required_flag_returns_400(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    schema = [
        {"name": "price", "type": "number"},
        {
            "name": "bad",
            "type": "computed",
            "expression": "price * 2",
            "return_type": "number",
            "required": True,
        },
    ]
    r = await client.post(
        "/api/v1/collections",
        json={"name": "invalid_col_req", "label": "Invalid", "schema": schema},
        headers=headers,
    )
    assert r.status_code == 400
    assert "required" in r.json()["message"]


@pytest.mark.asyncio
async def test_create_computed_field_with_default_returns_400(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    schema = [
        {"name": "price", "type": "number"},
        {
            "name": "bad",
            "type": "computed",
            "expression": "price * 2",
            "return_type": "number",
            "default": 0,
        },
    ]
    r = await client.post(
        "/api/v1/collections",
        json={"name": "invalid_col_def", "label": "Invalid", "schema": schema},
        headers=headers,
    )
    assert r.status_code == 400
    assert "default" in r.json()["message"]


@pytest.mark.asyncio
async def test_create_computed_field_with_unique_returns_400(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    schema = [
        {"name": "price", "type": "number"},
        {
            "name": "bad",
            "type": "computed",
            "expression": "price * 2",
            "return_type": "number",
            "unique": True,
        },
    ]
    r = await client.post(
        "/api/v1/collections",
        json={"name": "invalid_col_uniq", "label": "Invalid", "schema": schema},
        headers=headers,
    )
    assert r.status_code == 400
    assert "unique" in r.json()["message"]


@pytest.mark.asyncio
async def test_create_computed_field_referencing_unknown_field_returns_400(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    schema = [
        {"name": "price", "type": "number"},
        {
            "name": "bad",
            "type": "computed",
            "expression": "nonexistent * price",
            "return_type": "number",
        },
    ]
    r = await client.post(
        "/api/v1/collections",
        json={"name": "invalid_col_ref", "label": "Invalid", "schema": schema},
        headers=headers,
    )
    assert r.status_code == 400
    assert "nonexistent" in r.json()["message"]


@pytest.mark.asyncio
async def test_create_computed_field_with_invalid_expression_syntax_returns_400(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    schema = [
        {"name": "price", "type": "number"},
        {
            "name": "bad",
            "type": "computed",
            "expression": "price ***",
            "return_type": "number",
        },
    ]
    r = await client.post(
        "/api/v1/collections",
        json={"name": "invalid_col_syn", "label": "Invalid", "schema": schema},
        headers=headers,
    )
    assert r.status_code == 400
    assert "expression" in r.json()["message"].lower()


@pytest.mark.asyncio
async def test_max_computed_fields_limit_returns_400(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    schema = [{"name": "price", "type": "number"}]
    for i in range(11):
        schema.append(
            {
                "name": f"comp_{i}",
                "type": "computed",
                "expression": "price + 0",
                "return_type": "number",
            }
        )
    r = await client.post(
        "/api/v1/collections",
        json={"name": "invalid_col_max", "label": "Invalid", "schema": schema},
        headers=headers,
    )
    assert r.status_code == 400
    assert "computed" in r.json()["message"].lower()


# ── Records Read — Computed Values ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_records_includes_computed_fields(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    r = await client.get(f"/api/v1/records/{COLLECTION}", headers=headers)
    assert r.status_code == 200
    data = r.json()
    for item in data["items"]:
        assert "full_name" in item
        assert "total_price" in item


@pytest.mark.asyncio
async def test_computed_field_value_matches_expression(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    r = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": 'first_name = "Alice"'},
        headers=headers,
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    alice = items[0]
    assert alice["full_name"] == "Alice Smith"
    assert alice["total_price"] == 30.0


@pytest.mark.asyncio
async def test_get_by_id_includes_computed_fields(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    # Get list to find Alice's ID
    r = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": 'first_name = "Alice"'},
        headers=headers,
    )
    alice_id = r.json()["items"][0]["id"]

    r = await client.get(
        f"/api/v1/records/{COLLECTION}/{alice_id}", headers=headers
    )
    assert r.status_code == 200
    record = r.json()
    assert record["full_name"] == "Alice Smith"
    assert record["total_price"] == 30.0


@pytest.mark.asyncio
async def test_computed_field_updates_when_source_changes(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    # Create a fresh record
    r = await client.post(
        f"/api/v1/records/{COLLECTION}",
        json={"first_name": "Test", "last_name": "User", "price": 5.0, "quantity": 2},
        headers=headers,
    )
    assert r.status_code == 201
    record_id = r.json()["id"]

    # Verify initial computed value
    r = await client.get(
        f"/api/v1/records/{COLLECTION}/{record_id}", headers=headers
    )
    assert r.json()["total_price"] == 10.0

    # Update quantity
    r = await client.patch(
        f"/api/v1/records/{COLLECTION}/{record_id}",
        json={"quantity": 4},
        headers=headers,
    )
    assert r.status_code == 200

    # Verify computed value reflects the update
    r = await client.get(
        f"/api/v1/records/{COLLECTION}/{record_id}", headers=headers
    )
    assert r.json()["total_price"] == 20.0


# ── Cannot Write to Computed Field ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_record_with_computed_field_value_is_ignored(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    r = await client.post(
        f"/api/v1/records/{COLLECTION}",
        json={
            "first_name": "Foo",
            "last_name": "Bar",
            "price": 1.0,
            "quantity": 1,
            "full_name": "should be ignored",
        },
        headers=headers,
    )
    assert r.status_code == 201
    record_id = r.json()["id"]

    r = await client.get(
        f"/api/v1/records/{COLLECTION}/{record_id}", headers=headers
    )
    # Should be derived from expression, not the value we tried to write
    assert r.json()["full_name"] == "Foo Bar"


@pytest.mark.asyncio
async def test_update_record_with_computed_field_value_is_ignored(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    # Find Alice
    r = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": 'first_name = "Alice"'},
        headers=headers,
    )
    alice_id = r.json()["items"][0]["id"]

    r = await client.patch(
        f"/api/v1/records/{COLLECTION}/{alice_id}",
        json={"total_price": 9999},
        headers=headers,
    )
    assert r.status_code == 200

    r = await client.get(
        f"/api/v1/records/{COLLECTION}/{alice_id}", headers=headers
    )
    # Still Alice with price=10, quantity=3 → total_price=30
    assert r.json()["total_price"] == 30.0


# ── Filter by Computed Field ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_filter_by_computed_number_field(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    r = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": "total_price > 25"},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["full_name"] == "Alice Smith"


@pytest.mark.asyncio
async def test_filter_by_computed_text_field(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    r = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": 'full_name ~ "%Smith%"'},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_filter_computed_field_equality(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    r = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": 'full_name = "Bob Jones"'},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["first_name"] == "Bob"


@pytest.mark.asyncio
async def test_filter_combined_computed_and_regular_field(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    r = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"filter": 'total_price > 25 && last_name = "Smith"'},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["first_name"] == "Alice"


# ── Sort by Computed Field ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sort_by_computed_number_field_ascending(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    r = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"sort": "+total_price"},
        headers=headers,
    )
    assert r.status_code == 200
    items = r.json()["items"]
    # Alice has total=30, should be last
    assert items[-1]["first_name"] == "Alice"
    # All items have total_price ascending
    prices = [item["total_price"] for item in items]
    assert prices == sorted(prices)


@pytest.mark.asyncio
async def test_sort_by_computed_number_field_descending(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    r = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"sort": "-total_price"},
        headers=headers,
    )
    assert r.status_code == 200
    items = r.json()["items"]
    # Alice has total=30, should be first
    assert items[0]["first_name"] == "Alice"


@pytest.mark.asyncio
async def test_sort_by_computed_text_field(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    r = await client.get(
        f"/api/v1/records/{COLLECTION}",
        params={"sort": "+full_name"},
        headers=headers,
    )
    assert r.status_code == 200
    items = r.json()["items"]
    # Alphabetical: Alice Smith < Bob Jones < Carol Smith
    assert items[0]["full_name"] == "Alice Smith"


# ── Edge Cases ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_collection_with_no_computed_fields_works_normally(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    schema = [
        {"name": "title", "type": "text", "required": True},
        {"name": "count", "type": "number"},
    ]
    r = await client.post(
        "/api/v1/collections",
        json={"name": "no_computed_col", "label": "No Computed", "schema": schema},
        headers=headers,
    )
    assert r.status_code == 201

    await client.put(
        "/api/v1/collections/no_computed_col/rules",
        json={
            "list_rule": "",
            "view_rule": "",
            "create_rule": "",
            "update_rule": "",
            "delete_rule": "",
        },
        headers=headers,
    )

    r = await client.post(
        "/api/v1/records/no_computed_col",
        json={"title": "Test", "count": 1},
        headers=headers,
    )
    assert r.status_code == 201

    r = await client.get("/api/v1/records/no_computed_col", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 1

    await client.delete("/api/v1/collections/no_computed_col", headers=headers)


@pytest.mark.asyncio
async def test_computed_field_with_null_source_field(
    client: AsyncClient, superadmin_token
):
    headers = {"Authorization": f"Bearer {superadmin_token}"}
    # Create record with price=None (quantity still set)
    r = await client.post(
        f"/api/v1/records/{COLLECTION}",
        json={"first_name": "Null", "last_name": "Test", "quantity": 5},
        headers=headers,
    )
    assert r.status_code == 201
    record_id = r.json()["id"]

    r = await client.get(
        f"/api/v1/records/{COLLECTION}/{record_id}", headers=headers
    )
    assert r.status_code == 200
    # NULL * 5 = NULL in SQL — should not raise an error
    assert r.json()["total_price"] is None
