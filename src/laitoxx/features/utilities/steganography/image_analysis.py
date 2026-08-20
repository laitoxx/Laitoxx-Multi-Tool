"""Image and embedded-format analysis for ST3GG payloads."""

from __future__ import annotations

from typing import Any

import numpy as np
from PIL import Image

from .bit_codec import _bits_array_to_bytes, calculate_capacity
from .decoder import _extract_bit_units
from .models import HEADER_SIZE, MAGIC_BYTES, Channel, StegConfig, StegHeader, derive_magic, get_channel_preset


def analyze_image(image: Image.Image) -> dict[str, Any]:
    """Build an evidence-oriented image analysis report.

    Statistical indicators are deliberately reported as signals rather than
    proof: natural noisy/photographic images can have random-looking LSBs.
    """
    img = image.convert("RGBA")
    pixels = np.array(img, dtype=np.uint8)

    analysis = {
        "dimensions": {"width": img.width, "height": img.height},
        "total_pixels": img.width * img.height,
        "mode": image.mode,
        "format": image.format,
        "channels": {},
        "capacity_by_config": {},
        "detection": {},
    }

    # Analyze each channel
    channel_names = ["R", "G", "B", "A"]
    for i, name in enumerate(channel_names):
        channel_data = pixels[:, :, i].flatten()

        mean_val = float(np.mean(channel_data))
        std_val = float(np.std(channel_data))

        # LSB analysis
        lsb = channel_data & 1
        lsb_zeros = np.sum(lsb == 0)
        lsb_ones = np.sum(lsb == 1)
        total = len(channel_data)

        expected = total / 2
        chi_square = ((lsb_zeros - expected) ** 2 + (lsb_ones - expected) ** 2) / expected

        # Pairs analysis (RS analysis simplified)
        even_pixels = channel_data[::2]
        odd_pixels = channel_data[1::2] if len(channel_data) > 1 else even_pixels

        # Calculate LSB flipping effect
        min_len = min(len(even_pixels), len(odd_pixels))
        diff_original = np.abs(even_pixels[:min_len].astype(np.int16) - odd_pixels[:min_len].astype(np.int16))
        flipped_even = even_pixels[:min_len] ^ 1
        diff_flipped = np.abs(flipped_even.astype(np.int16) - odd_pixels[:min_len].astype(np.int16))

        smoothness_change = np.mean(diff_flipped) - np.mean(diff_original)

        probabilities = np.bincount(channel_data, minlength=256) / total
        nonzero = probabilities[probabilities > 0]
        entropy = float(-np.sum(nonzero * np.log2(nonzero)))
        lsb_balance = 1.0 - abs(float(lsb_ones - lsb_zeros)) / total
        pair_equal = float(np.mean((channel_data[:-1] >> 1) == (channel_data[1:] >> 1))) if total > 1 else 0.0

        analysis["channels"][name] = {
            "mean": mean_val,
            "std": std_val,
            "entropy_bits": entropy,
            "min": int(np.min(channel_data)),
            "max": int(np.max(channel_data)),
            "lsb_ratio": {
                "zeros": lsb_zeros / total,
                "ones": lsb_ones / total,
            },
            "chi_square": float(chi_square),
            "lsb_balance": lsb_balance,
            "adjacent_pair_similarity": pair_equal,
            "smoothness_change": float(smoothness_change),
        }

    color_channels = [analysis["channels"][name] for name in ("R", "G", "B")]
    avg_balance = float(np.mean([channel["lsb_balance"] for channel in color_channels]))
    avg_entropy = float(np.mean([channel["entropy_bits"] for channel in color_channels]))
    avg_smoothness = float(np.mean([abs(channel["smoothness_change"]) for channel in color_channels]))
    score = 0.0
    evidence = []
    if avg_balance > 0.985:
        score += 0.35
        evidence.append("RGB least-significant bits are unusually balanced")
    if avg_entropy > 7.75:
        score += 0.2
        evidence.append("RGB channel entropy is high")
    if avg_smoothness < 0.03:
        score += 0.15
        evidence.append("LSB flipping has little effect on local smoothness")
    alpha = analysis["channels"]["A"]
    if image.mode in {"RGBA", "LA"} and alpha["min"] != alpha["max"] and alpha["lsb_balance"] > 0.98:
        score += 0.2
        evidence.append("Non-uniform alpha channel has balanced LSBs")
    score = min(score, 0.9)
    detection_level = "HIGH" if score >= 0.65 else "MEDIUM" if score >= 0.35 else "LOW"

    analysis["detection"] = {
        "level": detection_level,
        "score": score,
        "evidence": evidence,
        "caveat": "Statistical indicators are not proof; validate by extracting a known header or checksum.",
        "recommendation": "Run opt-in exhaustive extraction" if score >= 0.35 else "No strong statistical indicators",
    }

    # Calculate capacity for common configurations
    for preset_name in ["R", "RGB", "RGBA"]:
        for bits in [1, 2, 4]:
            config = StegConfig(channels=get_channel_preset(preset_name), bits_per_channel=bits)
            cap = calculate_capacity(image, config)
            analysis["capacity_by_config"][f"{preset_name}_{bits}bit"] = cap["human"]

    return analysis


