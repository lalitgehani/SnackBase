"""Unit tests for field-level access control in authorization middleware."""

import pytest
from fastapi import HTTPException

from snackbase.infrastructure.api.middleware.authorization import (
    SYSTEM_FIELDS,
    apply_field_filter,
    validate_request_fields,
)


class TestApplyFieldFilter:
    """Tests for apply_field_filter function."""

    def test_wildcard_allows_all_fields(self):
        """Test that wildcard '*' allows all fields."""
        data = {"name": "John", "email": "john@example.com", "salary": 50000}
        result = apply_field_filter(data, "*")
        assert result == data

    def test_specific_fields_filtered_for_response(self):
        """Test that specific fields are filtered for responses."""
        data = {
            "id": "123",
            "name": "John",
            "email": "john@example.com",
            "salary": 50000,
            "created_at": "2024-01-01",
        }
        allowed_fields = ["name", "email"]
        result = apply_field_filter(data, allowed_fields, is_request=False)
        
        # Should include allowed fields + system fields
        assert "name" in result
        assert "email" in result
        assert "id" in result  # System field always included in responses
        assert "created_at" in result  # System field always included
        assert "salary" not in result  # Not in allowed fields

    def test_specific_fields_filtered_for_request(self):
        """Test that specific fields are filtered for requests."""
        data = {
            "name": "John",
            "email": "john@example.com",
            "salary": 50000,
        }
        allowed_fields = ["name", "email"]
        result = apply_field_filter(data, allowed_fields, is_request=True)
        
        # Should only include allowed fields (no system fields for requests)
        assert "name" in result
        assert "email" in result
        assert "salary" not in result

    def test_response_includes_system_fields(self):
        """Test that system fields are always included in responses."""
        data = {
            "id": "123",
            "name": "John",
            "account_id": "ACC123",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-02",
        }
        allowed_fields = ["name"]
        result = apply_field_filter(data, allowed_fields, is_request=False)
        
        # All system fields should be present
        for field in SYSTEM_FIELDS:
            if field in data:
                assert field in result
        assert "name" in result

    def test_request_excludes_system_fields_from_allowed(self):
        """Test that system fields are not automatically added for requests."""
        data = {"name": "John", "id": "123"}
        allowed_fields = ["name"]
        result = apply_field_filter(data, allowed_fields, is_request=True)
        
        # Should only have allowed fields, not system fields
        assert result == {"name": "John"}
        assert "id" not in result

    def test_empty_allowed_fields_list(self):
        """Test filtering with empty allowed fields list."""
        data = {"name": "John", "email": "john@example.com"}
        allowed_fields = []
        result = apply_field_filter(data, allowed_fields, is_request=False)
        
        # Should only include system fields
        assert "name" not in result
        assert "email" not in result

    def test_string_allowed_fields_fallback(self):
        """Test that non-wildcard string is handled gracefully."""
        data = {"name": "John", "email": "john@example.com"}
        allowed_fields = "invalid"  # Not "*" but still a string
        result = apply_field_filter(data, allowed_fields)
        
        # Should return data unchanged as fallback
        assert result == data


class TestValidateRequestFields:
    """Tests for validate_request_fields function."""

    def test_valid_request_passes(self):
        """Test that valid request with allowed fields passes."""
        data = {"name": "John", "email": "john@example.com"}
        allowed_fields = ["name", "email", "department"]
        
        # Should not raise exception
        validate_request_fields(data, allowed_fields, "create")

    def test_wildcard_allows_all_non_system_fields(self):
        """Test that wildcard allows all fields except system fields."""
        data = {"name": "John", "email": "john@example.com", "salary": 50000}
        
        # Should not raise exception
        validate_request_fields(data, "*", "create")

    def test_unauthorized_field_raises_error(self):
        """Test that unauthorized field in request raises HTTPException."""
        data = {"name": "John", "salary": 50000}
        allowed_fields = ["name", "email"]
        
        with pytest.raises(HTTPException) as exc_info:
            validate_request_fields(data, allowed_fields, "create")
        
        assert exc_info.value.status_code == 422
        assert "salary" in str(exc_info.value.detail)
        assert exc_info.value.detail["field_type"] == "restricted"
        assert "salary" in exc_info.value.detail["unauthorized_fields"]

    def test_system_field_in_request_raises_error(self):
        """Test that system field in request raises HTTPException."""
        data = {"name": "John", "id": "custom-id"}
        allowed_fields = ["name", "email"]
        
        with pytest.raises(HTTPException) as exc_info:
            validate_request_fields(data, allowed_fields, "create")
        
        assert exc_info.value.status_code == 422
        assert "id" in str(exc_info.value.detail)
        assert exc_info.value.detail["field_type"] == "system"
        assert "id" in exc_info.value.detail["unauthorized_fields"]

    def test_system_field_with_wildcard_raises_error(self):
        """Test that system field raises error even with wildcard permission."""
        data = {"name": "John", "created_at": "2024-01-01"}
        
        with pytest.raises(HTTPException) as exc_info:
            validate_request_fields(data, "*", "update")
        
        assert exc_info.value.status_code == 422
        assert "created_at" in str(exc_info.value.detail)
        assert exc_info.value.detail["field_type"] == "system"

    def test_multiple_unauthorized_fields(self):
        """Test error message with multiple unauthorized fields."""
        data = {"name": "John", "salary": 50000, "ssn": "123-45-6789"}
        allowed_fields = ["name", "email"]
        
        with pytest.raises(HTTPException) as exc_info:
            validate_request_fields(data, allowed_fields, "create")
        
        assert exc_info.value.status_code == 422
        unauthorized = exc_info.value.detail["unauthorized_fields"]
        assert "salary" in unauthorized
        assert "ssn" in unauthorized
        assert len(unauthorized) == 2

    def test_error_message_includes_operation(self):
        """Test that error message includes the operation type."""
        data = {"name": "John", "salary": 50000}
        allowed_fields = ["name"]
        
        with pytest.raises(HTTPException) as exc_info:
            validate_request_fields(data, allowed_fields, "update")
        
        assert "update" in exc_info.value.detail["message"]

    def test_error_includes_allowed_fields(self):
        """Test that error detail includes list of allowed fields."""
        data = {"name": "John", "salary": 50000}
        allowed_fields = ["name", "email", "department"]
        
        with pytest.raises(HTTPException) as exc_info:
            validate_request_fields(data, allowed_fields, "create")
        
        assert exc_info.value.detail["allowed_fields"] == sorted(allowed_fields)

    def test_empty_data_passes(self):
        """Test that empty data passes validation."""
        data = {}
        allowed_fields = ["name", "email"]
        
        # Should not raise exception
        validate_request_fields(data, allowed_fields, "create")

    def test_string_allowed_fields_fallback(self):
        """Test that non-wildcard string is handled gracefully."""
        data = {"name": "John"}
        allowed_fields = "invalid"  # Not "*" but still a string
        
        # Should not raise exception (fallback behavior)
        validate_request_fields(data, allowed_fields, "create")
