"""Focused image steganalysis operations."""

from __future__ import annotations

import io
import struct
import zlib
from typing import Any

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from .png_structure import PNG_MAGIC, png_parse_chunks


def gif_analysis(data: bytes) -> dict[str, Any]:
    """Analyze GIF files for steganography - comment blocks, palette LSB, disposal methods"""
    if not HAS_PIL:
        return {"error": "PIL not available"}

    results = {
        "found": False,
        "findings": [],
        "comment_blocks": [],
        "palette_lsb_decode": None,
        "disposal_methods": [],
    }

    try:
        # 1. Extract GIF comment extension blocks from raw data
        pos = 0
        while pos < len(data) - 2:
            if data[pos] == 0x21 and data[pos + 1] == 0xFE:  # Comment extension
                pos += 2
                comment = bytearray()
                while pos < len(data) and data[pos] != 0:
                    block_len = data[pos]
                    pos += 1
                    comment.extend(data[pos : pos + block_len])
                    pos += block_len
                pos += 1  # Skip terminator
                try:
                    decoded = comment.decode("utf-8", errors="replace")
                    results["comment_blocks"].append(decoded)
                    results["found"] = True
                    results["findings"].append(f"Comment block: {decoded[:100]}")
                except Exception:
                    results["comment_blocks"].append(comment.hex())
                continue
            pos += 1

        # 2. Extract disposal method bits from GCE blocks
        pos = 0
        while pos < len(data) - 5:
            if data[pos] == 0x21 and data[pos + 1] == 0xF9 and data[pos + 2] == 0x04:
                packed = data[pos + 3]
                disposal = (packed >> 2) & 0x07
                results["disposal_methods"].append(disposal)
                pos += 6
            else:
                pos += 1

        if len(results["disposal_methods"]) > 1:
            results["findings"].append(f"Disposal methods: {results['disposal_methods'][:20]}")

        # 3. Palette index LSB decode
        img = Image.open(io.BytesIO(data))
        if img.mode == "P":
            pixel_indices = list(img.getdata())
            bits = [idx & 1 for idx in pixel_indices]

            if len(bits) >= 32:
                length = 0
                for i in range(32):
                    length = (length << 1) | bits[i]

                if 0 < length < min(5000, (len(bits) - 32) // 8):
                    msg_bits = bits[32 : 32 + length * 8]
                    msg_bytes = bytearray()
                    for i in range(0, len(msg_bits), 8):
                        v = 0
                        for j in range(8):
                            if i + j < len(msg_bits):
                                v = (v << 1) | msg_bits[i + j]
                        msg_bytes.append(v)
                    try:
                        decoded_msg = msg_bytes.decode("utf-8", errors="replace")
                        results["palette_lsb_decode"] = {
                            "length": length,
                            "message": decoded_msg[:200],
                            "method": "palette_index_lsb",
                        }
                        results["found"] = True
                        results["findings"].append(f"Palette LSB decode ({length} bytes): {decoded_msg[:50]}")
                    except Exception:
                        pass

        results["suspicious"] = results["found"]
        return results

    except Exception as e:
        return {"error": str(e), "found": False}


def bmp_analysis(data: bytes) -> dict[str, Any]:
    """Analyze BMP files for steganography - reserved header fields, trailing data, LSB"""
    results = {
        "found": False,
        "findings": [],
        "reserved_bytes": None,
        "trailing_data": None,
        "lsb_decode": None,
    }

    if len(data) < 54:
        return {"error": "File too small for BMP", "found": False}

    if data[:2] != b"BM":
        return {"error": "Not a BMP file", "found": False}

    try:
        # Check reserved bytes at offset 6-9 (should be zero in clean BMPs)
        reserved = data[6:10]
        if reserved != b"\x00\x00\x00\x00":
            results["reserved_bytes"] = reserved.hex()
            results["found"] = True
            results["findings"].append(f"Non-zero reserved bytes: {reserved.hex()}")

        # Check for trailing data after pixel data
        file_size = struct.unpack("<I", data[2:6])[0]
        actual_size = len(data)
        if actual_size > file_size:
            trailing = data[file_size:]
            results["trailing_data"] = {
                "size": actual_size - file_size,
                "preview": trailing[:200].decode("utf-8", errors="replace"),
            }
            results["found"] = True
            results["findings"].append(f"Trailing data: {actual_size - file_size} bytes after BMP end")

        # LSB decode via PIL
        if HAS_PIL:
            img = Image.open(io.BytesIO(data)).convert("RGBA")
            pixels = list(img.getdata())
            bits = []
            for r, g, b, _a in pixels:
                for ch in [r, g, b]:
                    bits.append(ch & 1)

            if len(bits) >= 32:
                length = 0
                for i in range(32):
                    length = (length << 1) | bits[i]

                if 0 < length < min(5000, (len(bits) - 32) // 8):
                    msg_bits = bits[32 : 32 + length * 8]
                    msg_bytes = bytearray()
                    for i in range(0, len(msg_bits), 8):
                        v = 0
                        for j in range(8):
                            if i + j < len(msg_bits):
                                v = (v << 1) | msg_bits[i + j]
                        msg_bytes.append(v)
                    try:
                        decoded = msg_bytes.decode("utf-8", errors="replace")
                        results["lsb_decode"] = {"length": length, "message": decoded[:200], "method": "rgb_lsb"}
                        results["found"] = True
                        results["findings"].append(f"LSB decode ({length} bytes): {decoded[:50]}")
                    except Exception:
                        pass

        results["suspicious"] = results["found"]
        return results

    except Exception as e:
        return {"error": str(e), "found": False}


def png_filter_analysis(data: bytes) -> dict[str, Any]:
    """Analyze PNG filter bytes for anomalies"""
    result = png_parse_chunks(data)
    if not result.get("valid"):
        return result

    # Need to decompress IDAT to get filter bytes
    idat_data = b""
    ihdr_data = None

    for chunk in result["chunks"]:
        if chunk["type"] == "IDAT":
            offset = chunk["offset"]
            length = chunk["length"]
            idat_data += data[offset + 8 : offset + 8 + length]
        elif chunk["type"] == "IHDR" and "parsed" in chunk:
            ihdr_data = chunk["parsed"]

    if not ihdr_data:
        return {"error": "No IHDR chunk found"}

    try:
        decompressed = zlib.decompress(idat_data)
    except Exception:
        return {"error": "Failed to decompress IDAT"}

    # Calculate bytes per row
    width = ihdr_data["width"]
    height = ihdr_data["height"]
    bit_depth = ihdr_data["bit_depth"]
    color_type = ihdr_data["color_type"]

    # Samples per pixel based on color type
    samples = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type, 3)
    bytes_per_pixel = max(1, (samples * bit_depth) // 8)
    row_bytes = 1 + width * bytes_per_pixel  # +1 for filter byte

    # Extract filter bytes
    filter_bytes = []
    for row in range(height):
        offset = row * row_bytes
        if offset < len(decompressed):
            filter_bytes.append(decompressed[offset])

    # Analyze filter distribution
    filter_counts = {}
    for f in filter_bytes:
        filter_counts[f] = filter_counts.get(f, 0) + 1

    filter_names = {0: "None", 1: "Sub", 2: "Up", 3: "Average", 4: "Paeth"}

    return {
        "found": True,
        "row_count": len(filter_bytes),
        "filter_distribution": {filter_names.get(k, f"Unknown({k})"): v for k, v in filter_counts.items()},
        "unique_filters": len(filter_counts),
        "suspicious": 0 in filter_counts and filter_counts[0] > len(filter_bytes) * 0.9,
        "interpretation": "Excessive use of filter 0 (None) may indicate modified image",
    }


def png_detect_embedded_png(data: bytes) -> dict[str, Any]:
    """Detect PNG files embedded within PNG (nested steganography)"""
    results = {"found": False, "embedded_pngs": []}

    # Look for PNG magic in various locations
    search_start = 8  # Skip the outer PNG magic

    while True:
        pos = data.find(PNG_MAGIC, search_start)
        if pos == -1:
            break

        # Try to parse as PNG
        try:
            end_pos = data.find(b"IEND", pos)
            if end_pos != -1:
                # IEND + length (0) + CRC = +8 bytes
                end_pos += 12
                embedded_size = end_pos - pos

                results["embedded_pngs"].append(
                    {
                        "offset": pos,
                        "size": embedded_size,
                        "location": "after_iend" if pos > data.rfind(b"IEND", 0, pos) else "within_image",
                    }
                )
                results["found"] = True
        except Exception:
            pass

        search_start = pos + 1

    results["count"] = len(results["embedded_pngs"])
    results["suspicious"] = results["found"]

    return results