def detect_encoding(image: Image.Image, password: str | None = None) -> dict[str, Any] | None:
    """
    Attempt to detect if image contains STEG-encoded data.

    If password is provided, also checks for password-derived magic bytes
    (stealth mode headers that are undetectable without the password).

    Returns detection info if magic bytes found, None otherwise.
    """
    img = image.convert("RGBA")
    pixels = np.array(img, dtype=np.uint8)
    flat_pixels = pixels.reshape(-1, 4)

    # Exhaustive search - try ALL 15 channel presets × 8 bit depths = 120 combinations
    all_channel_combos = [
        [Channel.R, Channel.G, Channel.B],  # RGB (most common first)
        [Channel.R, Channel.G, Channel.B, Channel.A],  # RGBA
        [Channel.R],  # R
        [Channel.G],  # G
        [Channel.B],  # B
        [Channel.A],  # A
        [Channel.R, Channel.G],  # RG
        [Channel.R, Channel.B],  # RB
        [Channel.R, Channel.A],  # RA
        [Channel.G, Channel.B],  # GB
        [Channel.G, Channel.A],  # GA
        [Channel.B, Channel.A],  # BA
        [Channel.R, Channel.G, Channel.A],  # RGA
        [Channel.R, Channel.B, Channel.A],  # RBA
        [Channel.G, Channel.B, Channel.A],  # GBA
    ]

    configs_to_try = []
    for channels in all_channel_combos:
        for bits in range(1, 9):  # 1-8 bits per channel
            configs_to_try.append(StegConfig(channels=channels, bits_per_channel=bits))

    for config in configs_to_try:
        try:
            header_units = _extract_bit_units(
                flat_pixels, HEADER_SIZE * 8 // config.bits_per_channel + 1, config, len(flat_pixels)
            )
            header_bytes = _bits_array_to_bytes(header_units, config.bits_per_channel, HEADER_SIZE * 8)[:HEADER_SIZE]

            # Check for both fixed magic AND password-derived magic
            expected_magics = [MAGIC_BYTES]
            if password:
                expected_magics.append(derive_magic(password))
            if header_bytes[:4] in expected_magics:
                protected = bool(password and header_bytes[:4] == derive_magic(password))
                header = StegHeader.from_bytes(header_bytes, password if protected else None)
                return {
                    "detected": True,
                    "config": {
                        "channels": [c.name for c in header.config.channels],
                        "bits_per_channel": header.config.bits_per_channel,
                        "strategy": header.config.strategy.value,
                        "compression": header.config.use_compression,
                    },
                    "payload_length": header.payload_length,
                    "original_length": header.original_length,
                }
        except Exception:
            continue

    return None
