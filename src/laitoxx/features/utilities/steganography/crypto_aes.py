"""AES-CBC and AES-GCM payload encryption."""

from __future__ import annotations

from .crypto_backend import HAS_CRYPTO, Cipher, algorithms, default_backend, modes, padding
from .crypto_model import EncryptedPayload, derive_key, generate_iv, generate_salt


def encrypt_aes_cbc(data: bytes, password: str) -> EncryptedPayload:
    """
    Encrypt data using AES-256-CBC

    Args:
        data: Plaintext bytes
        password: Encryption password

    Returns:
        EncryptedPayload with ciphertext, IV, and salt
    """
    if not HAS_CRYPTO:
        raise RuntimeError("cryptography library not installed. Install with: pip install cryptography")

    salt = generate_salt()
    iv = generate_iv()
    key = derive_key(password, salt)

    # Pad data to block size
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data) + padder.finalize()

    # Encrypt
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    return EncryptedPayload(ciphertext=ciphertext, iv=iv, salt=salt, method="aes-256-cbc")


def decrypt_aes_cbc(payload: EncryptedPayload, password: str) -> bytes:
    """
    Decrypt AES-256-CBC encrypted data

    Args:
        payload: EncryptedPayload from encrypt_aes_cbc
        password: Decryption password

    Returns:
        Decrypted plaintext bytes
    """
    if not HAS_CRYPTO:
        raise RuntimeError("cryptography library not installed. Install with: pip install cryptography")

    key = derive_key(password, payload.salt)

    # Decrypt
    cipher = Cipher(algorithms.AES(key), modes.CBC(payload.iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(payload.ciphertext) + decryptor.finalize()

    # Unpad
    unpadder = padding.PKCS7(128).unpadder()
    data = unpadder.update(padded_data) + unpadder.finalize()

    return data


def encrypt_aes_gcm(data: bytes, password: str) -> EncryptedPayload:
    """
    Encrypt data using AES-256-GCM (authenticated encryption)

    Args:
        data: Plaintext bytes
        password: Encryption password

    Returns:
        EncryptedPayload with ciphertext (includes auth tag), IV, and salt
    """
    if not HAS_CRYPTO:
        raise RuntimeError("cryptography library not installed. Install with: pip install cryptography")

    salt = generate_salt()
    iv = generate_iv(12)  # GCM uses 12-byte IV
    key = derive_key(password, salt)

    cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(data) + encryptor.finalize()

    # Append auth tag to ciphertext
    ciphertext_with_tag = ciphertext + encryptor.tag

    return EncryptedPayload(ciphertext=ciphertext_with_tag, iv=iv, salt=salt, method="aes-256-gcm")


def decrypt_aes_gcm(payload: EncryptedPayload, password: str) -> bytes:
    """
    Decrypt AES-256-GCM encrypted data

    Args:
        payload: EncryptedPayload from encrypt_aes_gcm
        password: Decryption password

    Returns:
        Decrypted plaintext bytes
    """
    if not HAS_CRYPTO:
        raise RuntimeError("cryptography library not installed. Install with: pip install cryptography")

    key = derive_key(password, payload.salt)

    # Extract auth tag (last 16 bytes)
    ciphertext = payload.ciphertext[:-16]
    tag = payload.ciphertext[-16:]

    cipher = Cipher(algorithms.AES(key), modes.GCM(payload.iv, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    data = decryptor.update(ciphertext) + decryptor.finalize()

    return data
