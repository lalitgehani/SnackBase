"""Unit tests for MacroRepository."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from snackbase.infrastructure.persistence.models.macro import MacroModel
from snackbase.infrastructure.persistence.repositories.macro_repository import (
    MacroRepository,
)


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def macro_repository(mock_session):
    """Create a MacroRepository fixture."""
    return MacroRepository(mock_session)


@pytest.mark.asyncio
async def test_create_macro(macro_repository, mock_session):
    """Test creating a macro."""
    macro = await macro_repository.create(
        name="test_macro",
        sql_query="SELECT 1",
        parameters=["param1"],
        description="Test macro",
        created_by="user1",
    )

    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once()
    
    assert macro.name == "test_macro"
    assert macro.sql_query == "SELECT 1"
    assert macro.parameters == '["param1"]'
    assert macro.description == "Test macro"
    assert macro.created_by == "user1"


@pytest.mark.asyncio
async def test_create_macro_duplicate_name(macro_repository, mock_session):
    """Test creating a macro with a duplicate name."""
    mock_session.commit.side_effect = IntegrityError(None, None, Exception("Duplicate"))

    with pytest.raises(IntegrityError):
        await macro_repository.create(
            name="test_macro_dup",
            sql_query="SELECT 1",
        )


@pytest.mark.asyncio
async def test_get_by_id(macro_repository, mock_session):
    """Test getting a macro by ID."""
    expected_macro = MacroModel(id=1, name="test")
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = expected_macro
    mock_session.execute.return_value = mock_result

    found = await macro_repository.get_by_id(1)
    
    mock_session.execute.assert_called_once()
    assert found == expected_macro


@pytest.mark.asyncio
async def test_get_by_id_not_found(macro_repository, mock_session):
    """Test getting a non-existent macro by ID."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    found = await macro_repository.get_by_id(99999)
    assert found is None


@pytest.mark.asyncio
async def test_get_by_name(macro_repository, mock_session):
    """Test getting a macro by name."""
    expected_macro = MacroModel(id=1, name="test_macro_name")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = expected_macro
    mock_session.execute.return_value = mock_result

    found = await macro_repository.get_by_name("test_macro_name")
    assert found == expected_macro


@pytest.mark.asyncio
async def test_list_all(macro_repository, mock_session):
    """Test listing macros."""
    expected_macros = [
        MacroModel(id=1, name="macro_1"),
        MacroModel(id=2, name="macro_2"),
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = expected_macros
    mock_session.execute.return_value = mock_result

    macros = await macro_repository.list_all()
    
    assert len(macros) == 2
    assert macros == expected_macros


@pytest.mark.asyncio
async def test_update_macro(macro_repository, mock_session):
    """Test updating a macro."""
    existing_macro = MacroModel(id=1, name="old", sql_query="SELECT 1")
    
    # Mock get_by_id to return existing macro
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_macro
    mock_session.execute.return_value = mock_result

    updated = await macro_repository.update(
        macro_id=1,
        name="updated_macro",
        sql_query="SELECT 2",
        parameters=["p1"],
        description="Updated",
    )

    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once()
    
    assert updated.name == "updated_macro"
    assert updated.sql_query == "SELECT 2"
    assert updated.parameters == '["p1"]'
    assert updated.description == "Updated"


@pytest.mark.asyncio
async def test_update_macro_not_found(macro_repository, mock_session):
    """Test updating a non-existent macro."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    updated = await macro_repository.update(
        macro_id=99999,
        name="fail",
    )
    assert updated is None


@pytest.mark.asyncio
async def test_delete_macro(macro_repository, mock_session):
    """Test deleting a macro."""
    existing_macro = MacroModel(id=1, name="test")
    
    # Mock get_by_id
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_macro
    mock_session.execute.return_value = mock_result

    deleted = await macro_repository.delete(1)
    
    mock_session.delete.assert_called_once_with(existing_macro)
    mock_session.commit.assert_called_once()
    assert deleted is True


@pytest.mark.asyncio
async def test_delete_macro_not_found(macro_repository, mock_session):
    """Test deleting a non-existent macro."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    deleted = await macro_repository.delete(99999)
    assert deleted is False
