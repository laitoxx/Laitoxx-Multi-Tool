"""Encrypted payload value object and key material helpers."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass


@dataclass
class EncryptedPayload:
    """Container for encrypted data with metadata"""

    ciphertext: bytes
    iv: bytes
    salt: bytes
    method: str  # 'aes-256-cbc', 'aes-256-gcm', 'xor'


def derive_key(password: str, salt: bytes, key_length: int = 32) -> bytes:
    """
    Derive encryption key from password using PBKDF2

    Args:
        password: User password
        salt: Random salt (should be stored with ciphertext)
        key_length: Desired key length in bytes (32 for AES-256)

    Returns:
        Derived key bytes
    """
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations=600000, dklen=key_length)


def generate_salt(length: int = 16) -> bytes:
    """Generate cryptographically secure random salt"""
    return secrets.token_bytes(length)


def generate_iv(length: int = 16) -> bytes:
    """Generate cryptographically secure random IV"""
    return secrets.token_bytes(length)
