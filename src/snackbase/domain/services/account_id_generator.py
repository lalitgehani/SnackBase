"""Account ID generator service.

Generates unique account IDs in XX#### format (2 uppercase letters + 4 digits).
Provides validation and collision prevention.
"""

import re
from typing import Iterable


class AccountIdExhaustedError(Exception):
    """Raised when all possible account IDs have been exhausted."""

    def __init__(self) -> None:
        super().__init__(
            "All 6,760,000 possible account IDs have been exhausted. "
            "Consider implementing an extended ID format."
        )


class AccountIdGenerator:
    """Generator for unique account IDs in XX#### format.

    Generates IDs by cycling through letter pairs (AA-ZZ) and number
    portions (0000-9999). Total capacity is 6,760,000 unique IDs.

    Example IDs: AA0001, AB1234, XY9876, ZZ9999
    """

    # Regex pattern for valid account IDs
    PATTERN = re.compile(r"^[A-Z]{2}\d{4}$")

    # Letter range for ID generation
    LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    @classmethod
    def validate(cls, account_id: str) -> bool:
        """Validate that an account ID matches the XX#### format.

        Args:
            account_id: The account ID to validate.

        Returns:
            True if the ID matches the format, False otherwise.

        Examples:
            >>> AccountIdGenerator.validate("AB1234")
            True
            >>> AccountIdGenerator.validate("ab1234")
            False
            >>> AccountIdGenerator.validate("A1234")
            False
        """
        if not isinstance(account_id, str):
            return False
        return bool(cls.PATTERN.match(account_id))

    @classmethod
    def generate(cls, existing_ids: Iterable[str] | None = None) -> str:
        """Generate a new unique account ID.

        Generates the next available ID by finding the highest existing ID
        and incrementing. If no existing IDs, starts from AA0001.

        Args:
            existing_ids: Iterable of existing account IDs to avoid collisions.

        Returns:
            A new unique account ID in XX#### format.

        Raises:
            AccountIdExhaustedError: If all 6,760,000 IDs are exhausted.
        """
        existing_set = set(existing_ids) if existing_ids else set()

        if not existing_set:
            # Start with AA0001 (skip 0000 for aesthetic reasons)
            return "AA0001"

        # Find the highest existing ID and increment from there
        highest = cls._find_highest_id(existing_set)
        next_id = cls._increment_id(highest)

        # Keep incrementing until we find an unused ID
        attempts = 0
        max_attempts = 6_760_000  # Total possible IDs

        while next_id in existing_set:
            next_id = cls._increment_id(next_id)
            attempts += 1
            if attempts >= max_attempts:
                raise AccountIdExhaustedError()

        return next_id

    @classmethod
    def _find_highest_id(cls, existing_ids: set[str]) -> str:
        """Find the highest ID in the existing set.

        Ignores IDs starting with 'SY' as they are reserved for system accounts.

        Args:
            existing_ids: Set of existing account IDs.

        Returns:
            The highest ID based on lexicographic ordering (excluding SY).
        """
        valid_ids = [
            id_
            for id_ in existing_ids
            if cls.validate(id_) and not id_.startswith("SY")
        ]
        if not valid_ids:
            return "AA0000"
        return max(valid_ids, key=cls._id_sort_key)

    @classmethod
    def _id_sort_key(cls, account_id: str) -> tuple[int, int, int]:
        """Create a sort key for comparing account IDs.

        Args:
            account_id: Valid account ID in XX#### format.

        Returns:
            Tuple of (first_letter_index, second_letter_index, number).
        """
        first_letter = cls.LETTERS.index(account_id[0])
        second_letter = cls.LETTERS.index(account_id[1])
        number = int(account_id[2:])
        return (first_letter, second_letter, number)

    @classmethod
    def _increment_id(cls, account_id: str) -> str:
        """Increment an account ID to the next value.

        Skips the 'SY' prefix range as it is reserved.

        Args:
            account_id: Valid account ID in XX#### format.

        Returns:
            The next account ID.

        Raises:
            AccountIdExhaustedError: If incrementing past ZZ9999.
        """
        first_idx = cls.LETTERS.index(account_id[0])
        second_idx = cls.LETTERS.index(account_id[1])
        number = int(account_id[2:])

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
            raise AccountIdExhaustedError()

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
