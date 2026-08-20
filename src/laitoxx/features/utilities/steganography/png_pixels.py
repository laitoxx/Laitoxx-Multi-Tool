"""Focused image steganalysis operations."""

from __future__ import annotations

import io
from typing import Any

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from .analysis_base import FileType, calculate_entropy, detect_file_type


def png_extract_lsb(data: bytes, bits: int = 1, channels: str = "RGB") -> dict[str, Any]:
    """Extract LSB data from PNG image pixels"""
    if not HAS_PIL:
        return {"error": "PIL not available", "found": False}

    try:
        img = Image.open(io.BytesIO(data))

        # Convert to RGBA for consistent processing
        if img.mode == "P":
            img = img.convert("RGBA")
        elif img.mode == "L":
            img = img.convert("RGB")
        elif img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA")

        pixels = list(img.getdata())

        # Extract bits from specified channels
        channel_map = {"R": 0, "G": 1, "B": 2, "A": 3}
        channel_indices = [channel_map[c] for c in channels.upper() if c in channel_map]

        extracted_bits = []
        (1 << bits) - 1

        for pixel in pixels:
            for ch_idx in channel_indices:
                if ch_idx < len(pixel):
                    for bit_pos in range(bits):
                        extracted_bits.append((pixel[ch_idx] >> bit_pos) & 1)

        # Pack into bytes
        result_bytes = bytearray()
        for i in range(0, len(extracted_bits) - 7, 8):
            byte_val = 0
            for j in range(8):
                byte_val |= extracted_bits[i + j] << j
            result_bytes.append(byte_val)

        raw_data = bytes(result_bytes)

        # Look for patterns
        result = {
            "found": True,
            "extracted_size": len(raw_data),
            "channels": channels,
            "bits_per_channel": bits,
            "entropy": calculate_entropy(raw_data[:1024]),
            "raw_data": raw_data,
        }

        # Check for STEG magic
        if raw_data[:4] == b"STEG":
            result["steg_header_found"] = True
            result["suspicious"] = True

        # Check for file signatures
        file_type = detect_file_type(raw_data)
        if file_type != FileType.UNKNOWN:
            result["embedded_file_type"] = file_type.value
            result["suspicious"] = True

        # Check for readable text
        try:
            text = raw_data[:100].decode("utf-8")
            printable = sum(1 for c in text if c.isprintable() or c in "\r\n\t")
            if printable > len(text) * 0.7:
                result["text_preview"] = text
                result["suspicious"] = True
        except Exception:
            pass

        return result

    except Exception as e:
        return {"error": str(e), "found": False}


def png_chi_square_analysis(data: bytes) -> dict[str, Any]:
    """Chi-square analysis to detect LSB manipulation"""
    if not HAS_PIL or not HAS_NUMPY:
        return {"error": "PIL or numpy not available"}

    try:
        img = Image.open(io.BytesIO(data))

        if img.mode == "P":
            img = img.convert("RGB")
        elif img.mode == "L":
            img = img.convert("RGB")
        elif img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        pixels = np.array(img)
        results = {}

        # Analyze each channel
        channel_names = ["Red", "Green", "Blue", "Alpha"]
        for ch_idx in range(min(pixels.shape[2], 4)):
            channel = pixels[:, :, ch_idx].flatten()

            # Pair analysis: count pairs (2k, 2k+1)
            pairs = np.zeros(128)
            for val in channel:
                pair_idx = val // 2
                if pair_idx < 128:
                    pairs[pair_idx] += 1

            # Expected distribution
            total = len(channel)
            expected = total / 128

            # Chi-square for pairs
            chi_sq = sum((pairs[i] - expected) ** 2 / expected for i in range(128) if expected > 0)

            # Also analyze bit plane
            lsb_plane = channel & 1
            ones = np.sum(lsb_plane)
            zeros = total - ones
            expected_ones = total / 2
            lsb_chi_sq = (ones - expected_ones) ** 2 / expected_ones + (zeros - expected_ones) ** 2 / expected_ones

            results[channel_names[ch_idx]] = {
                "chi_square_pairs": float(chi_sq),
                "chi_square_lsb": float(lsb_chi_sq),
                "lsb_ones_ratio": float(ones / total),
                "suspicious": lsb_chi_sq > 3.84,  # 95% confidence threshold
            }

        overall_suspicious = any(r["suspicious"] for r in results.values())

        return {
            "found": True,
            "channels": results,
            "suspicious": overall_suspicious,
            "interpretation": "Low chi-square LSB values may indicate LSB steganography"
            if overall_suspicious
            else "No strong LSB manipulation detected",
        }

    except Exception as e:
        return {"error": str(e), "found": False}


def png_bit_plane_analysis(data: bytes) -> dict[str, Any]:
    """Analyze individual bit planes of PNG image"""
    if not HAS_PIL or not HAS_NUMPY:
        return {"error": "PIL or numpy not available"}

    try:
        img = Image.open(io.BytesIO(data))

        if img.mode == "P":
            img = img.convert("RGB")

        pixels = np.array(img)
        results = {}

        channel_names = ["Red", "Green", "Blue", "Alpha"][: pixels.shape[2] if len(pixels.shape) > 2 else 1]

        if len(pixels.shape) == 2:  # Grayscale
            pixels = pixels.reshape(pixels.shape[0], pixels.shape[1], 1)
            channel_names = ["Gray"]

        for ch_idx, ch_name in enumerate(channel_names):
            channel = pixels[:, :, ch_idx]
            planes = {}

            for bit in range(8):
                plane = (channel >> bit) & 1

                # Calculate entropy of bit plane
                plane_bytes = np.packbits(plane.flatten())
                entropy = calculate_entropy(plane_bytes.tobytes())

                # Calculate percentage of 1s
                ones_pct = np.mean(plane) * 100

                planes[f"bit_{bit}"] = {
                    "entropy": float(entropy),
                    "ones_percentage": float(ones_pct),
                    "suspicious": bit < 2 and (entropy > 7.5 or abs(ones_pct - 50) < 1),
                }

            results[ch_name] = planes

        # Determine overall suspicion
        suspicious = any(
            plane["suspicious"] for channel_planes in results.values() for plane in channel_planes.values()
        )

        return {
            "found": True,
            "channels": results,
            "suspicious": suspicious,
            "interpretation": "High entropy in lower bit planes may indicate hidden data",
        }

    except Exception as e:
        return {"error": str(e), "found": False}
