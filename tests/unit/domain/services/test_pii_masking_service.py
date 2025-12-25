"""Unit tests for PII masking service."""

import pytest

from snackbase.domain.services import PIIMaskingService


class TestPIIMaskingService:
    """Tests for PIIMaskingService."""

    def test_should_mask_for_user_with_pii_access(self):
        """Test that users with pii_access group should not have data masked."""
        user_groups = ["pii_access", "admin"]
        assert PIIMaskingService.should_mask_for_user(user_groups) is False

    def test_should_mask_for_user_without_pii_access(self):
        """Test that users without pii_access group should have data masked."""
        user_groups = ["admin", "user"]
        assert PIIMaskingService.should_mask_for_user(user_groups) is True

    def test_should_mask_for_user_with_empty_groups(self):
        """Test that users with no groups should have data masked."""
        user_groups = []
        assert PIIMaskingService.should_mask_for_user(user_groups) is True

    def test_mask_email_standard(self):
        """Test masking standard email address."""
        result = PIIMaskingService.mask_email("john.doe@example.com")
        assert result == "j***@example.com"

    def test_mask_email_single_char_local(self):
        """Test masking email with single character local part."""
        result = PIIMaskingService.mask_email("a@example.com")
        assert result == "a***@example.com"

    def test_mask_email_long_local(self):
        """Test masking email with long local part."""
        result = PIIMaskingService.mask_email("verylongemailaddress@example.com")
        assert result == "v***@example.com"

    def test_mask_email_invalid(self):
        """Test masking invalid email returns original."""
        result = PIIMaskingService.mask_email("notanemail")
        assert result == "notanemail"

    def test_mask_email_empty(self):
        """Test masking empty email returns empty."""
        result = PIIMaskingService.mask_email("")
        assert result == ""

    def test_mask_ssn_with_dashes(self):
        """Test masking SSN with dashes."""
        result = PIIMaskingService.mask_ssn("123-45-6789")
        assert result == "***-**-****"

    def test_mask_ssn_without_dashes(self):
        """Test masking SSN without dashes."""
        result = PIIMaskingService.mask_ssn("123456789")
        assert result == "***-**-****"

    def test_mask_ssn_non_standard_format(self):
        """Test masking SSN with non-standard format."""
        result = PIIMaskingService.mask_ssn("12-345-6789")
        # Should mask all digits
        assert "*" in result
        assert "1" not in result
        assert "2" not in result

    def test_mask_ssn_empty(self):
        """Test masking empty SSN returns empty."""
        result = PIIMaskingService.mask_ssn("")
        assert result == ""

    def test_mask_phone_with_country_code(self):
        """Test masking phone with country code."""
        result = PIIMaskingService.mask_phone("+1-555-123-4567")
        assert result == "+1-***-***-4567"

    def test_mask_phone_without_country_code(self):
        """Test masking phone without country code."""
        result = PIIMaskingService.mask_phone("555-123-4567")
        assert result == "***-***-4567"

    def test_mask_phone_digits_only(self):
        """Test masking phone with digits only."""
        result = PIIMaskingService.mask_phone("5551234567")
        assert result == "***-***-4567"

    def test_mask_phone_short(self):
        """Test masking short phone number."""
        result = PIIMaskingService.mask_phone("123")
        assert result == "***"

    def test_mask_phone_empty(self):
        """Test masking empty phone returns empty."""
        result = PIIMaskingService.mask_phone("")
        assert result == ""

    def test_mask_name_single_word(self):
        """Test masking single word name."""
        result = PIIMaskingService.mask_name("John")
        assert result == "J***"

    def test_mask_name_multiple_words(self):
        """Test masking multiple word name."""
        result = PIIMaskingService.mask_name("John Doe")
        assert result == "J*** D***"

    def test_mask_name_three_words(self):
        """Test masking three word name."""
        result = PIIMaskingService.mask_name("John Michael Doe")
        assert result == "J*** M*** D***"

    def test_mask_name_empty(self):
        """Test masking empty name returns empty."""
        result = PIIMaskingService.mask_name("")
        assert result == ""

    def test_mask_full_standard(self):
        """Test full masking preserves length."""
        result = PIIMaskingService.mask_full("sensitive data")
        assert result == "**************"
        assert len(result) == len("sensitive data")

    def test_mask_full_short(self):
        """Test full masking short string."""
        result = PIIMaskingService.mask_full("abc")
        assert result == "***"

    def test_mask_full_empty(self):
        """Test full masking empty string returns empty."""
        result = PIIMaskingService.mask_full("")
        assert result == ""

    def test_mask_custom_defaults_to_full(self):
        """Test custom masking defaults to full masking."""
        result = PIIMaskingService.mask_custom("custom data")
        assert result == "***********"

    def test_mask_custom_with_pattern(self):
        """Test custom masking with pattern (currently ignored)."""
        result = PIIMaskingService.mask_custom("custom data", pattern="custom")
        # Currently defaults to full masking
        assert result == "***********"

    def test_mask_value_email(self):
        """Test mask_value routes to email masking."""
        result = PIIMaskingService.mask_value("john@example.com", "email")
        assert result == "j***@example.com"

    def test_mask_value_ssn(self):
        """Test mask_value routes to SSN masking."""
        result = PIIMaskingService.mask_value("123-45-6789", "ssn")
        assert result == "***-**-****"

    def test_mask_value_phone(self):
        """Test mask_value routes to phone masking."""
        result = PIIMaskingService.mask_value("+1-555-123-4567", "phone")
        assert result == "+1-***-***-4567"

    def test_mask_value_name(self):
        """Test mask_value routes to name masking."""
        result = PIIMaskingService.mask_value("John Doe", "name")
        assert result == "J*** D***"

    def test_mask_value_full(self):
        """Test mask_value routes to full masking."""
        result = PIIMaskingService.mask_value("secret", "full")
        assert result == "******"

    def test_mask_value_custom(self):
        """Test mask_value routes to custom masking."""
        result = PIIMaskingService.mask_value("data", "custom")
        assert result == "****"

    def test_mask_value_case_insensitive(self):
        """Test mask_value is case insensitive."""
        result = PIIMaskingService.mask_value("john@example.com", "EMAIL")
        assert result == "j***@example.com"

    def test_mask_value_unknown_type(self):
        """Test mask_value with unknown type returns original."""
        result = PIIMaskingService.mask_value("data", "unknown")
        assert result == "data"

    def test_mask_value_none(self):
        """Test mask_value with None returns None."""
        result = PIIMaskingService.mask_value(None, "email")
        assert result is None

    def test_mask_value_numeric(self):
        """Test mask_value converts numeric to string."""
        result = PIIMaskingService.mask_value(123456789, "ssn")
        assert result == "***-**-****"

    def test_mask_email_with_subdomain(self):
        """Test masking email with subdomain."""
        result = PIIMaskingService.mask_email("user@mail.example.com")
        assert result == "u***@mail.example.com"

    def test_mask_phone_international(self):
        """Test masking international phone number."""
        result = PIIMaskingService.mask_phone("+44-20-1234-5678")
        # Should show country code and last 4
        assert result.startswith("+44")
        assert result.endswith("5678")

    def test_mask_name_with_special_chars(self):
        """Test masking name with special characters."""
        result = PIIMaskingService.mask_name("O'Brien")
        assert result == "O***"

    def test_mask_full_with_special_chars(self):
        """Test full masking with special characters."""
        result = PIIMaskingService.mask_full("test@#$%")
        assert result == "********"
        assert len(result) == 8
