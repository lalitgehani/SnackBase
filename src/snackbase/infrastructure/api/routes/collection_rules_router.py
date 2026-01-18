"""Collection rules API routes.

Provides endpoints for managing collection-level access rules.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.core.logging import get_logger
from snackbase.infrastructure.api.dependencies import SuperadminUser
from snackbase.infrastructure.persistence.database import get_db_session
from snackbase.infrastructure.api.schemas.collection_schemas import (
    CollectionRuleResponse,
    UpdateCollectionRulesRequest,
)
from snackbase.infrastructure.persistence.models import CollectionRuleModel
from snackbase.infrastructure.persistence.repositories import (
    CollectionRepository,
    CollectionRuleRepository,
)

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/{collection_name}/rules",
    response_model=CollectionRuleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get collection rules",
    description="Get access control rules for a collection. Only superadmins can access this endpoint.",
)
async def get_collection_rules(
    collection_name: str,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> CollectionRuleResponse:
    """Get collection rules by collection name.

    Args:
        collection_name: Name of the collection.
        current_user: Authenticated superadmin user.
        session: Database session.

    Returns:
        Collection rules.

    Raises:
        HTTPException: 404 if collection not found.
    """
    logger.info("Getting rules for collection", collection_name=collection_name)

    # Check if collection exists
    collection_repo = CollectionRepository(session)
    collection = await collection_repo.get_by_name(collection_name)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_name}' not found",
        )

    # Get rules
    rule_repo = CollectionRuleRepository(session)
    rules = await rule_repo.get_by_collection_id(collection.id)

    # If no rules exist, return default locked rules
    if not rules:
        logger.warning(
            "No rules found for collection, returning default locked rules",
            collection_name=collection_name,
        )
        # Create default rules (all locked)
        default_rules = CollectionRuleModel(
            id=str(uuid.uuid4()),
            collection_id=collection.id,
            list_rule=None,
            view_rule=None,
            create_rule=None,
            update_rule=None,
            delete_rule=None,
            list_fields="*",
            view_fields="*",
            create_fields="*",
            update_fields="*",
        )
        rules = await rule_repo.create(default_rules)
        await session.commit()

    return CollectionRuleResponse.model_validate(rules)


@router.put(
    "/{collection_name}/rules",
    response_model=CollectionRuleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update collection rules",
    description="Update access control rules for a collection. Supports partial updates. Only superadmins can access this endpoint.",
)
async def update_collection_rules(
    collection_name: str,
    request: UpdateCollectionRulesRequest,
    current_user: SuperadminUser,
    session: AsyncSession = Depends(get_db_session),
) -> CollectionRuleResponse:
    """Update collection rules by collection name.

    Supports partial updates - only provided fields will be updated.

    Args:
        collection_name: Name of the collection.
        request: Updated rule values.
        current_user: Authenticated superadmin user.
        session: Database session.

    Returns:
        Updated collection rules.

    Raises:
        HTTPException: 404 if collection not found, 400 if validation fails.
    """
    logger.info("Updating rules for collection", collection_name=collection_name)

    # Check if collection exists
    collection_repo = CollectionRepository(session)
    collection = await collection_repo.get_by_name(collection_name)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_name}' not found",
        )

    # Get existing rules
    rule_repo = CollectionRuleRepository(session)
    rules = await rule_repo.get_by_collection_id(collection.id)

    # If no rules exist, create default ones first
    if not rules:
        logger.info(
            "No rules found for collection, creating default rules",
            collection_name=collection_name,
        )
        rules = CollectionRuleModel(
            id=str(uuid.uuid4()),
            collection_id=collection.id,
            list_rule=None,
            view_rule=None,
            create_rule=None,
            update_rule=None,
            delete_rule=None,
            list_fields="*",
            view_fields="*",
            create_fields="*",
            update_fields="*",
        )
        rules = await rule_repo.create(rules)

    # Update rules (partial update - only update provided fields)
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rules, field, value)

    # Save changes
    rules = await rule_repo.update(rules)
    await session.commit()

    logger.info("Successfully updated collection rules", collection_name=collection_name)

    return CollectionRuleResponse.model_validate(rules)
