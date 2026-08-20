import numpy as np


def _generate_spread_indices(total_pixels, pixels_needed):
    if pixels_needed > total_pixels:
        raise ValueError("Image capacity exceeded.")
    step = total_pixels / pixels_needed
    return np.floor(np.arange(pixels_needed) * step).astype(np.uint32)


def encode_spread(pixels_rgba, data_bits, channels=[0, 1, 2], bit_offset=0):
    total_pixels = len(pixels_rgba)
    num_channels = len(channels)
    slots_needed = len(data_bits)
    pixels_needed = (slots_needed + num_channels - 1) // num_channels

    pixel_indices = _generate_spread_indices(total_pixels, pixels_needed)

    bit_idx = 0
    for p_idx in pixel_indices:
        for ch in channels:
            if bit_idx >= slots_needed:
                return pixels_rgba

            val = pixels_rgba[p_idx, ch]
            pixels_rgba[p_idx, ch] = (val & (255 - (1 << bit_offset))) | (data_bits[bit_idx] << bit_offset)
            bit_idx += 1

    return pixels_rgba


def decode_spread(pixels_rgba, num_bits_expected, channels=[0, 1, 2], bit_offset=0):
    total_pixels = len(pixels_rgba)
    num_channels = len(channels)
    pixels_needed = (num_bits_expected + num_channels - 1) // num_channels

    pixel_indices = _generate_spread_indices(total_pixels, pixels_needed)
    extracted_bits = np.zeros(num_bits_expected, dtype=np.uint8)

    bit_idx = 0
    for p_idx in pixel_indices:
        for ch in channels:
            if bit_idx >= num_bits_expected:
                return extracted_bits

            val = pixels_rgba[p_idx, ch]
            extracted_bits[bit_idx] = (val >> bit_offset) & 1
            bit_idx += 1

    return extracted_bits
