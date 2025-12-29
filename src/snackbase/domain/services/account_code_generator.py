"""Account code generator service.

Generates unique account codes in XX#### format (2 uppercase letters + 4 digits).
Provides validation and collision prevention.
"""

import re
from typing import Iterable


class AccountCodeExhaustedError(Exception):
    """Raised when all possible account codes have been exhausted."""

    def __init__(self) -> None:
        super().__init__(
            "All 6,760,000 possible account codes have been exhausted. "
            "Consider implementing an extended code format."
        )


class AccountCodeGenerator:
    """Generator for unique account codes in XX#### format.

    Generates codes by cycling through letter pairs (AA-ZZ) and number
    portions (0000-9999). Total capacity is 6,760,000 unique codes.

    Example codes: AA0001, AB1234, XY9876, ZZ9999
    """

    # Regex pattern for valid account codes
    PATTERN = re.compile(r"^[A-Z]{2}\d{4}$")

    # Letter range for code generation
    LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    @classmethod
    def validate(cls, account_code: str) -> bool:
        """Validate that an account code matches the XX#### format.

        Args:
            account_code: The account code to validate.

        Returns:
            True if the code matches the format, False otherwise.

        Examples:
            >>> AccountCodeGenerator.validate("AB1234")
            True
            >>> AccountCodeGenerator.validate("ab1234")
            False
            >>> AccountCodeGenerator.validate("A1234")
            False
        """
        if not isinstance(account_code, str):
            return False
        return bool(cls.PATTERN.match(account_code))

    @classmethod
    def validate_with_error(cls, account_code: str) -> tuple[bool, str | None]:
        """Validate an account code and return a descriptive error message if invalid.

        Args:
            account_code: The account code to validate.

        Returns:
            A tuple of (is_valid, error_message). If valid, error_message is None.
            If invalid, error_message describes the validation failure.

        Examples:
            >>> AccountCodeGenerator.validate_with_error("AB1234")
            (True, None)
            >>> AccountCodeGenerator.validate_with_error("ab1234")
            (False, "Account code must contain uppercase letters only")
            >>> AccountCodeGenerator.validate_with_error("A1234")
            (False, "Account code must be exactly 6 characters (2 letters + 4 digits)")
        """
        if not isinstance(account_code, str):
            return False, "Account code must be a string"

        if not account_code:
            return False, "Account code cannot be empty"

        if len(account_code) != 6:
            return (
                False,
                f"Account code must be exactly 6 characters (2 letters + 4 digits), got {len(account_code)}",
            )

        # Check letter portion
        letter_portion = account_code[:2]
        if not letter_portion.isalpha():
            return False, "First 2 characters must be letters"

        if not letter_portion.isupper():
            return False, "Account code must contain uppercase letters only"

        # Check number portion
        number_portion = account_code[2:]
        if not number_portion.isdigit():
            return False, "Last 4 characters must be digits"

        return True, None

    @classmethod
    def generate(cls, existing_codes: Iterable[str] | None = None) -> str:
        """Generate a new unique account code.

        Generates the next available code by finding the highest existing code
        and incrementing. If no existing codes, starts from AA0001.

        Thread-Safety:
            This method is a pure function and is inherently thread-safe.
            However, the caller MUST ensure that existing_codes is fetched
            within a database transaction with appropriate isolation level
            (e.g., SERIALIZABLE or REPEATABLE READ) to prevent race conditions
            during concurrent account creation.

        Args:
            existing_codes: Iterable of existing account codes to avoid collisions.
                Should be fetched from the database within a transaction.

        Returns:
            A new unique account code in XX#### format.

        Raises:
            AccountCodeExhaustedError: If all 6,760,000 codes are exhausted.

        Examples:
            >>> AccountCodeGenerator.generate([])
            'AA0001'
            >>> AccountCodeGenerator.generate(['AA0001'])
            'AA0002'
            >>> AccountCodeGenerator.generate(['AA9999'])
            'AB0000'
        """
        existing_set = set(existing_codes) if existing_codes else set()

        if not existing_set:
            # Start with AA0001 (skip 0000 for aesthetic reasons)
            return "AA0001"

        # Find the highest existing code and increment from there
        highest = cls._find_highest_code(existing_set)
        next_code = cls._increment_code(highest)

        # Keep incrementing until we find an unused code
        attempts = 0
        max_attempts = 6_760_000  # Total possible codes

        while next_code in existing_set:
            next_code = cls._increment_code(next_code)
            attempts += 1
            if attempts >= max_attempts:
                raise AccountCodeExhaustedError()

        return next_code

    @classmethod
    def _find_highest_code(cls, existing_codes: set[str]) -> str:
        """Find the highest code in the existing set.

        Ignores codes starting with 'SY' as they are reserved for system accounts.

        Args:
            existing_codes: Set of existing account codes.

        Returns:
            The highest code based on lexicographic ordering (excluding SY).
        """
        valid_codes = [
            code
            for code in existing_codes
            if cls.validate(code) and not code.startswith("SY")
        ]
        if not valid_codes:
            return "AA0000"
        return max(valid_codes, key=cls._code_sort_key)

    @classmethod
    def _code_sort_key(cls, account_code: str) -> tuple[int, int, int]:
        """Create a sort key for comparing account codes.

        Args:
            account_code: Valid account code in XX#### format.

        Returns:
            Tuple of (first_letter_index, second_letter_index, number).
        """
        first_letter = cls.LETTERS.index(account_code[0])
        second_letter = cls.LETTERS.index(account_code[1])
        number = int(account_code[2:])
        return (first_letter, second_letter, number)

    @classmethod
    def _increment_code(cls, account_code: str) -> str:
        """Increment an account code to the next value.

        Skips the 'SY' prefix range as it is reserved.

        Args:
            account_code: Valid account code in XX#### format.

        Returns:
            The next account code.

        Raises:
            AccountCodeExhaustedError: If incrementing past ZZ9999.
        """
        first_idx = cls.LETTERS.index(account_code[0])
        second_idx = cls.LETTERS.index(account_code[1])
        number = int(account_code[2:])

        # Increment number
        number += 1

        # Handle overflow
        if number > 9999:
            number = 0
            second_idx += 1

        if second_idx > 25:
            second_idx = 0
            first_idx += 1

        if first_idx > 25:
            raise AccountCodeExhaustedError()

        # Check for reserved prefix SY
        # S=18, Y=24
        s_idx = cls.LETTERS.index("S")
        y_idx = cls.LETTERS.index("Y")

        if first_idx == s_idx and second_idx == y_idx:
            # Skip entire SY range -> jump to SZ
            # Actually, next after SY9999 is SZ0000
            # But if we land anywhere in SY range (e.g. SY0000), skip to SZ0000
            # Since we only increment by 1 or carry over, we will hit SY0000 first
            # (coming from SX9999 -> SY0000).
            # So just force it to next block if we are in SY.
            # But wait, we might just want to skip SY completely.
            # If we are at SYxxxx, move to SZ0000?
            # Yes, simpler validation.
            second_idx += 1
            number = 0
            # Should be safe since Y < Z (24 < 25), so second_idx becomes 25 (Z).

        return f"{cls.LETTERS[first_idx]}{cls.LETTERS[second_idx]}{number:04d}"
