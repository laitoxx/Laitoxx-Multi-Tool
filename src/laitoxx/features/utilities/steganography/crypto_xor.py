"""Portable XOR fallback encryption."""

from __future__ import annotations

import hashlib

from .crypto_model import EncryptedPayload, derive_key, generate_salt


def encrypt_xor(data: bytes, password: str) -> EncryptedPayload:
    """
    Simple XOR encryption (fallback when cryptography not available)
    NOT CRYPTOGRAPHICALLY SECURE - use only as fallback

    Args:
        data: Plaintext bytes
        password: Encryption password

    Returns:
        EncryptedPayload with XOR'd ciphertext
    """
    salt = generate_salt()
    key = derive_key(password, salt, key_length=len(data))

    # Extend key to match data length using key derivation
    extended_key = b""
    counter = 0
    while len(extended_key) < len(data):
        extended_key += hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        counter += 1
    extended_key = extended_key[: len(data)]

    ciphertext = bytes(a ^ b for a, b in zip(data, extended_key, strict=False))

    return EncryptedPayload(
        ciphertext=ciphertext,
        iv=b"",  # XOR doesn't use IV
        salt=salt,
        method="xor",
    )


def decrypt_xor(payload: EncryptedPayload, password: str) -> bytes:
    """
    Decrypt XOR encrypted data

    Args:
        payload: EncryptedPayload from encrypt_xor
        password: Decryption password

    Returns:
        Decrypted plaintext bytes
    """
    key = derive_key(password, payload.salt, key_length=len(payload.ciphertext))

    # Extend key to match data length
    extended_key = b""
    counter = 0
    while len(extended_key) < len(payload.ciphertext):
        extended_key += hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        counter += 1
    extended_key = extended_key[: len(payload.ciphertext)]

    plaintext = bytes(a ^ b for a, b in zip(payload.ciphertext, extended_key, strict=False))
    return plaintext
