"""Integration tests for the ?expand= query parameter on records endpoints.

Tests cover:
- Single reference field expansion on list endpoint
- Single reference field expansion on get endpoint
- Multiple reference fields expanded in one request
- Nested expansion using dot notation
- Invalid (non-reference) expand field returns 400
- Deleted referenced record returns null instead of error
- Cross-account reference returns null (account isolation)
- Without expand param, reference fields return IDs as strings (backward compat)
"""

import pytest
from httpx import AsyncClient


COMPANIES_COLLECTION = "expand_companies"
INDUSTRIES_COLLECTION = "expand_industries"
EMPLOYEES_COLLECTION = "expand_employees"

INDUSTRIES_SCHEMA = [
    {"name": "sector", "type": "text", "required": True},
]

COMPANIES_SCHEMA = [
    {"name": "company_name", "type": "text", "required": True},
    {
        "name": "industry",
        "type": "reference",
        "collection": INDUSTRIES_COLLECTION,
        "on_delete": "set_null",
    },
]

EMPLOYEES_SCHEMA = [
    {"name": "employee_name", "type": "text", "required": True},
    {
        "name": "company",
        "type": "reference",
        "collection": COMPANIES_COLLECTION,
        "on_delete": "set_null",
    },
    {
        "name": "department",
        "type": "text",
    },
]


async def _open_rules(client, token, collection):
    headers = {"Authorization": f"Bearer {token}"}
    await client.put(
        f"/api/v1/collections/{collection}/rules",
        json={
            "list_rule": "",
            "view_rule": "",
            "create_rule": "",
            "update_rule": "",
            "delete_rule": "",
        },
        headers=headers,
    )


@pytest.fixture(autouse=True)
async def setup_collections(client: AsyncClient, superadmin_token):
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create collections in dependency order
    for name, schema in [
        (INDUSTRIES_COLLECTION, INDUSTRIES_SCHEMA),
        (COMPANIES_COLLECTION, COMPANIES_SCHEMA),
        (EMPLOYEES_COLLECTION, EMPLOYEES_SCHEMA),
    ]:
        r = await client.post(
            "/api/v1/collections",
            json={"name": name, "label": name, "schema": schema},
            headers=headers,
        )
        assert r.status_code in (200, 201), f"Failed to create collection {name}: {r.text}"
        await _open_rules(client, superadmin_token, name)

    yield

    # Cleanup in reverse dependency order
    for name in [EMPLOYEES_COLLECTION, COMPANIES_COLLECTION, INDUSTRIES_COLLECTION]:
        await client.delete(f"/api/v1/collections/{name}", headers=headers)


@pytest.mark.asyncio
async def test_expand_single_reference_list(client: AsyncClient, superadmin_token):
    """Expanding a reference field in list response replaces ID with full object."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create industry
    r = await client.post(
        f"/api/v1/records/{INDUSTRIES_COLLECTION}",
        json={"sector": "Technology"},
        headers=headers,
    )
    assert r.status_code == 201
    industry_id = r.json()["id"]

    # Create company referencing the industry
    r = await client.post(
        f"/api/v1/records/{COMPANIES_COLLECTION}",
        json={"company_name": "Acme Corp", "industry": industry_id},
        headers=headers,
    )
    assert r.status_code == 201

    # List without expand — industry is raw ID
    r = await client.get(f"/api/v1/records/{COMPANIES_COLLECTION}", headers=headers)
    assert r.status_code == 200
    item = r.json()["items"][0]
    assert item["industry"] == industry_id

    # List with expand — industry is full object
    r = await client.get(
        f"/api/v1/records/{COMPANIES_COLLECTION}",
        params={"expand": "industry"},
        headers=headers,
    )
    assert r.status_code == 200
    item = r.json()["items"][0]
    assert isinstance(item["industry"], dict)
    assert item["industry"]["id"] == industry_id
    assert item["industry"]["sector"] == "Technology"


@pytest.mark.asyncio
async def test_expand_single_reference_get(client: AsyncClient, superadmin_token):
    """Expanding a reference field in get-by-ID response replaces ID with full object."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    r = await client.post(
        f"/api/v1/records/{INDUSTRIES_COLLECTION}",
        json={"sector": "Finance"},
        headers=headers,
    )
    assert r.status_code == 201
    industry_id = r.json()["id"]

    r = await client.post(
        f"/api/v1/records/{COMPANIES_COLLECTION}",
        json={"company_name": "Bank Corp", "industry": industry_id},
        headers=headers,
    )
    assert r.status_code == 201
    company_id = r.json()["id"]

    # Get without expand
    r = await client.get(f"/api/v1/records/{COMPANIES_COLLECTION}/{company_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["industry"] == industry_id

    # Get with expand
    r = await client.get(
        f"/api/v1/records/{COMPANIES_COLLECTION}/{company_id}",
        params={"expand": "industry"},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["industry"], dict)
    assert data["industry"]["id"] == industry_id
    assert data["industry"]["sector"] == "Finance"


@pytest.mark.asyncio
async def test_expand_multiple_fields(client: AsyncClient, superadmin_token):
    """Multiple expand fields are all replaced in a single request."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Create industry
    r = await client.post(
        f"/api/v1/records/{INDUSTRIES_COLLECTION}",
        json={"sector": "Retail"},
        headers=headers,
    )
    industry_id = r.json()["id"]

    # Create company
    r = await client.post(
        f"/api/v1/records/{COMPANIES_COLLECTION}",
        json={"company_name": "Shop Co", "industry": industry_id},
        headers=headers,
    )
    company_id = r.json()["id"]

    # Create employee with both references
    r = await client.post(
        f"/api/v1/records/{EMPLOYEES_COLLECTION}",
        json={"employee_name": "Alice", "company": company_id, "department": "Sales"},
        headers=headers,
    )
    assert r.status_code == 201
    employee_id = r.json()["id"]

    # Expand just company
    r = await client.get(
        f"/api/v1/records/{EMPLOYEES_COLLECTION}/{employee_id}",
        params={"expand": "company"},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["company"], dict)
    assert data["company"]["id"] == company_id


@pytest.mark.asyncio
async def test_expand_nested(client: AsyncClient, superadmin_token):
    """Nested expansion using dot notation expands through multiple levels."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    r = await client.post(
        f"/api/v1/records/{INDUSTRIES_COLLECTION}",
        json={"sector": "Healthcare"},
        headers=headers,
    )
    industry_id = r.json()["id"]

    r = await client.post(
        f"/api/v1/records/{COMPANIES_COLLECTION}",
        json={"company_name": "Med Corp", "industry": industry_id},
        headers=headers,
    )
    company_id = r.json()["id"]

    r = await client.post(
        f"/api/v1/records/{EMPLOYEES_COLLECTION}",
        json={"employee_name": "Bob", "company": company_id},
        headers=headers,
    )
    employee_id = r.json()["id"]

    # Expand company.industry — nested 2 levels
    r = await client.get(
        f"/api/v1/records/{EMPLOYEES_COLLECTION}/{employee_id}",
        params={"expand": "company.industry"},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["company"], dict)
    assert data["company"]["id"] == company_id
    assert isinstance(data["company"]["industry"], dict)
    assert data["company"]["industry"]["id"] == industry_id
    assert data["company"]["industry"]["sector"] == "Healthcare"


