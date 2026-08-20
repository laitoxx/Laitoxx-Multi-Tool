"""Vectorized bit packing and pixel selection primitives."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from PIL import Image

from .models import HEADER_SIZE, EncodingStrategy, StegConfig


def _create_bit_mask(bits: int, offset: int = 0) -> int:
    """Create a bit mask for specified bits at offset"""
    return ((1 << bits) - 1) << offset


def _bytes_to_bits_array(data: bytes, bits_per_unit: int = 1) -> np.ndarray:
    """
    Convert bytes to numpy array of bit groups.
    Much faster than string conversion.

    Args:
        data: Input bytes
        bits_per_unit: How many bits per output element (1-8)

    Returns:
        numpy array of uint8 values, each containing bits_per_unit bits
    """
    # Convert to bit array
    byte_array = np.frombuffer(data, dtype=np.uint8)
    # Unpack each byte into 8 bits
    bits = np.unpackbits(byte_array)

    # Group into units of bits_per_unit
    if bits_per_unit == 1:
        return bits

    # Pad to multiple of bits_per_unit
    pad_len = (bits_per_unit - len(bits) % bits_per_unit) % bits_per_unit
    if pad_len:
        bits = np.concatenate([bits, np.zeros(pad_len, dtype=np.uint8)])

    # Reshape and combine bits
    bits = bits.reshape(-1, bits_per_unit)
    # Convert each group to a value (MSB first within each group)
    multipliers = 2 ** np.arange(bits_per_unit - 1, -1, -1, dtype=np.uint8)
    return np.sum(bits * multipliers, axis=1).astype(np.uint8)


def _bits_array_to_bytes(bits: np.ndarray, bits_per_unit: int = 1, total_bits: int = None) -> bytes:
    """
    Convert numpy array of bit groups back to bytes.

    Args:
        bits: Array of bit values
        bits_per_unit: Bits per element in input array
        total_bits: Total number of valid bits (for trimming padding)

    Returns:
        Reconstructed bytes
    """
    if bits_per_unit == 1:
        bit_array = bits
    else:
        # Expand each value to bits_per_unit bits
        bit_array = np.zeros(len(bits) * bits_per_unit, dtype=np.uint8)
        for i in range(bits_per_unit):
            shift = bits_per_unit - 1 - i
            bit_array[i::bits_per_unit] = (bits >> shift) & 1

    # Trim to total_bits if specified
    if total_bits is not None:
        bit_array = bit_array[:total_bits]

    # Pad to multiple of 8
    pad_len = (8 - len(bit_array) % 8) % 8
    if pad_len:
        bit_array = np.concatenate([bit_array, np.zeros(pad_len, dtype=np.uint8)])

    # Pack into bytes
    return np.packbits(bit_array).tobytes()


# ============== PIXEL INDEX GENERATION ==============


def _generate_pixel_indices(
    num_pixels: int, num_needed: int, strategy: EncodingStrategy, seed: int | None = None
) -> np.ndarray:
    """
    Generate pixel indices based on encoding strategy.

    Args:
        num_pixels: Total pixels available
        num_needed: Number of pixels needed
        strategy: Encoding strategy
        seed: Random seed for reproducibility

    Returns:
        Array of pixel indices to use
    """
    if num_needed > num_pixels:
        raise ValueError(f"Not enough pixels: need {num_needed}, have {num_pixels}")

    if strategy == EncodingStrategy.SEQUENTIAL or strategy == EncodingStrategy.INTERLEAVED:
        # Simple sequential indices
        return np.arange(num_needed, dtype=np.uint32)

    elif strategy == EncodingStrategy.SPREAD:
        # Spread evenly across the image
        step = num_pixels / num_needed
        return np.floor(np.arange(num_needed) * step).astype(np.uint32)

    elif strategy == EncodingStrategy.RANDOMIZED:
        # A seeded affine permutation has a stable prefix and costs O(needed),
        # unlike allocating a full permutation for every auto-scan attempt.
        rng = np.random.default_rng(seed or 42)
        start = int(rng.integers(0, num_pixels))
        step = int(rng.integers(1, num_pixels))
        while math.gcd(step, num_pixels) != 1:
            step = 1 if step + 1 >= num_pixels else step + 1
        offsets = np.arange(num_needed, dtype=np.uint64)
        return ((start + offsets * step) % num_pixels).astype(np.uint32)

    return np.arange(num_needed, dtype=np.uint32)


# ============== CAPACITY CALCULATION ==============


def calculate_capacity(image: Image.Image, config: StegConfig) -> dict[str, Any]:
    """Calculate steganographic capacity of an image"""
    width, height = image.size
    total_pixels = width * height

    bits_per_pixel = config.bits_per_pixel
    total_bits = total_pixels * bits_per_pixel
    total_bytes = total_bits // 8

    # Account for header
    header_bits = HEADER_SIZE * 8
    usable_bits = total_bits - header_bits
    usable_bytes = usable_bits // 8

    return {
        "dimensions": (width, height),
        "pixels": total_pixels,
        "bits_total": total_bits,
        "bytes_total": total_bytes,
        "header_bytes": HEADER_SIZE,
        "usable_bits": usable_bits,
        "usable_bytes": max(0, usable_bytes),
        "human": _human_readable_size(max(0, usable_bytes)),
        "config": {
            "channels": [c.name for c in config.channels],
            "bits_per_channel": config.bits_per_channel,
            "bits_per_pixel": bits_per_pixel,
            "strategy": config.strategy.value,
        },
    }


def _human_readable_size(size_bytes: int) -> str:
    """Convert bytes to human readable string"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"
