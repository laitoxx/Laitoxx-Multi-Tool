"""LSB payload decoder."""

from __future__ import annotations

import zlib

import numpy as np
from PIL import Image

from .bit_codec import _bits_array_to_bytes, _create_bit_mask, _generate_pixel_indices
from .models import HEADER_SIZE, Channel, EncodingStrategy, StegConfig, StegHeader


def decode(image: Image.Image, config: StegConfig | None = None, verify_checksum: bool = True) -> bytes:
    """
    Decode data from image using LSB steganography.

    Args:
        image: PIL Image with embedded data
        config: Optional config (if None, auto-detect from header)
        verify_checksum: Whether to verify CRC32 checksum

    Returns:
        Extracted bytes
    """
    # Convert to RGBA numpy array
    img = image.convert("RGBA")
    pixels = np.array(img, dtype=np.uint8)
    height, width = pixels.shape[:2]
    total_pixels = height * width
    flat_pixels = pixels.reshape(-1, 4)

    # First, we need to extract the header to get config
    if config is None:
        from .image_analysis import detect_encoding

        # Auto-detect: exhaustive search across all channel/bit combos
        detected = detect_encoding(image)
        if detected:
            # Reconstruct config from detection result
            channel_map = {"R": Channel.R, "G": Channel.G, "B": Channel.B, "A": Channel.A}
            channels = [channel_map[c] for c in detected["config"]["channels"]]
            header_config = StegConfig(channels=channels, bits_per_channel=detected["config"]["bits_per_channel"])
        else:
            # Fallback to default
            header_config = StegConfig()
    else:
        header_config = config

    # Extract header bytes
    header_bits_needed = HEADER_SIZE * 8
    header_units_needed = header_bits_needed // header_config.bits_per_channel
    if header_bits_needed % header_config.bits_per_channel:
        header_units_needed += 1

    header_units = _extract_bit_units(flat_pixels, header_units_needed, header_config, total_pixels)

    header_bytes = _bits_array_to_bytes(header_units, header_config.bits_per_channel, header_bits_needed)[:HEADER_SIZE]

    # Parse header
    try:
        header = StegHeader.from_bytes(header_bytes)
    except ValueError as e:
        raise ValueError(f"Failed to decode header: {e}. Image may not contain encoded data or config mismatch.") from e

    # Use config from header if not provided
    actual_config = config if config else header.config

    # Now extract the full payload using actual config
    total_data_len = HEADER_SIZE + header.payload_length
    total_bits_needed = total_data_len * 8
    total_units_needed = total_bits_needed // actual_config.bits_per_channel
    if total_bits_needed % actual_config.bits_per_channel:
        total_units_needed += 1

    all_units = _extract_bit_units(flat_pixels, total_units_needed, actual_config, total_pixels)

    all_bytes = _bits_array_to_bytes(all_units, actual_config.bits_per_channel, total_bits_needed)

    # Extract payload (skip header)
    payload = all_bytes[HEADER_SIZE : HEADER_SIZE + header.payload_length]

    if len(payload) < header.payload_length:
        raise ValueError(f"Incomplete payload: got {len(payload)}, expected {header.payload_length}")

    # Decompress if needed
    if actual_config.use_compression:
        try:
            data = zlib.decompress(payload)
        except zlib.error as e:
            raise ValueError(f"Decompression failed: {e}") from e
    else:
        data = payload

    # Verify length
    if len(data) != header.original_length:
        raise ValueError(f"Length mismatch: got {len(data)}, expected {header.original_length}")

    # Verify checksum
    if verify_checksum:
        actual_crc = zlib.crc32(data) & 0xFFFFFFFF
        if actual_crc != header.crc32:
            raise ValueError(
                f"Checksum mismatch: got {actual_crc:08x}, expected {header.crc32:08x}. Data may be corrupted."
            )

    return data


def _extract_bit_units(flat_pixels: np.ndarray, num_units: int, config: StegConfig, total_pixels: int) -> np.ndarray:
    """
    Extract bit units from pixel array.

    Args:
        flat_pixels: Flattened pixel array (N, 4)
        num_units: Number of bit units to extract
        config: Steganography configuration
        total_pixels: Total number of pixels

    Returns:
        Array of extracted bit values
    """
    channel_indices = config.channel_indices
    num_channels = len(channel_indices)
    bits_per_ch = config.bits_per_channel
    bit_offset = config.bit_offset
    bit_mask = _create_bit_mask(bits_per_ch, bit_offset)

    result = np.zeros(num_units, dtype=np.uint8)

    if config.strategy == EncodingStrategy.INTERLEAVED:
        pixels_needed = (num_units + num_channels - 1) // num_channels
        pixel_indices = _generate_pixel_indices(total_pixels, pixels_needed, config.strategy, config.seed)

        unit_idx = 0
        for pix_idx in pixel_indices:
            for ch in channel_indices:
                if unit_idx >= num_units:
                    break
                value = flat_pixels[pix_idx, ch]
                result[unit_idx] = (value & bit_mask) >> bit_offset
                unit_idx += 1
            if unit_idx >= num_units:
                break

    elif config.strategy == EncodingStrategy.SEQUENTIAL:
        unit_idx = 0
        for ch in channel_indices:
            pixel_indices = _generate_pixel_indices(
                total_pixels, min(total_pixels, num_units - unit_idx), config.strategy, config.seed
            )
            for pix_idx in pixel_indices:
                if unit_idx >= num_units:
                    break
                value = flat_pixels[pix_idx, ch]
                result[unit_idx] = (value & bit_mask) >> bit_offset
                unit_idx += 1
            if unit_idx >= num_units:
                break

    else:
        # Spread or randomized
        pixels_needed = (num_units + num_channels - 1) // num_channels
        pixel_indices = _generate_pixel_indices(total_pixels, pixels_needed, config.strategy, config.seed)

        unit_idx = 0
        for pix_idx in pixel_indices:
            for ch in channel_indices:
                if unit_idx >= num_units:
                    break
                value = flat_pixels[pix_idx, ch]
                result[unit_idx] = (value & bit_mask) >> bit_offset
                unit_idx += 1
            if unit_idx >= num_units:
                break

    return result
