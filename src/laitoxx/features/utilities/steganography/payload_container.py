"""Validated envelope shared by non-LSB image methods."""

from __future__ import annotations

import struct
import zlib

MAGIC = b"ST3M"
VERSION = 1
_HEADER = struct.Struct(">4sBBHII")


def pack_method_payload(method: str, payload: bytes, *, encrypted: bool = False) -> bytes:
    method_bytes = method.upper().encode("ascii")
    if len(method_bytes) > 255:
        raise ValueError("Method identifier is too long")
    flags = 1 if encrypted else 0
    checksum = zlib.crc32(payload) & 0xFFFFFFFF
    return _HEADER.pack(MAGIC, VERSION, flags, len(method_bytes), len(payload), checksum) + method_bytes + payload


def unpack_method_payload(data: bytes, expected_method: str | None = None) -> tuple[bytes, bool]:
    if len(data) < _HEADER.size:
        raise ValueError("Payload envelope is too short")
    magic, version, flags, method_length, payload_length, checksum = _HEADER.unpack_from(data)
    if magic != MAGIC:
        raise ValueError("No ST3GG method envelope found")
    if version != VERSION:
        raise ValueError(f"Unsupported method envelope version: {version}")
    end_method = _HEADER.size + method_length
    end_payload = end_method + payload_length
    if end_payload > len(data):
        raise ValueError("Incomplete method payload")
    method = data[_HEADER.size : end_method].decode("ascii")
    if expected_method and method != expected_method.upper():
        raise ValueError(f"Payload belongs to {method}, not {expected_method.upper()}")
    payload = data[end_method:end_payload]
    if zlib.crc32(payload) & 0xFFFFFFFF != checksum:
        raise ValueError("Method payload checksum mismatch")
    return payload, bool(flags & 1)
