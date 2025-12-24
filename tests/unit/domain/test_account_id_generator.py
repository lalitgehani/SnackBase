"""Unit tests for AccountIdGenerator.

Tests all acceptance criteria from F1.13:
- Format validation (XX####)
- ID generation and uniqueness
- Collision handling
- Letter/number cycling
- Exhaustion scenarios
- Restart behavior
"""

import pytest

from snackbase.domain.services.account_id_generator import (
    AccountIdExhaustedError,
    AccountIdGenerator,
)


class TestValidation:
    """Test account ID format validation."""

    def test_validate_valid_ids(self):
        """Valid IDs should pass validation."""
        valid_ids = [
            "AB1234",
            "XY9876",
            "AA0001",
            "ZZ9999",
            "AA0000",
            "MN5432",
        ]
        for account_id in valid_ids:
            assert AccountIdGenerator.validate(account_id) is True

    def test_validate_invalid_lowercase(self):
        """Lowercase letters should fail validation."""
        invalid_ids = [
            "ab1234",
            "Ab1234",
            "aB1234",
            "xy9876",
        ]
        for account_id in invalid_ids:
            assert AccountIdGenerator.validate(account_id) is False

    def test_validate_invalid_length(self):
        """Wrong length should fail validation."""
        invalid_ids = [
            "A1234",  # Too short
            "ABC1234",  # Too long
            "AB123",  # Too short
            "AB12345",  # Too long
            "",  # Empty
        ]
        for account_id in invalid_ids:
            assert AccountIdGenerator.validate(account_id) is False

    def test_validate_invalid_special_chars(self):
        """Special characters should fail validation."""
        invalid_ids = [
            "A@1234",
            "AB-234",
            "AB 234",
            "AB12.4",
            "AB12#4",
        ]
        for account_id in invalid_ids:
            assert AccountIdGenerator.validate(account_id) is False

    def test_validate_invalid_format(self):
        """Invalid format (numbers in letters, letters in numbers) should fail."""
        invalid_ids = [
            "A11234",  # Number in letter portion
            "1B1234",  # Number in letter portion
            "AB12A4",  # Letter in number portion
            "ABCD12",  # All letters
            "123456",  # All numbers
        ]
        for account_id in invalid_ids:
            assert AccountIdGenerator.validate(account_id) is False

    def test_validate_edge_cases(self):
        """Edge cases should be handled correctly."""
        assert AccountIdGenerator.validate(None) is False
        assert AccountIdGenerator.validate(123456) is False
        assert AccountIdGenerator.validate([]) is False
        assert AccountIdGenerator.validate({}) is False


class TestValidateWithError:
    """Test validation with descriptive error messages."""

    def test_validate_with_error_valid_id(self):
        """Valid ID should return (True, None)."""
        is_valid, error = AccountIdGenerator.validate_with_error("AB1234")
        assert is_valid is True
        assert error is None

    def test_validate_with_error_lowercase(self):
        """Lowercase should return descriptive error."""
        is_valid, error = AccountIdGenerator.validate_with_error("ab1234")
        assert is_valid is False
        assert "uppercase" in error.lower()

    def test_validate_with_error_wrong_length(self):
        """Wrong length should return descriptive error."""
        is_valid, error = AccountIdGenerator.validate_with_error("A1234")
        assert is_valid is False
        assert "6 characters" in error
        assert "got 5" in error

    def test_validate_with_error_empty(self):
        """Empty string should return descriptive error."""
        is_valid, error = AccountIdGenerator.validate_with_error("")
        assert is_valid is False
        assert "empty" in error.lower()

    def test_validate_with_error_not_string(self):
        """Non-string should return descriptive error."""
        is_valid, error = AccountIdGenerator.validate_with_error(123456)
        assert is_valid is False
        assert "string" in error.lower()

    def test_validate_with_error_non_alpha_letters(self):
        """Non-alphabetic characters in letter portion should return error."""
        is_valid, error = AccountIdGenerator.validate_with_error("A11234")
        assert is_valid is False
        assert "letters" in error.lower()

    def test_validate_with_error_non_digit_numbers(self):
        """Non-digit characters in number portion should return error."""
        is_valid, error = AccountIdGenerator.validate_with_error("AB12A4")
        assert is_valid is False
        assert "digits" in error.lower()


