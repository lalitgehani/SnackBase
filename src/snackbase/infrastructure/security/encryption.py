import base64
import hashlib
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet, InvalidToken


class EncryptionService:
    """
    Encryption service using Fernet symmetric encryption.
    """

    DEFAULT_SENSITIVE_FIELDS = {
        "secret",
        "token",
        "key",
        "password",
        "cert",
        "access_key",
        "private",
    }

    def __init__(self, secret_key: str):
        """
        Initialize the encryption service with a secret key.
        The secret key is hashed using SHA-256 to ensure it's a valid 32-byte Fernet key.
        """
        key_bytes = secret_key.encode("utf-8")
        h = hashlib.sha256(key_bytes).digest()
        fernet_key = base64.urlsafe_b64encode(h)
        self._fernet = Fernet(fernet_key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string and return a base64-encoded ciphertext.
        """
        if not plaintext:
            return plaintext
        ciphertext = self._fernet.encrypt(plaintext.encode("utf-8"))
        return ciphertext.decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a base64-encoded ciphertext and return the original plaintext.
        Returns the original ciphertext if decryption fails.
        """
        if not ciphertext:
            return ciphertext
        try:
            plaintext = self._fernet.decrypt(ciphertext.encode("utf-8"))
            return plaintext.decode("utf-8")
        except (InvalidToken, ValueError):
            # If not a valid Fernet token or decryption fails, return as is
            return ciphertext

    def encrypt_dict(
        self, data: Dict[str, Any], sensitive_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Recursively encrypt sensitive fields in a dictionary.
        """
        fields_to_encrypt = (
            set(sensitive_fields) if sensitive_fields else self.DEFAULT_SENSITIVE_FIELDS
        )
        result: Dict[str, Any] = {}

        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = self.encrypt_dict(value, list(fields_to_encrypt))
            elif isinstance(value, list):
                result[key] = [
                    self.encrypt_dict(item, list(fields_to_encrypt)) if isinstance(item, dict) else item
                    for item in value
                ]
            elif (
                any(field in key.lower() for field in fields_to_encrypt)
                and isinstance(value, str)
                and value
            ):
                result[key] = self.encrypt(value)
            else:
                result[key] = value

        return result

    def decrypt_dict(
        self, data: Dict[str, Any], sensitive_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Recursively decrypt sensitive fields in a dictionary.
        """
        fields_to_decrypt = (
            set(sensitive_fields) if sensitive_fields else self.DEFAULT_SENSITIVE_FIELDS
        )
        result: Dict[str, Any] = {}

        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = self.decrypt_dict(value, list(fields_to_decrypt))
            elif isinstance(value, list):
                result[key] = [
                    self.decrypt_dict(item, list(fields_to_decrypt)) if isinstance(item, dict) else item
                    for item in value
                ]
            elif (
                any(field in key.lower() for field in fields_to_decrypt)
                and isinstance(value, str)
                and value
            ):
                result[key] = self.decrypt(value)
            else:
                result[key] = value

        return result
