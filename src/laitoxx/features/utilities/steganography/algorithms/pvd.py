# PVD Steganography Implementation
import math

import numpy as np
from PIL import Image

PVD_RANGES = {
    "wu-tsai": [
        {"lower": 0, "upper": 7, "bits": 3},
        {"lower": 8, "upper": 15, "bits": 3},
        {"lower": 16, "upper": 31, "bits": 4},
        {"lower": 32, "upper": 63, "bits": 5},
        {"lower": 64, "upper": 127, "bits": 6},
        {"lower": 128, "upper": 255, "bits": 7},
    ],
    "wide": [
        {"lower": 0, "upper": 15, "bits": 4},
        {"lower": 16, "upper": 47, "bits": 5},
        {"lower": 48, "upper": 111, "bits": 6},
        {"lower": 112, "upper": 255, "bits": 7},
    ],
    "narrow": [
        {"lower": 0, "upper": 3, "bits": 2},
        {"lower": 4, "upper": 7, "bits": 2},
        {"lower": 8, "upper": 15, "bits": 3},
        {"lower": 16, "upper": 31, "bits": 4},
        {"lower": 32, "upper": 63, "bits": 5},
        {"lower": 64, "upper": 127, "bits": 6},
        {"lower": 128, "upper": 255, "bits": 7},
    ],
}


def find_pvd_range(diff, ranges):
    abs_diff = abs(diff)
    for r in ranges:
        if r["lower"] <= abs_diff <= r["upper"]:
            return r
    return ranges[-1]


def get_pixel_pairs(width, height, direction):
    pairs = []
    if direction in ("horizontal", "both"):
        for row in range(height):
            for col in range(0, width - 1, 2):
                pairs.append(((row, col), (row, col + 1)))
    if direction in ("vertical", "both"):
        for row in range(0, height - 1, 2):
            for col in range(width):
                pairs.append(((row, col), (row + 1, col)))
    return pairs


def encode_pvd(image_path, output_path, data: bytes, direction="horizontal", range_type="wu-tsai"):
    img = Image.open(image_path).convert("RGB")
    pixels = np.array(img, dtype=np.int32)
    height, width, _ = pixels.shape

    ranges = PVD_RANGES[range_type]

    data_len = len(data)
    header = data_len.to_bytes(4, byteorder="big")
    full_data = header + data

    bits = []
    for b in full_data:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)

    pairs = get_pixel_pairs(width, height, direction)
    bit_idx = 0

    for (r1, c1), (r2, c2) in pairs:
        if bit_idx >= len(bits):
            break

        for c in range(3):
            if bit_idx >= len(bits):
                break

            p1 = int(pixels[r1, c1, c])
            p2 = int(pixels[r2, c2, c])
            diff = p1 - p2
            r_info = find_pvd_range(diff, ranges)

            bits_to_embed = min(r_info["bits"], len(bits) - bit_idx)
            if bits_to_embed <= 0:
                continue

            embed_value = 0
            for _ in range(bits_to_embed):
                embed_value = (embed_value << 1) | bits[bit_idx]
                bit_idx += 1

            embed_value <<= r_info["bits"] - bits_to_embed

            new_diff = r_info["lower"] + embed_value
            signed_new_diff = new_diff if diff >= 0 else -new_diff

            diff_change = signed_new_diff - diff

            new_p1 = p1 + math.ceil(diff_change / 2.0)
            new_p2 = p2 - math.floor(diff_change / 2.0)

            if new_p1 < 0:
                new_p2 += -new_p1
                new_p1 = 0
            if new_p2 < 0:
                new_p1 += -new_p2
                new_p2 = 0
            if new_p1 > 255:
                new_p2 -= new_p1 - 255
                new_p1 = 255
            if new_p2 > 255:
                new_p1 -= new_p2 - 255
                new_p2 = 255

            new_p1 = max(0, min(255, new_p1))
            new_p2 = max(0, min(255, new_p2))

            pixels[r1, c1, c] = new_p1
            pixels[r2, c2, c] = new_p2

    if bit_idx < len(bits):
        raise ValueError("Data too large to embed in this image with the given PVD settings.")

    encoded_img = Image.fromarray(np.uint8(pixels))
    encoded_img.save(output_path)


def decode_pvd(image_path, direction="horizontal", range_type="wu-tsai"):
    img = Image.open(image_path).convert("RGB")
    pixels = np.array(img, dtype=np.int32)
    height, width, _ = pixels.shape

    ranges = PVD_RANGES[range_type]
    pairs = get_pixel_pairs(width, height, direction)

    bits = []
    max_bits = 32 + 8 * 1000000

    for (r1, c1), (r2, c2) in pairs:
        if len(bits) >= max_bits:
            break
        for c in range(3):
            if len(bits) >= max_bits:
                break

            p1 = int(pixels[r1, c1, c])
            p2 = int(pixels[r2, c2, c])
            diff = abs(p1 - p2)
            r_info = find_pvd_range(diff, ranges)

            embed_value = diff - r_info["lower"]

            for b in range(r_info["bits"] - 1, -1, -1):
                bits.append((embed_value >> b) & 1)

    if len(bits) < 32:
        return b""

    length = 0
    for i in range(32):
        length = (length << 1) | bits[i]

    if length <= 0 or length > 1000000:
        return b""

    if len(bits) < 32 + length * 8:
        return b""

    out = bytearray()
    bit_idx = 32
    for _ in range(length):
        byte = 0
        for _ in range(8):
            byte = (byte << 1) | bits[bit_idx]
            bit_idx += 1
        out.append(byte)

    return bytes(out)