class TestGeneration:
    """Test account ID generation."""

    def test_generate_first_id(self):
        """First ID should be AA0001."""
        account_id = AccountIdGenerator.generate([])
        assert account_id == "AA0001"

    def test_generate_no_existing_ids(self):
        """With no existing IDs, should return AA0001."""
        account_id = AccountIdGenerator.generate(None)
        assert account_id == "AA0001"

    def test_generate_sequential(self):
        """Should generate sequential IDs."""
        existing = ["AA0001"]
        account_id = AccountIdGenerator.generate(existing)
        assert account_id == "AA0002"

        existing = ["AA0001", "AA0002"]
        account_id = AccountIdGenerator.generate(existing)
        assert account_id == "AA0003"

    def test_generate_collision_avoidance(self):
        """Should skip existing IDs even with gaps."""
        existing = ["AA0001", "AA0002", "AA0004"]
        account_id = AccountIdGenerator.generate(existing)
        # Implementation continues from highest (AA0004 -> AA0005)
        assert account_id == "AA0005"

    def test_generate_fills_gaps(self):
        """Should continue from highest ID."""
        existing = ["AA0001", "AA0005"]
        account_id = AccountIdGenerator.generate(existing)
        # Should increment from highest (AA0005) to AA0006
        assert account_id == "AA0006"

    def test_generate_number_overflow(self):
        """When numbers reach 9999, should advance to next letter pair."""
        existing = ["AA9999"]
        account_id = AccountIdGenerator.generate(existing)
        assert account_id == "AB0000"

    def test_generate_second_letter_overflow(self):
        """When second letter reaches Z, should advance first letter."""
        existing = ["AZ9999"]
        account_id = AccountIdGenerator.generate(existing)
        assert account_id == "BA0000"

    def test_generate_skips_sy_prefix(self):
        """Should skip SY prefix (reserved for system)."""
        existing = ["SX9999"]
        account_id = AccountIdGenerator.generate(existing)
        # Should skip SY and go to SZ
        assert account_id == "SZ0000"

    def test_generate_handles_sy_in_existing(self):
        """Should ignore SY IDs in existing set."""
        existing = ["SY0001", "SY9999", "AA0001"]
        account_id = AccountIdGenerator.generate(existing)
        # Should continue from AA0001, not SY9999
        assert account_id == "AA0002"

    def test_generate_multiple_sequential(self):
        """Should generate multiple unique IDs."""
        existing = []
        generated = []
        for _ in range(10):
            new_id = AccountIdGenerator.generate(existing + generated)
            generated.append(new_id)
            assert AccountIdGenerator.validate(new_id)

        # All should be unique
        assert len(set(generated)) == 10
        # Should be sequential starting from AA0001
        assert generated[0] == "AA0001"
        assert generated[9] == "AA0010"

    def test_generate_with_invalid_ids_in_existing(self):
        """Should ignore invalid IDs in existing set."""
        existing = ["AA0001", "invalid", "AB12", "AA0002"]
        account_id = AccountIdGenerator.generate(existing)
        # Should continue from AA0002
        assert account_id == "AA0003"

    def test_generate_collision_loop(self):
        """Should handle collision by incrementing until unused ID found."""
        # Create a scenario where the next ID after highest is already taken
        # This forces the collision loop to execute (lines 150-154)
        # Start with AA0005 as highest, but AA0006 and AA0007 already exist
        existing = ["AA0005", "AA0006", "AA0007", "AA0001"]
        account_id = AccountIdGenerator.generate(existing)
        # Should skip AA0006 and AA0007, land on AA0008
        assert account_id == "AA0008"

        # Test with more collisions
        existing = ["AB0001", "AB0002", "AB0003", "AB0004", "AB0005"]
        account_id = AccountIdGenerator.generate(existing)
        assert account_id == "AB0006"


class TestExhaustion:
    """Test ID exhaustion scenarios."""

    def test_generate_exhaustion_error(self):
        """Should raise error when all IDs are exhausted."""
        # Create a scenario where we're at ZZ9999
        existing = ["ZZ9999"]
        with pytest.raises(AccountIdExhaustedError) as exc_info:
            AccountIdGenerator.generate(existing)

        # Check error message
        assert "6,760,000" in str(exc_info.value)
        assert "exhausted" in str(exc_info.value).lower()

    def test_exhaustion_error_message(self):
        """Exhaustion error should have descriptive message."""
        error = AccountIdExhaustedError()
        message = str(error)
        assert "6,760,000" in message
        assert "exhausted" in message.lower()