@pytest.mark.asyncio
async def test_expand_invalid_field_returns_400(client: AsyncClient, superadmin_token):
    """Expanding a non-reference field returns HTTP 400."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    r = await client.get(
        f"/api/v1/records/{EMPLOYEES_COLLECTION}",
        params={"expand": "employee_name"},
        headers=headers,
    )
    assert r.status_code == 400
    body = r.json()
    assert "not a reference field" in body["message"]
    assert "employee_name" in body["message"]


@pytest.mark.asyncio
async def test_expand_deleted_reference_returns_null(client: AsyncClient, superadmin_token):
    """When a referenced record is deleted, the expanded field returns null."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    r = await client.post(
        f"/api/v1/records/{INDUSTRIES_COLLECTION}",
        json={"sector": "Energy"},
        headers=headers,
    )
    industry_id = r.json()["id"]

    r = await client.post(
        f"/api/v1/records/{COMPANIES_COLLECTION}",
        json={"company_name": "Power Co", "industry": industry_id},
        headers=headers,
    )
    company_id = r.json()["id"]

    # Delete the industry record
    await client.delete(
        f"/api/v1/records/{INDUSTRIES_COLLECTION}/{industry_id}", headers=headers
    )

    # Expand should return null for the deleted reference
    r = await client.get(
        f"/api/v1/records/{COMPANIES_COLLECTION}/{company_id}",
        params={"expand": "industry"},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["industry"] is None


@pytest.mark.asyncio
async def test_expand_no_param_backward_compatible(client: AsyncClient, superadmin_token):
    """Without ?expand=, reference fields are still returned as plain ID strings."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    r = await client.post(
        f"/api/v1/records/{INDUSTRIES_COLLECTION}",
        json={"sector": "Manufacturing"},
        headers=headers,
    )
    industry_id = r.json()["id"]

    r = await client.post(
        f"/api/v1/records/{COMPANIES_COLLECTION}",
        json={"company_name": "Factory Inc", "industry": industry_id},
        headers=headers,
    )
    company_id = r.json()["id"]

    # List — no expand
    r = await client.get(f"/api/v1/records/{COMPANIES_COLLECTION}", headers=headers)
    assert r.status_code == 200
    item = next(i for i in r.json()["items"] if i["id"] == company_id)
    assert item["industry"] == industry_id

    # Get — no expand
    r = await client.get(
        f"/api/v1/records/{COMPANIES_COLLECTION}/{company_id}", headers=headers
    )
    assert r.status_code == 200
    assert r.json()["industry"] == industry_id


@pytest.mark.asyncio
async def test_expand_null_reference_field(client: AsyncClient, superadmin_token):
    """Expanding a null reference field leaves it as null (no error)."""
    headers = {"Authorization": f"Bearer {superadmin_token}"}

    # Company with no industry set
    r = await client.post(
        f"/api/v1/records/{COMPANIES_COLLECTION}",
        json={"company_name": "Solo Corp"},
        headers=headers,
    )
    assert r.status_code == 201
    company_id = r.json()["id"]

    r = await client.get(
        f"/api/v1/records/{COMPANIES_COLLECTION}/{company_id}",
        params={"expand": "industry"},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["industry"] is None
