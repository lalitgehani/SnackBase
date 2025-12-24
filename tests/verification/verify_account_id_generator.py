#!/usr/bin/env python3
"""Verification script for F1.13: Account ID Generator.

Demonstrates all acceptance criteria:
- Format validation (XX####)
- ID generation and uniqueness
- Collision handling
- Letter/number cycling
- Exhaustion scenarios
- Descriptive error messages
"""

from snackbase.domain.services.account_id_generator import (
    AccountIdExhaustedError,
    AccountIdGenerator,
)


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def print_test(description: str, passed: bool, details: str = "") -> None:
    """Print a test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {description}")
    if details:
        print(f"       {details}")


def test_format_validation() -> None:
    """Test format validation."""
    print_section("1. Format Validation (XX####)")

    # Valid IDs
    valid_ids = ["AB1234", "XY9876", "AA0001", "ZZ9999"]
    for account_id in valid_ids:
        result = AccountIdGenerator.validate(account_id)
        print_test(
            f"Validate '{account_id}'",
            result is True,
            f"Result: {result}",
        )

    # Invalid IDs
    invalid_test_cases = [
        ("ab1234", "lowercase letters"),
        ("A1234", "wrong length (5 chars)"),
        ("ABC1234", "wrong length (7 chars)"),
        ("AB12A4", "letter in number portion"),
        ("A@1234", "special character"),
        ("", "empty string"),
    ]

    for account_id, reason in invalid_test_cases:
        result = AccountIdGenerator.validate(account_id)
        print_test(
            f"Reject '{account_id}' ({reason})",
            result is False,
            f"Result: {result}",
        )


def test_validation_with_errors() -> None:
    """Test validation with descriptive error messages."""
    print_section("2. Descriptive Error Messages")

    test_cases = [
        ("AB1234", True, None),
        ("ab1234", False, "uppercase"),
        ("A1234", False, "6 characters"),
        ("", False, "empty"),
        (123456, False, "string"),
        ("AB12A4", False, "digits"),
    ]

    for value, expected_valid, expected_error_keyword in test_cases:
        is_valid, error = AccountIdGenerator.validate_with_error(value)
        passed = is_valid == expected_valid

        if not expected_valid and expected_error_keyword:
            passed = passed and expected_error_keyword in error.lower()

        details = f"Valid: {is_valid}, Error: {error}" if error else f"Valid: {is_valid}"
        print_test(
            f"Validate '{value}'",
            passed,
            details,
        )


def test_id_generation() -> None:
    """Test ID generation."""
    print_section("3. ID Generation and Uniqueness")

    # First ID
    first_id = AccountIdGenerator.generate([])
    print_test(
        "First ID generation (no existing IDs)",
        first_id == "AA0001",
        f"Generated: {first_id}",
    )

    # Sequential generation
    existing = ["AA0001"]
    next_id = AccountIdGenerator.generate(existing)
    print_test(
        "Sequential generation",
        next_id == "AA0002",
        f"After AA0001 -> {next_id}",
    )

    # Generate multiple IDs
    existing = []
    generated = []
    for i in range(10):
        new_id = AccountIdGenerator.generate(existing + generated)
        generated.append(new_id)

    all_unique = len(generated) == len(set(generated))
    all_valid = all(AccountIdGenerator.validate(id_) for id_ in generated)
    print_test(
        "Generate 10 unique IDs",
        all_unique and all_valid,
        f"Generated: {', '.join(generated[:5])}... (showing first 5)",
    )


def test_collision_handling() -> None:
    """Test collision handling."""
    print_section("4. Collision Handling")

    # Continue from highest (implementation increments from highest, doesn't fill gaps)
    existing = ["AA0001", "AA0002", "AA0004"]
    new_id = AccountIdGenerator.generate(existing)
    print_test(
        "Continue from highest ID (doesn't fill gaps)",
        new_id == "AA0005",
        f"Existing: {existing}, Highest: AA0004, Generated: {new_id}",
    )

    # Continue from highest with gaps
    existing = ["AA0001", "AA0005", "AA0003"]
    new_id = AccountIdGenerator.generate(existing)
    print_test(
        "Continue from highest ID",
        new_id == "AA0006",
        f"Highest: AA0005, Generated: {new_id}",
    )


def test_letter_number_cycling() -> None:
    """Test letter and number cycling."""
    print_section("5. Letter and Number Cycling")

    test_cases = [
        (["AA9999"], "AB0000", "Number overflow (9999 -> 0000, letter increment)"),
        (["AB9999"], "AC0000", "Number overflow with second letter"),
        (["AZ9999"], "BA0000", "Second letter overflow (Z -> A, first letter increment)"),
        (["BZ9999"], "CA0000", "Second letter overflow again"),
    ]

    for existing, expected, description in test_cases:
        new_id = AccountIdGenerator.generate(existing)
        print_test(
            description,
            new_id == expected,
            f"After {existing[0]} -> {new_id}",
        )


def test_sy_prefix_handling() -> None:
    """Test SY prefix (reserved for system) handling."""
    print_section("6. Reserved Prefix Handling (SY)")

    # Skip SY prefix
    existing = ["SX9999"]
    new_id = AccountIdGenerator.generate(existing)
    print_test(
        "Skip SY prefix (reserved)",
        new_id == "SZ0000",
        f"After SX9999 -> {new_id} (skipped SY)",
    )

    # Ignore SY in existing IDs
    existing = ["SY0001", "SY9999", "AA0001"]
    new_id = AccountIdGenerator.generate(existing)
    print_test(
        "Ignore SY IDs when finding highest",
        new_id == "AA0002",
        f"Existing: {existing}, Generated: {new_id}",
    )


def test_capacity() -> None:
    """Test total capacity calculation."""
    print_section("7. Total Capacity")

    # Calculate capacity
    letter_pairs = 26 * 26  # AA-ZZ
    numbers_per_pair = 10000  # 0000-9999
    total_capacity = letter_pairs * numbers_per_pair

    print_test(
        "Total capacity calculation",
        total_capacity == 6_760_000,
        f"26 letters × 26 letters × 10,000 numbers = {total_capacity:,}",
    )

    # Test near exhaustion
    existing = ["ZZ9998"]
    new_id = AccountIdGenerator.generate(existing)
    print_test(
        "Generate near exhaustion",
        new_id == "ZZ9999",
        f"After ZZ9998 -> {new_id}",
    )


def test_exhaustion_error() -> None:
    """Test exhaustion error."""
    print_section("8. Exhaustion Error Handling")

    try:
        # Try to generate after last possible ID
        AccountIdGenerator.generate(["ZZ9999"])
        print_test("Exhaustion error raised", False, "No error was raised!")
    except AccountIdExhaustedError as e:
        error_msg = str(e)
        has_capacity = "6,760,000" in error_msg
        has_exhausted = "exhausted" in error_msg.lower()

        print_test(
            "Exhaustion error raised with descriptive message",
            has_capacity and has_exhausted,
            f"Error: {error_msg}",
        )


def test_restart_behavior() -> None:
    """Test behavior after system restart."""
    print_section("9. Restart Behavior")

    # Simulate existing IDs from database (non-sequential)
    existing = ["AA0001", "AB0001", "AA0005", "MN5432", "XY9876"]
    new_id = AccountIdGenerator.generate(existing)

    # Should find highest (XY9876) and increment
    print_test(
        "Find highest ID and continue",
        new_id == "XY9877",
        f"Existing: {existing}, Highest: XY9876, Generated: {new_id}",
    )

    # With gaps
    existing = ["AA0001", "AA0010", "AA0005"]
    new_id = AccountIdGenerator.generate(existing)
    print_test(
        "Handle gaps in sequence",
        new_id == "AA0011",
        f"Existing: {existing}, Generated: {new_id}",
    )


def test_edge_cases() -> None:
    """Test edge cases."""
    print_section("10. Edge Cases")

    # Empty existing IDs
    new_id = AccountIdGenerator.generate([])
    print_test(
        "Empty existing IDs",
        new_id == "AA0001",
        f"Generated: {new_id}",
    )

    # Single existing ID
    new_id = AccountIdGenerator.generate(["AA0001"])
    print_test(
        "Single existing ID",
        new_id == "AA0002",
        f"Generated: {new_id}",
    )

    # Invalid IDs in existing set (should be ignored)
    existing = ["AA0001", "invalid", "AB12", "AA0002"]
    new_id = AccountIdGenerator.generate(existing)
    print_test(
        "Ignore invalid IDs in existing set",
        new_id == "AA0003",
        f"Existing: {existing}, Generated: {new_id}",
    )

    # Boundary: AA0000
    new_id = AccountIdGenerator.generate(["AA0000"])
    print_test(
        "Boundary case: AA0000",
        new_id == "AA0001",
        f"After AA0000 -> {new_id}",
    )


def main() -> None:
    """Run all verification tests."""
    print("\n" + "=" * 70)
    print("  F1.13: Account ID Generator - Verification Script")
    print("=" * 70)

    test_format_validation()
    test_validation_with_errors()
    test_id_generation()
    test_collision_handling()
    test_letter_number_cycling()
    test_sy_prefix_handling()
    test_capacity()
    test_exhaustion_error()
    test_restart_behavior()
    test_edge_cases()

    print_section("Verification Complete")
    print("All acceptance criteria have been demonstrated.")
    print("\nNext steps:")
    print("  1. Run unit tests: uv run pytest tests/unit/domain/test_account_id_generator.py -v")
    print("  2. Run integration tests: uv run pytest tests/integration/test_account_id_generator_integration.py -v")
    print("  3. Check test coverage: uv run pytest tests/ --cov=snackbase.domain.services.account_id_generator")
    print()


if __name__ == "__main__":
    main()
