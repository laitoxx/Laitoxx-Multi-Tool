"""Focused steganography analysis operations."""

from __future__ import annotations

import struct
import zlib
from typing import Any

from .analysis_base import FileType, calculate_entropy, detect_file_type

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

PNG_CHUNK_TYPES = {
    "IHDR": "Image header",
    "PLTE": "Palette",
    "IDAT": "Image data",
    "IEND": "Image end",
    "tEXt": "Textual data",
    "zTXt": "Compressed textual data",
    "iTXt": "International textual data",
    "bKGD": "Background color",
    "cHRM": "Primary chromaticities",
    "gAMA": "Gamma",
    "hIST": "Palette histogram",
    "iCCP": "ICC profile",
    "pHYs": "Physical pixel dimensions",
    "sBIT": "Significant bits",
    "sPLT": "Suggested palette",
    "sRGB": "Standard RGB color space",
    "tIME": "Last modification time",
    "tRNS": "Transparency",
    "eXIf": "EXIF data",
    "acTL": "Animation control (APNG)",
    "fcTL": "Frame control (APNG)",
    "fdAT": "Frame data (APNG)",
}


def png_parse_chunks(data: bytes) -> dict[str, Any]:
    """Parse all PNG chunks and return detailed information"""
    if not data.startswith(PNG_MAGIC):
        return {"error": "Not a valid PNG file", "valid": False}

    chunks = []
    pos = 8  # Skip magic bytes
    total_idat_size = 0
    chunk_type_counts = {}

    while pos < len(data):
        if pos + 8 > len(data):
            break

        chunk_length = struct.unpack(">I", data[pos : pos + 4])[0]
        chunk_type = data[pos + 4 : pos + 8].decode("ascii", errors="replace")

        if pos + 12 + chunk_length > len(data):
            chunks.append({"type": chunk_type, "offset": pos, "length": chunk_length, "error": "Truncated chunk"})
            break

        chunk_data = data[pos + 8 : pos + 8 + chunk_length]
        stored_crc = struct.unpack(">I", data[pos + 8 + chunk_length : pos + 12 + chunk_length])[0]
        calculated_crc = zlib.crc32(data[pos + 4 : pos + 8 + chunk_length]) & 0xFFFFFFFF

        chunk_info = {
            "type": chunk_type,
            "description": PNG_CHUNK_TYPES.get(chunk_type, "Unknown/Private"),
            "offset": pos,
            "length": chunk_length,
            "crc_valid": stored_crc == calculated_crc,
            "crc_stored": f"{stored_crc:08x}",
            "crc_calculated": f"{calculated_crc:08x}",
        }

        # Track chunk type counts
        chunk_type_counts[chunk_type] = chunk_type_counts.get(chunk_type, 0) + 1

        # Track IDAT size
        if chunk_type == "IDAT":
            total_idat_size += chunk_length

        # Parse IHDR
        if chunk_type == "IHDR" and chunk_length == 13:
            width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
            chunk_info["parsed"] = {
                "width": width,
                "height": height,
                "bit_depth": bit_depth,
                "color_type": color_type,
                "compression": compression,
                "filter": filter_method,
                "interlace": interlace,
            }

        # Parse text chunks
        elif chunk_type == "tEXt":
            null_pos = chunk_data.find(b"\x00")
            if null_pos != -1:
                keyword = chunk_data[:null_pos].decode("latin-1", errors="replace")
                text = chunk_data[null_pos + 1 :].decode("latin-1", errors="replace")
                chunk_info["parsed"] = {"keyword": keyword, "text": text[:500]}

        elif chunk_type == "zTXt":
            null_pos = chunk_data.find(b"\x00")
            if null_pos != -1:
                keyword = chunk_data[:null_pos].decode("latin-1", errors="replace")
                try:
                    text = zlib.decompress(chunk_data[null_pos + 2 :]).decode("latin-1", errors="replace")
                    chunk_info["parsed"] = {"keyword": keyword, "text": text[:500], "compressed": True}
                except Exception:
                    chunk_info["parsed"] = {"keyword": keyword, "error": "Decompression failed"}

        elif chunk_type == "iTXt":
            null_pos = chunk_data.find(b"\x00")
            if null_pos != -1:
                keyword = chunk_data[:null_pos].decode("latin-1", errors="replace")
                chunk_info["parsed"] = {"keyword": keyword}

        # Parse tIME
        elif chunk_type == "tIME" and chunk_length == 7:
            year, month, day, hour, minute, second = struct.unpack(">HBBBBB", chunk_data)
            chunk_info["parsed"] = {
                "timestamp": f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
            }

        # Parse pHYs
        elif chunk_type == "pHYs" and chunk_length == 9:
            ppux, ppuy, unit = struct.unpack(">IIB", chunk_data)
            chunk_info["parsed"] = {
                "pixels_per_unit_x": ppux,
                "pixels_per_unit_y": ppuy,
                "unit": "meter" if unit == 1 else "unknown",
            }

        chunks.append(chunk_info)
        pos += 12 + chunk_length

        if chunk_type == "IEND":
            break

    # Check for data after IEND
    after_iend = len(data) - pos

    return {
        "valid": True,
        "chunks": chunks,
        "chunk_count": len(chunks),
        "chunk_type_counts": chunk_type_counts,
        "total_idat_size": total_idat_size,
        "data_after_iend": after_iend,
        "suspicious": after_iend > 0,
    }


