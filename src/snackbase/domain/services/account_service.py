"""Account service for business logic.

Provides methods for account management operations including
creation, updates, deletion, and listing with business rules.
"""

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.domain.services.account_code_generator import AccountCodeGenerator
from snackbase.infrastructure.persistence.models import AccountModel
from snackbase.infrastructure.persistence.repositories import AccountRepository


class AccountService:
    """Service for account management business logic."""

    SYSTEM_ACCOUNT_ID = "00000000-0000-0000-0000-000000000000"  # Nil UUID
    SYSTEM_ACCOUNT_CODE = "SY0000"  # Human-readable code

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the account service.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session
        self.account_repo = AccountRepository(session)

    async def create_account(self, name: str, slug: str | None = None) -> AccountModel:
        """Create a new account with auto-generated ID and optional slug.

        Args:
            name: Account name.
            slug: Optional URL-friendly slug (auto-generated if not provided).

        Returns:
            Created account model.

        Raises:
            ValueError: If slug already exists or is invalid.
        """
        # Generate UUID for account ID
        account_id = str(uuid.uuid4())

        # Generate account code
        existing_codes = await self.account_repo.get_all_account_codes()
        account_code = AccountCodeGenerator.generate(existing_codes)

        # Generate or validate slug
        if slug:
            # Validate slug format
            if not re.match(r"^[a-z0-9-]+$", slug):
                raise ValueError(
                    "Slug must contain only lowercase letters, numbers, and hyphens"
                )
            # Check if slug already exists
            if await self.account_repo.slug_exists(slug):
                raise ValueError(f"Slug '{slug}' already exists")
        else:
            # Auto-generate slug from name
            slug = self._generate_slug_from_name(name)
            # Ensure uniqueness
            base_slug = slug
            counter = 1
            while await self.account_repo.slug_exists(slug):
                slug = f"{base_slug}-{counter}"
                counter += 1

        # Create account
        now = datetime.now(timezone.utc)
        account = AccountModel(
            id=account_id,
            account_code=account_code,
            slug=slug,
            name=name,
            created_at=now,
            updated_at=now,
        )

        return await self.account_repo.create(account)

    async def update_account(self, account_id: str, name: str) -> AccountModel:
        """Update an account's name.

        Args:
            account_id: Account ID.
            name: New account name.

        Returns:
            Updated account model.

        Raises:
            ValueError: If account not found.
        """
        account = await self.account_repo.get_by_id(account_id)
        if not account:
            raise ValueError(f"Account '{account_id}' not found")

        account.name = name
        account.updated_at = datetime.now(timezone.utc)

        return await self.account_repo.update(account)

    async def delete_account(self, account_id: str) -> None:
        """Delete an account.

        Args:
            account_id: Account ID.

        Raises:
            ValueError: If account not found or is system account.
        """
        if account_id == self.SYSTEM_ACCOUNT_ID:
            raise ValueError("Cannot delete system account")

        account = await self.account_repo.get_by_id(account_id)
        if not account:
            raise ValueError(f"Account '{account_id}' not found")

        await self.account_repo.delete(account)

    async def get_account_with_details(self, account_id: str) -> tuple[AccountModel, int]:
        """Get account with user count.

        Args:
            account_id: Account ID.

        Returns:
            Tuple of (account model, user count).

        Raises:
            ValueError: If account not found.
        """
        account = await self.account_repo.get_by_id(account_id)
        if not account:
            raise ValueError(f"Account '{account_id}' not found")

        user_count = await self.account_repo.get_user_count(account_id)

        return account, user_count

    async def list_accounts(
        self,
        page: int = 1,
        page_size: int = 25,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        search: str | None = None,
    ) -> tuple[list[tuple[AccountModel, int]], int]:
        """List accounts with pagination and search.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            sort_by: Column to sort by.
            sort_order: Sort order (asc or desc).
            search: Optional search query.

        Returns:
            Tuple of (list of (account, user_count) tuples, total count).
        """
        accounts, total = await self.account_repo.get_all_paginated(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            search_query=search,
        )

        # Get user counts for each account
        accounts_with_counts = []
        for account in accounts:
            user_count = await self.account_repo.get_user_count(account.id)
            accounts_with_counts.append((account, user_count))

        return accounts_with_counts, total

    def _generate_slug_from_name(self, name: str) -> str:
        """Generate a URL-friendly slug from account name.

        Args:
            name: Account name.

        Returns:
            Generated slug.
        """
        # Convert to lowercase and replace spaces with hyphens
        slug = name.lower().strip()
        slug = re.sub(r"[^a-z0-9-]+", "-", slug)
        slug = re.sub(r"-+", "-", slug)  # Remove consecutive hyphens
        slug = slug.strip("-")  # Remove leading/trailing hyphens

        # Ensure slug is within length limits
        if len(slug) < 3:
            slug = f"account-{slug}"
        if len(slug) > 32:
            slug = slug[:32].rstrip("-")

        return slug
