from functools import cmp_to_key

import numpy as np
from PIL import Image


def compare_colors(c1, c2):
    r1, g1, b1 = int(c1[0]), int(c1[1]), int(c1[2])
    r2, g2, b2 = int(c2[0]), int(c2[1]), int(c2[2])

    lum1 = 0.299 * r1 + 0.587 * g1 + 0.114 * b1
    lum2 = 0.299 * r2 + 0.587 * g2 + 0.114 * b2

    if lum1 != lum2:
        return -1 if lum1 < lum2 else 1
    if r1 != r2:
        return r1 - r2
    if g1 != g2:
        return g1 - g2
    return b1 - b2


def encode_palette(image_path, output_path, payload: bytes, num_colors=256):
    img = Image.open(image_path).convert("RGB")

    quantized = img.quantize(colors=num_colors, method=Image.Quantize.MEDIANCUT)
    pixels = np.array(quantized.convert("RGB"))

    flat_pixels = pixels.reshape(-1, 3)
    total_pixels = flat_pixels.shape[0]

    unique_colors = np.unique(flat_pixels, axis=0)
    sorted_palette = sorted(unique_colors, key=cmp_to_key(compare_colors))
    palette_size = len(sorted_palette)

    if palette_size < 2:
        raise ValueError("Image must have at least 2 unique colors for index parity.")

    color_to_idx = {tuple(c): i for i, c in enumerate(sorted_palette)}

    payload_len = len(payload)
    full_payload = payload_len.to_bytes(4, byteorder="big") + payload

    bits = []
    for byte in full_payload:
        for j in range(7, -1, -1):
            bits.append((byte >> j) & 1)

    if palette_size + len(bits) > total_pixels:
        raise ValueError(f"Capacity exceeded. Need {palette_size + len(bits)} pixels, have {total_pixels}.")

    for i in range(palette_size):
        flat_pixels[i] = sorted_palette[i]

    for i in range(len(bits)):
        pixel_idx = palette_size + i
        color = tuple(flat_pixels[pixel_idx])
        idx = color_to_idx[color]

        bit = bits[i]
        if (idx & 1) != bit:
            best_idx = idx ^ 1
            if best_idx >= palette_size:
                best_idx = (idx - 1) if idx > 0 else 1

            flat_pixels[pixel_idx] = sorted_palette[best_idx]

    out_img = Image.fromarray(flat_pixels.reshape(pixels.shape).astype("uint8"), "RGB")
    out_img.save(output_path, format="PNG")


def decode_palette(image_path):
    img = Image.open(image_path).convert("RGB")
    flat_pixels = np.array(img).reshape(-1, 3)

    unique_colors = np.unique(flat_pixels, axis=0)
    sorted_palette = sorted(unique_colors, key=cmp_to_key(compare_colors))
    palette_size = len(sorted_palette)
    color_to_idx = {tuple(c): i for i, c in enumerate(sorted_palette)}

    bits = []
    for i in range(palette_size, flat_pixels.shape[0]):
        color = tuple(flat_pixels[i])
        bits.append(color_to_idx[color] & 1)

    if len(bits) < 32:
        return b""

    length_val = 0
    for i in range(32):
        length_val = (length_val << 1) | bits[i]

    if length_val < 0 or length_val > (len(bits) - 32) // 8:
        bytes_out = bytearray()
        for i in range(0, len(bits) - 7, 8):
            val = 0
            for j in range(8):
                val = (val << 1) | bits[i + j]
            bytes_out.append(val)
        return bytes_out

    bytes_out = bytearray()
    start = 32
    for _ in range(length_val):
        val = 0
        for j in range(8):
            val = (val << 1) | bits[start + j]
        bytes_out.append(val)
        start += 8

    return bytes_out