def png_extract_text_chunks(data: bytes) -> dict[str, Any]:
    """Extract all text metadata from PNG"""
    result = png_parse_chunks(data)
    if not result.get("valid"):
        return result

    text_chunks = []
    for chunk in result["chunks"]:
        if chunk["type"] in ("tEXt", "zTXt", "iTXt") and "parsed" in chunk:
            text_chunks.append(
                {
                    "type": chunk["type"],
                    "keyword": chunk["parsed"].get("keyword", ""),
                    "text": chunk["parsed"].get("text", ""),
                    "offset": chunk["offset"],
                }
            )

    return {"found": len(text_chunks) > 0, "text_chunks": text_chunks, "count": len(text_chunks)}


def png_detect_appended_data(data: bytes) -> dict[str, Any]:
    """Detect data appended after PNG IEND chunk"""
    if not data.startswith(PNG_MAGIC):
        return {"found": False, "error": "Not a valid PNG file"}

    # Parse through PNG chunks to find actual IEND position
    pos = 8  # Skip magic
    iend_end_pos = None

    while pos + 8 <= len(data):
        chunk_length = struct.unpack(">I", data[pos : pos + 4])[0]
        chunk_type = data[pos + 4 : pos + 8]

        # Chunk end = pos + 4 (length) + 4 (type) + chunk_length + 4 (CRC)
        chunk_end_pos = pos + 12 + chunk_length

        if chunk_type == b"IEND":
            iend_end_pos = chunk_end_pos
            break

        pos = chunk_end_pos

    if iend_end_pos is None:
        return {"found": False, "error": "No IEND chunk found"}

    if iend_end_pos >= len(data):
        return {"found": False, "appended_size": 0}

    appended_data = data[iend_end_pos:]

    if len(appended_data) == 0:
        return {"found": False, "appended_size": 0}

    # Analyze appended data
    result = {
        "found": True,
        "appended_size": len(appended_data),
        "offset": iend_end_pos,
        "entropy": calculate_entropy(appended_data),
        "preview_hex": appended_data[:64].hex(),
        "suspicious": True,
    }

    # Check if appended data is another file
    file_type = detect_file_type(appended_data)
    if file_type != FileType.UNKNOWN:
        result["embedded_file_type"] = file_type.value

    # Check for printable text
    try:
        text = appended_data[:200].decode("utf-8")
        if all(c.isprintable() or c in "\r\n\t" for c in text):
            result["text_preview"] = text
    except Exception:
        pass

    return result


def png_analyze_idat(data: bytes) -> dict[str, Any]:
    """Analyze PNG IDAT chunks for anomalies"""
    result = png_parse_chunks(data)
    if not result.get("valid"):
        return result

    idat_chunks = []
    prev_end = 0

    for chunk in result["chunks"]:
        if chunk["type"] == "IDAT":
            idat_chunks.append({"offset": chunk["offset"], "length": chunk["length"], "crc_valid": chunk["crc_valid"]})

            # Check for gap between IDAT chunks
            if prev_end > 0 and chunk["offset"] != prev_end:
                gap = chunk["offset"] - prev_end
                if gap > 12:  # More than just the next chunk header
                    idat_chunks[-1]["gap_before"] = gap

            prev_end = chunk["offset"] + 12 + chunk["length"]

    if not idat_chunks:
        return {"found": False, "error": "No IDAT chunks found"}

    total_size = sum(c["length"] for c in idat_chunks)
    sizes = [c["length"] for c in idat_chunks]

    return {
        "found": True,
        "chunk_count": len(idat_chunks),
        "total_size": total_size,
        "chunks": idat_chunks,
        "size_variance": max(sizes) - min(sizes) if len(sizes) > 1 else 0,
        "avg_chunk_size": total_size // len(idat_chunks),
        "all_crc_valid": all(c["crc_valid"] for c in idat_chunks),
        "suspicious": any("gap_before" in c for c in idat_chunks),
    }
