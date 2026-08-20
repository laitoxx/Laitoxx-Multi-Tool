"""LSB payload encoder."""

from __future__ import annotations

import zlib

import numpy as np
from PIL import Image

from .bit_codec import _bytes_to_bits_array, _create_bit_mask, _generate_pixel_indices, calculate_capacity
from .models import FORMAT_VERSION, EncodingStrategy, StegConfig, StegHeader


def encode(image: Image.Image, data: bytes, config: StegConfig, output_path: str | None = None) -> Image.Image:
    """
    Encode data into image using LSB steganography.

    Args:
        image: Source PIL Image
        data: Bytes to encode
        config: Steganography configuration
        output_path: Optional path to save result

    Returns:
        Modified PIL Image with embedded data
    """
    # Convert to RGBA numpy array
    img = image.convert("RGBA")
    pixels = np.array(img, dtype=np.uint8)
    height, width = pixels.shape[:2]
    total_pixels = height * width

    # Prepare payload
    original_length = len(data)
    if config.use_compression:
        payload = zlib.compress(data, level=9)
    else:
        payload = data

    payload_length = len(payload)
    crc32 = zlib.crc32(data) & 0xFFFFFFFF

    # Create header
    header = StegHeader(
        version=FORMAT_VERSION,
        config=config,
        payload_length=payload_length,
        original_length=original_length,
        crc32=crc32,
    )
    header_bytes = header.to_bytes()

    # Combine header and payload
    full_data = header_bytes + payload

    # Check capacity
    capacity = calculate_capacity(image, config)
    data_bits_needed = len(full_data) * 8
    if data_bits_needed > capacity["bits_total"]:
        raise ValueError(
            f"Data too large: {len(full_data):,} bytes needed, {capacity['bytes_total']:,} bytes available"
        )

    # Convert data to bit units
    bits_per_ch = config.bits_per_channel
    bit_units = _bytes_to_bits_array(full_data, bits_per_ch)

    # Calculate how many pixel-channel slots we need
    num_channels = len(config.channels)
    channel_indices = config.channel_indices

    if config.strategy == EncodingStrategy.INTERLEAVED:
        # Interleaved: cycle through channels at each pixel
        slots_needed = len(bit_units)
        pixels_needed = (slots_needed + num_channels - 1) // num_channels

        # Generate pixel indices
        pixel_indices = _generate_pixel_indices(total_pixels, pixels_needed, config.strategy, config.seed)

        # Flatten pixels for easier access
        flat_pixels = pixels.reshape(-1, 4)

        # Embed data
        bit_mask = _create_bit_mask(bits_per_ch, config.bit_offset)
        clear_mask = ~bit_mask & 0xFF

        slot_idx = 0
        for pix_idx in pixel_indices:
            for ch in channel_indices:
                if slot_idx >= len(bit_units):
                    break
                # Clear target bits and set new value
                original = flat_pixels[pix_idx, ch]
                value = bit_units[slot_idx]
                flat_pixels[pix_idx, ch] = (original & clear_mask) | (value << config.bit_offset)
                slot_idx += 1
            if slot_idx >= len(bit_units):
                break

        # Reshape back
        pixels = flat_pixels.reshape(height, width, 4)

    else:
        # Sequential or other strategies: process each channel in order
        flat_pixels = pixels.reshape(-1, 4)

        if config.strategy == EncodingStrategy.SEQUENTIAL:
            # Fill each channel completely before moving to next
            bit_mask = _create_bit_mask(bits_per_ch, config.bit_offset)
            clear_mask = ~bit_mask & 0xFF

            slot_idx = 0
            for ch in channel_indices:
                pixel_indices = _generate_pixel_indices(
                    total_pixels, min(total_pixels, len(bit_units) - slot_idx), config.strategy, config.seed
                )
                for pix_idx in pixel_indices:
                    if slot_idx >= len(bit_units):
                        break
                    original = flat_pixels[pix_idx, ch]
                    value = bit_units[slot_idx]
                    flat_pixels[pix_idx, ch] = (original & clear_mask) | (value << config.bit_offset)
                    slot_idx += 1
                if slot_idx >= len(bit_units):
                    break

        else:
            # Spread or randomized with interleaving
            slots_needed = len(bit_units)
            pixels_needed = (slots_needed + num_channels - 1) // num_channels

            pixel_indices = _generate_pixel_indices(total_pixels, pixels_needed, config.strategy, config.seed)

            bit_mask = _create_bit_mask(bits_per_ch, config.bit_offset)
            clear_mask = ~bit_mask & 0xFF

            slot_idx = 0
            for pix_idx in pixel_indices:
                for ch in channel_indices:
                    if slot_idx >= len(bit_units):
                        break
                    original = flat_pixels[pix_idx, ch]
                    value = bit_units[slot_idx]
                    flat_pixels[pix_idx, ch] = (original & clear_mask) | (value << config.bit_offset)
                    slot_idx += 1
                if slot_idx >= len(bit_units):
                    break

        pixels = flat_pixels.reshape(height, width, 4)

    # Create result image
    result = Image.fromarray(pixels, "RGBA")

    if output_path:
        result.save(output_path, format="PNG", optimize=False)

    return result
