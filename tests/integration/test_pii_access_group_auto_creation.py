"""Integration tests for automatic pii_access group creation on registration."""

import uuid
import pytest
from sqlalchemy import select

from snackbase.infrastructure.persistence.models import GroupModel, UsersGroupsModel
from snackbase.domain.services.pii_masking_service import PIIMaskingService


class TestPIIAccessGroupAutoCreation:
    """Tests for automatic pii_access group creation on user registration."""

    @pytest.mark.asyncio
    async def test_registration_creates_pii_access_group(self, client, db_session):
        """Test that registration automatically creates pii_access group."""
        # Register new account
        payload = {
            "email": "newuser@example.com",
            "password": "StrongPassword123!",
            "account_name": "New Account"
        }
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201

        data = response.json()
        account_id = data["account"]["id"]
        user_id = data["user"]["id"]

        # Verify pii_access group exists for the account
        result = await db_session.execute(
            select(GroupModel).where(
                (GroupModel.account_id == account_id) &
                (GroupModel.name == PIIMaskingService.PII_ACCESS_GROUP)
            )
        )
        group = result.scalar_one_or_none()

        assert group is not None, "pii_access group should be created"
        assert group.name == PIIMaskingService.PII_ACCESS_GROUP
        assert group.description == "Users in this group can view unmasked PII data"
        assert group.account_id == account_id

    @pytest.mark.asyncio
    async def test_registered_user_added_to_pii_access_group(self, client, db_session):
        """Test that the registered user is added to the pii_access group."""
        # Register new account
        payload = {
            "email": "user2@example.com",
            "password": "StrongPassword123!",
            "account_name": "Test Account 2"
        }
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201

        data = response.json()
        account_id = data["account"]["id"]
        user_id = data["user"]["id"]

        # Get the pii_access group
        result = await db_session.execute(
            select(GroupModel).where(
                (GroupModel.account_id == account_id) &
                (GroupModel.name == PIIMaskingService.PII_ACCESS_GROUP)
            )
        )
        group = result.scalar_one()

        # Verify user is in the group via junction table
        result = await db_session.execute(
            select(UsersGroupsModel).where(
                (UsersGroupsModel.user_id == user_id) &
                (UsersGroupsModel.group_id == group.id)
            )
        )
        user_group = result.scalar_one_or_none()

        assert user_group is not None, "User should be added to pii_access group"

    @pytest.mark.asyncio
    async def test_duplicate_registration_creates_separate_groups(self, client, db_session):
        """Test that different accounts get separate pii_access groups."""
        # Register first account
        payload1 = {
            "email": "account1@example.com",
            "password": "StrongPassword123!",
            "account_name": "Account 1"
        }
        response1 = await client.post("/api/v1/auth/register", json=payload1)
        assert response1.status_code == 201
        account1_id = response1.json()["account"]["id"]

        # Register second account
        payload2 = {
            "email": "account2@example.com",
            "password": "StrongPassword123!",
            "account_name": "Account 2"
        }
        response2 = await client.post("/api/v1/auth/register", json=payload2)
        assert response2.status_code == 201
        account2_id = response2.json()["account"]["id"]

        # Verify each account has its own pii_access group
        result1 = await db_session.execute(
            select(GroupModel).where(
                (GroupModel.account_id == account1_id) &
                (GroupModel.name == PIIMaskingService.PII_ACCESS_GROUP)
            )
        )
        group1 = result1.scalar_one()

        result2 = await db_session.execute(
            select(GroupModel).where(
                (GroupModel.account_id == account2_id) &
                (GroupModel.name == PIIMaskingService.PII_ACCESS_GROUP)
            )
        )
        group2 = result2.scalar_one()

        # Groups should be different
        assert group1.id != group2.id
        assert group1.account_id != group2.account_id

    @pytest.mark.asyncio
    async def test_registration_failure_rolls_back_group_creation(self, client, db_session):
        """Test that if registration fails, pii_access group is not created."""
        # Try to register with invalid data (duplicate slug should cause conflict)
        # First register a valid account
        payload1 = {
            "email": "first@example.com",
            "password": "StrongPassword123!",
            "account_name": "First Account",
            "account_slug": "unique-slug-123"
        }
        response1 = await client.post("/api/v1/auth/register", json=payload1)
        assert response1.status_code == 201
        account1_id = response1.json()["account"]["id"]

        # Try to register with same slug (should fail)
        payload2 = {
            "email": "second@example.com",
            "password": "StrongPassword123!",
            "account_name": "Second Account",
            "account_slug": "unique-slug-123"  # Duplicate slug
        }
        response2 = await client.post("/api/v1/auth/register", json=payload2)
        assert response2.status_code == 409  # Conflict

        # Verify only the first account's group exists
        result = await db_session.execute(
            select(GroupModel).where(
                (GroupModel.account_id == account1_id) &
                (GroupModel.name == PIIMaskingService.PII_ACCESS_GROUP)
            )
        )
        assert result.scalar_one() is not None

        # Verify no extra pii_access groups were created
        result = await db_session.execute(
            select(GroupModel).where(
                GroupModel.name == PIIMaskingService.PII_ACCESS_GROUP
            )
        )
        groups = result.scalars().all()
        # Should only be one pii_access group (from first registration)
        assert len(groups) == 1
