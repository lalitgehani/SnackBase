"""Pydantic schemas for Macro API."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MacroBase(BaseModel):
    """Base schema for Macro."""

    name: str = Field(..., description="Unique name of the macro", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Description of the macro")
    sql_query: str = Field(..., description="The SQL SELECT query")
    parameters: List[str] = Field(default_factory=list, description="List of parameter names")
    
    model_config = ConfigDict(from_attributes=True)
    # ... (rest of class) will be kept by context matching logic? No.
    # I should target specific lines.


    @field_validator("sql_query")
    def validate_sql_query(cls, v: str) -> str:
        """Validate that the query is a SELECT statement."""
        v_stripped = v.strip().upper()
        if not v_stripped.startswith("SELECT"):
            raise ValueError("Macro query must be a SELECT statement")
        
        forbidden_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "GRANT", "REVOKE"]
        for keyword in forbidden_keywords:
            # Simple check for forbidden keywords. 
            # In a real-world scenario, a proper SQL parser would be safer.
            # We assume word boundaries or simple containment for now as a strict check.
            # Using token checking would be better but this covers basic injection attempts in macro definitions.
            if f" {keyword} " in f" {v_stripped} " or f"\n{keyword} " in v_stripped or f" {keyword}\n" in v_stripped:
                 raise ValueError(f"Macro query cannot contain forbidden keyword: {keyword}")

        return v

    @field_validator("name")
    def validate_name(cls, v: str) -> str:
        """Validate macro name format."""
        if not v.isidentifier():
             raise ValueError("Macro name must be a valid identifier (alphanumeric and underscore)")
        return v


class MacroCreate(MacroBase):
    """Schema for creating a macro."""
    pass


class MacroUpdate(BaseModel):
    """Schema for updating a macro."""

    name: Optional[str] = Field(None, description="Unique name of the macro", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Description of the macro")
    sql_query: Optional[str] = Field(None, description="The SQL SELECT query")
    parameters: Optional[List[str]] = Field(None, description="List of parameter names")

    @field_validator("sql_query")
    def validate_sql_query(cls, v: str | None) -> str | None:
        """Validate that the query is a SELECT statement."""
        if v is None:
            return v
        
        v_stripped = v.strip().upper()
        if not v_stripped.startswith("SELECT"):
            raise ValueError("Macro query must be a SELECT statement")
        
        forbidden_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "GRANT", "REVOKE"]
        for keyword in forbidden_keywords:
             if f" {keyword} " in f" {v_stripped} " or f"\n{keyword} " in v_stripped or f" {keyword}\n" in v_stripped:
                 raise ValueError(f"Macro query cannot contain forbidden keyword: {keyword}")
        return v

    @field_validator("name")
    def validate_name(cls, v: str | None) -> str | None:
        """Validate macro name format."""
        if v is None:
            return v
        if not v.isidentifier():
             raise ValueError("Macro name must be a valid identifier (alphanumeric and underscore)")
        return v


class MacroResponse(MacroBase):
    """Schema for macro response."""

    id: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("parameters", mode="before")
    def parse_parameters(cls, v):
        """Parse JSON string parameters to list if necessary."""
        import json
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v


class MacroTestRequest(BaseModel):
    """Schema for testing a macro."""

    parameters: List[str] = Field(
        default_factory=list,
        description="Array of test values to pass to the macro"
    )


class MacroTestResponse(BaseModel):
    """Schema for macro test response."""

    result: Optional[str] = Field(None, description="The result of the macro execution")
    execution_time: float = Field(..., description="Execution time in milliseconds")
    rows_affected: int = Field(0, description="Number of rows affected (always 0 for SELECT)")
