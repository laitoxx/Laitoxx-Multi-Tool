"""
STEGOSAURUS WRECKS - Cryptography Module
AES encryption for steganographic payloads
"""

from .crypto_aes import decrypt_aes_cbc, decrypt_aes_gcm, encrypt_aes_cbc, encrypt_aes_gcm
from .crypto_backend import HAS_CRYPTO
from .crypto_model import EncryptedPayload
from .crypto_xor import decrypt_xor, encrypt_xor

# ============== AES Encryption (requires cryptography library) ==============


# ============== XOR Encryption (fallback, no dependencies) ==============


# ============== Unified Interface ==============


def encrypt(data: bytes, password: str, method: str = "auto") -> bytes:
    """
    Encrypt data with specified method

    Args:
        data: Plaintext bytes
        password: Encryption password
        method: 'aes-cbc', 'aes-gcm', 'xor', or 'auto'

    Returns:
        Packed encrypted payload (can be embedded directly)
    """
    if method == "auto":
        method = "aes-gcm" if HAS_CRYPTO else "xor"

    if method == "aes-cbc":
        payload = encrypt_aes_cbc(data, password)
    elif method == "aes-gcm":
        payload = encrypt_aes_gcm(data, password)
    elif method == "xor":
        payload = encrypt_xor(data, password)
    else:
        raise ValueError(f"Unknown encryption method: {method}")

    return pack_payload(payload)


def decrypt(packed_data: bytes, password: str) -> bytes:
    """
    Decrypt packed encrypted payload

    Args:
        packed_data: Packed payload from encrypt()
        password: Decryption password

    Returns:
        Decrypted plaintext bytes
    """
    payload = unpack_payload(packed_data)

    if payload.method == "aes-256-cbc":
        return decrypt_aes_cbc(payload, password)
    elif payload.method == "aes-256-gcm":
        return decrypt_aes_gcm(payload, password)
    elif payload.method == "xor":
        return decrypt_xor(payload, password)
    else:
        raise ValueError(f"Unknown encryption method: {payload.method}")


def pack_payload(payload: EncryptedPayload) -> bytes:
    """
    Pack EncryptedPayload into bytes for embedding

    Format:
    [1 byte: method ID][1 byte: salt len][salt][1 byte: iv len][iv][ciphertext]
    """
    method_ids = {"aes-256-cbc": 1, "aes-256-gcm": 2, "xor": 3}
    method_id = method_ids.get(payload.method, 0)

    packed = bytes([method_id])
    packed += bytes([len(payload.salt)]) + payload.salt
    packed += bytes([len(payload.iv)]) + payload.iv
    packed += payload.ciphertext

    return packed


def unpack_payload(data: bytes) -> EncryptedPayload:
    """
    Unpack bytes into EncryptedPayload

    Args:
        data: Packed payload bytes

    Returns:
        EncryptedPayload object
    """
    method_names = {1: "aes-256-cbc", 2: "aes-256-gcm", 3: "xor"}

    idx = 0
    method_id = data[idx]
    method = method_names.get(method_id, "unknown")
    idx += 1

    salt_len = data[idx]
    idx += 1
    salt = data[idx : idx + salt_len]
    idx += salt_len

    iv_len = data[idx]
    idx += 1
    iv = data[idx : idx + iv_len]
    idx += iv_len

    ciphertext = data[idx:]

    return EncryptedPayload(ciphertext=ciphertext, iv=iv, salt=salt, method=method)


def get_available_methods() -> list:
    """Get list of available encryption methods"""
    methods = ["xor"]  # Always available
    if HAS_CRYPTO:
        methods = ["aes-gcm", "aes-cbc"] + methods
    return methods


def crypto_status() -> dict:
    """Get cryptography library status"""
    return {
        "cryptography_available": HAS_CRYPTO,
        "available_methods": get_available_methods(),
        "recommended": "aes-gcm" if HAS_CRYPTO else "xor",
    }
