"""PII masking service for protecting sensitive data.

Provides masking functions for different types of PII data based on user permissions.
"""

import re
from typing import Any


class PIIMaskingService:
    """Service for masking PII data in API responses.
    
    Masks sensitive data based on mask type. Only users with the 'pii_access'
    group can see unmasked data.
    """

    PII_ACCESS_GROUP = "pii_access"

    @classmethod
    def should_mask_for_user(cls, user_groups: list[str]) -> bool:
        """Check if data should be masked for the given user.
        
        Args:
            user_groups: List of group names the user belongs to.
            
        Returns:
            True if data should be masked, False if user has pii_access.
        """
        return cls.PII_ACCESS_GROUP not in user_groups

    @classmethod
    def mask_email(cls, value: str) -> str:
        """Mask email address as j***@example.com.
        
        Shows first character of local part and full domain.
        
        Args:
            value: Email address to mask.
            
        Returns:
            Masked email address.
        """
        if not value or "@" not in value:
            return value
        
        local, domain = value.split("@", 1)
        if len(local) == 0:
            return value
        
        masked_local = local[0] + "***"
        return f"{masked_local}@{domain}"

    @classmethod
    def mask_ssn(cls, value: str) -> str:
        """Mask SSN as ***-**-****.
        
        Masks all digits in SSN format.
        
        Args:
            value: SSN to mask (can be with or without dashes).
            
        Returns:
            Masked SSN.
        """
        if not value:
            return value
        
        # Remove all non-digit characters to check length
        digits_only = re.sub(r"\D", "", value)
        
        if len(digits_only) == 9:
            # Standard SSN format
            return "***-**-****"
        else:
            # Non-standard format, mask all digits
            return re.sub(r"\d", "*", value)

    @classmethod
    def mask_phone(cls, value: str) -> str:
        """Mask phone number as +1-***-***-4567.
        
        Shows country code (if present) and last 4 digits.
        
        Args:
            value: Phone number to mask.
            
        Returns:
            Masked phone number.
        """
        if not value:
            return value
        
        # Extract digits
        digits = re.sub(r"\D", "", value)
        
        if len(digits) < 4:
            # Too short, mask everything
            return re.sub(r"\d", "*", value)
        
        # Check if starts with country code
        if value.strip().startswith("+"):
            # Extract country code (1-3 digits after +)
            country_match = re.match(r"(\+\d{1,3})", value)
            if country_match:
                country_code = country_match.group(1)
                last_four = digits[-4:]
                return f"{country_code}-***-***-{last_four}"
        
        # No country code, just show last 4
        last_four = digits[-4:]
        return f"***-***-{last_four}"

    @classmethod
    def mask_name(cls, value: str) -> str:
        """Mask name as J*** D***.
        
        Shows first character of each word.
        
        Args:
            value: Name to mask.
            
        Returns:
            Masked name.
        """
        if not value:
            return value
        
        words = value.split()
        masked_words = []
        
        for word in words:
            if len(word) == 0:
                continue
            masked_word = word[0] + "***"
            masked_words.append(masked_word)
        
        return " ".join(masked_words)

    @classmethod
    def mask_full(cls, value: str) -> str:
        """Mask entire value as ****** (same length as original).
        
        Replaces all characters with asterisks.
        
        Args:
            value: Value to mask.
            
        Returns:
            Masked value with same length.
        """
        if not value:
            return value
        
        return "*" * len(value)

    @classmethod
    def mask_custom(cls, value: str, pattern: str | None = None) -> str:
        """Apply custom masking pattern.
        
        Currently defaults to full masking. Can be extended to support
        custom patterns in the future.
        
        Args:
            value: Value to mask.
            pattern: Custom pattern (currently unused).
            
        Returns:
            Masked value.
        """
        # For now, custom masking defaults to full masking
        # This can be extended to support custom patterns in the future
        return cls.mask_full(value)

    @classmethod
    def mask_value(cls, value: Any, mask_type: str) -> Any:
        """Mask a value based on its mask type.
        
        Routes to the appropriate masking function based on mask_type.
        
        Args:
            value: Value to mask.
            mask_type: Type of masking to apply (email, ssn, phone, name, full, custom).
            
        Returns:
            Masked value, or original value if mask_type is unknown or value is None.
        """
        if value is None:
            return None
        
        # Convert to string for masking
        str_value = str(value)
        
        mask_type_lower = mask_type.lower()
        
        if mask_type_lower == "email":
            return cls.mask_email(str_value)
        elif mask_type_lower == "ssn":
            return cls.mask_ssn(str_value)
        elif mask_type_lower == "phone":
            return cls.mask_phone(str_value)
        elif mask_type_lower == "name":
            return cls.mask_name(str_value)
        elif mask_type_lower == "full":
            return cls.mask_full(str_value)
        elif mask_type_lower == "custom":
            return cls.mask_custom(str_value)
        else:
            # Unknown mask type, return original value
            return value