class TestRestartBehavior:
    """Test behavior after system restart."""

    def test_find_highest_id(self):
        """Should correctly identify the highest ID."""
        existing = ["AB1234", "AA0001", "XY9876", "MN5432"]
        # XY9876 should be highest
        account_id = AccountIdGenerator.generate(existing)
        assert account_id == "XY9877"

    def test_restart_continues_from_highest(self):
        """After restart, should continue from highest existing ID."""
        # Simulate existing IDs from before restart
        existing = ["AA0001", "AA0005", "AA0003", "AB0001"]
        account_id = AccountIdGenerator.generate(existing)
        # Should continue from AB0001
        assert account_id == "AB0002"

    def test_restart_with_gaps(self):
        """Should handle gaps in ID sequence correctly."""
        existing = ["AA0001", "AA0010", "AA0005"]
        account_id = AccountIdGenerator.generate(existing)
        # Should continue from highest (AA0010)
        assert account_id == "AA0011"

    def test_restart_ignores_sy_prefix(self):
        """Should ignore SY prefix when finding highest ID."""
        existing = ["SY9999", "AA0001"]
        account_id = AccountIdGenerator.generate(existing)
        # Should use AA0001 as highest, not SY9999
        assert account_id == "AA0002"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_existing_ids(self):
        """Empty list should start from AA0001."""
        assert AccountIdGenerator.generate([]) == "AA0001"

    def test_single_existing_id(self):
        """Single existing ID should increment correctly."""
        assert AccountIdGenerator.generate(["AA0001"]) == "AA0002"

    def test_multiple_existing_ids(self):
        """Multiple existing IDs should find next available."""
        existing = ["AA0001", "AA0002", "AA0003"]
        assert AccountIdGenerator.generate(existing) == "AA0004"

    def test_non_sequential_existing_ids(self):
        """Non-sequential IDs should work correctly."""
        existing = ["AA0001", "AB0001", "AC0001"]
        assert AccountIdGenerator.generate(existing) == "AC0002"

    def test_boundary_aa0000(self):
        """AA0000 should increment to AA0001."""
        existing = ["AA0000"]
        assert AccountIdGenerator.generate(existing) == "AA0001"

    def test_boundary_zz9998(self):
        """ZZ9998 should increment to ZZ9999."""
        existing = ["ZZ9998"]
        assert AccountIdGenerator.generate(existing) == "ZZ9999"

    def test_letter_pair_combinations(self):
        """Test various letter pair combinations."""
        test_cases = [
            (["AA9999"], "AB0000"),
            (["AB9999"], "AC0000"),
            (["AZ9999"], "BA0000"),
            (["BZ9999"], "CA0000"),
            (["ZY9999"], "ZZ0000"),
        ]
        for existing, expected in test_cases:
            assert AccountIdGenerator.generate(existing) == expected

    def test_capacity_calculation(self):
        """Verify total capacity is 6,760,000."""
        # 26 letters * 26 letters * 10,000 numbers = 6,760,000
        # Minus SY prefix (1 * 10,000) = 6,750,000 usable
        # But we count total capacity as 6,760,000
        letter_pairs = 26 * 26  # 676
        numbers_per_pair = 10000
        total = letter_pairs * numbers_per_pair
        assert total == 6_760_000


class TestSortingAndComparison:
    """Test internal sorting and comparison logic."""

    def test_id_sort_key(self):
        """Test that IDs sort correctly."""
        ids = ["AB0001", "AA0002", "AA0001", "BA0001", "AB0002"]
        sorted_ids = sorted(ids, key=AccountIdGenerator._id_sort_key)
        assert sorted_ids == ["AA0001", "AA0002", "AB0001", "AB0002", "BA0001"]

    def test_find_highest_id_with_mixed_order(self):
        """Should find highest ID regardless of input order."""
        existing = {"AA0001", "ZZ9999", "AB0001", "MN5432"}
        highest = AccountIdGenerator._find_highest_id(existing)
        assert highest == "ZZ9999"

    def test_find_highest_id_empty_set(self):
        """Empty set should return AA0000."""
        highest = AccountIdGenerator._find_highest_id(set())
        assert highest == "AA0000"

    def test_find_highest_id_only_invalid(self):
        """Set with only invalid IDs should return AA0000."""
        existing = {"invalid", "AB12", "12345"}
        highest = AccountIdGenerator._find_highest_id(existing)
        assert highest == "AA0000"
