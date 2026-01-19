import pytest
from unittest.mock import AsyncMock, MagicMock
from snackbase.core.macros.expander import MacroExpander

@pytest.mark.asyncio
async def test_expand_no_macros():
    expander = MacroExpander()
    expr = "status = 'active'"
    result = await expander.expand(expr)
    assert result == expr

@pytest.mark.asyncio
async def test_expand_builtin_owns_record():
    expander = MacroExpander()
    # Default
    result = await expander.expand("@owns_record")
    assert result == "(created_by = @request.auth.id)"
    # With field
    result = await expander.expand("@owns_record(owner_id)")
    assert result == "(owner_id = @request.auth.id)"

@pytest.mark.asyncio
async def test_expand_builtin_has_role():
    expander = MacroExpander()
    expr = "@has_role('admin')"
    result = await expander.expand(expr)
    assert result == "(@request.auth.role = 'admin')"

@pytest.mark.asyncio
async def test_expand_builtin_is_public():
    expander = MacroExpander()
    expr = "@is_public"
    result = await expander.expand(expr)
    assert result == "(public = true)"

@pytest.mark.asyncio
async def test_expand_combined_macros():
    expander = MacroExpander()
    expr = "@has_role('admin') || @owns_record"
    result = await expander.expand(expr)
    assert result == "(@request.auth.role = 'admin') || (created_by = @request.auth.id)"

@pytest.mark.asyncio
async def test_expand_db_macro():
    mock_session = AsyncMock()
    expander = MacroExpander(mock_session)
    
    mock_macro = MagicMock()
    mock_macro.name = "my_custom_macro"
    mock_macro.sql_query = "category = 'special'"
    
    expander.macro_repo.get_by_name = AsyncMock(return_value=mock_macro)
    
    expr = "@my_custom_macro"
    result = await expander.expand(expr)
    assert result == "(category = 'special')"
    expander.macro_repo.get_by_name.assert_called_with("my_custom_macro")

@pytest.mark.asyncio
async def test_expand_parameterized_db_macro():
    mock_session = AsyncMock()
    expander = MacroExpander(mock_session)
    
    mock_macro = MagicMock()
    mock_macro.name = "has_status"
    mock_macro.sql_query = "status = $1"
    
    expander.macro_repo.get_by_name = AsyncMock(return_value=mock_macro)
    
    expr = "@has_status('active')"
    result = await expander.expand(expr)
    assert result == "(status = 'active')"

@pytest.mark.asyncio
async def test_expand_nested_macros():
    mock_session = AsyncMock()
    expander = MacroExpander(mock_session)
    
    def side_effect(name):
        if name == "inner":
            m = MagicMock()
            m.sql_query = "a = 1"
            return m
        if name == "outer":
            m = MagicMock()
            m.sql_query = "@inner && b = 2"
            return m
        return None
        
    expander.macro_repo.get_by_name = AsyncMock(side_effect=side_effect)
    
    expr = "@outer"
    result = await expander.expand(expr)
    assert result == "((a = 1) && b = 2)"

@pytest.mark.asyncio
async def test_expand_recursion_error():
    mock_session = AsyncMock()
    expander = MacroExpander(mock_session)
    
    mock_macro = MagicMock()
    mock_macro.sql_query = "@loop"
    expander.macro_repo.get_by_name = AsyncMock(return_value=mock_macro)
    
    with pytest.raises(RecursionError):
        await expander.expand("@loop")
