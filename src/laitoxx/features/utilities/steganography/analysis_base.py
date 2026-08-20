"""Focused steganography analysis operations."""

from __future__ import annotations

import math
from dataclasses import field
from enum import Enum
from typing import Any


class AnalysisResult:
    """Standard result format for all analysis functions"""

    success: bool
    action: str
    file_type: str
    data: dict[str, Any] = field(default_factory=dict)
    findings: list[str] = field(default_factory=list)
    suspicious: bool = False
    confidence: float = 0.0
    raw_data: bytes | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "action": self.action,
            "file_type": self.file_type,
            "data": self.data,
            "findings": self.findings,
            "suspicious": self.suspicious,
            "confidence": self.confidence,
            "has_raw_data": self.raw_data is not None,
            "error": self.error,
        }


class FileType(Enum):
    PNG = "png"
    JPEG = "jpeg"
    GIF = "gif"
    BMP = "bmp"
    WEBP = "webp"
    TIFF = "tiff"
    ICO = "ico"
    HEIC = "heic"
    AVIF = "avif"
    SVG = "svg"
    WAV = "wav"
    MP3 = "mp3"
    FLAC = "flac"
    OGG = "ogg"
    AVI = "avi"
    MKV = "mkv"
    PDF = "pdf"
    OFFICE = "office"
    ZIP = "zip"
    RAR = "rar"
    FONT = "font"
    AIFF = "aiff"
    AU = "au"
    MIDI = "midi"
    PCAP = "pcap"
    SQLITE = "sqlite"
    GZIP = "gzip"
    TAR = "tar"
    UNKNOWN = "unknown"


# Magic bytes for file type detection
MAGIC_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": FileType.PNG,
    b"\xff\xd8\xff": FileType.JPEG,
    b"GIF87a": FileType.GIF,
    b"GIF89a": FileType.GIF,
    b"BM": FileType.BMP,
    b"RIFF": FileType.WAV,  # Could also be AVI - check further
    b"\xff\xfb": FileType.MP3,
    b"\xff\xfa": FileType.MP3,
    b"\xff\xf3": FileType.MP3,
    b"\xff\xf2": FileType.MP3,
    b"ID3": FileType.MP3,
    b"fLaC": FileType.FLAC,
    b"OggS": FileType.OGG,
    b"%PDF": FileType.PDF,
    b"PK\x03\x04": FileType.ZIP,  # Could be Office - check further
    b"Rar!\x1a\x07": FileType.RAR,
    b"\x1aE\xdf\xa3": FileType.MKV,
    b"\x00\x00\x01\x00": FileType.ICO,
    b"\x00\x00\x02\x00": FileType.ICO,  # CUR format
    b"\x1f\x8b": FileType.GZIP,
    b"MThd": FileType.MIDI,
    b".snd": FileType.AU,
    b"\xa1\xb2\xc3\xd4": FileType.PCAP,
    b"\xd4\xc3\xb2\xa1": FileType.PCAP,  # Little-endian PCAP
    b"SQLite format 3": FileType.SQLITE,
}

WEBP_SIGNATURES = [b"WEBP"]
HEIC_SIGNATURES = [b"ftyp", b"heic", b"heix", b"hevc", b"mif1"]
AVIF_SIGNATURES = [b"ftypavif", b"ftypavis"]


def detect_file_type(data: bytes) -> FileType:
    """Detect file type from magic bytes"""
    if len(data) < 12:
        return FileType.UNKNOWN

    # Check standard signatures
    for magic, ftype in MAGIC_SIGNATURES.items():
        if data.startswith(magic):
            # Special handling for RIFF container
            if magic == b"RIFF" and len(data) >= 12:
                if data[8:12] == b"WAVE":
                    return FileType.WAV
                elif data[8:12] == b"AVI ":
                    return FileType.AVI
                elif data[8:12] == b"WEBP":
                    return FileType.WEBP
            # Special handling for ZIP-based formats
            elif magic == b"PK\x03\x04":
                # Check if it's an Office document
                if (
                    b"[Content_Types].xml" in data[:2000]
                    or b"word/" in data[:2000]
                    or b"xl/" in data[:2000]
                    or b"ppt/" in data[:2000]
                ):
                    return FileType.OFFICE
                return FileType.ZIP
            return ftype

    # Check for HEIC/AVIF (ftyp box)
    if len(data) >= 12 and data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in [b"heic", b"heix", b"hevc", b"mif1"]:
            return FileType.HEIC
        elif brand in [b"avif", b"avis"]:
            return FileType.AVIF

    # Check for TIFF (II = little-endian, MM = big-endian)
    if data[:4] in [b"II\x2a\x00", b"MM\x00\x2a"]:
        return FileType.TIFF

    # Check for AIFF (FORM container with AIFF type)
    if data[:4] == b"FORM" and len(data) >= 12:
        if data[8:12] == b"AIFF" or data[8:12] == b"AIFC":
            return FileType.AIFF

    # Check for TAR (magic at offset 257)
    if len(data) >= 265 and data[257:262] == b"ustar":
        return FileType.TAR

    # Check for SVG
    if b"<svg" in data[:1000] or b"<?xml" in data[:100] and b"<svg" in data[:2000]:
        return FileType.SVG

    # Check for fonts
    if data[:4] in [b"\x00\x01\x00\x00", b"OTTO", b"true", b"typ1"]:
        return FileType.FONT
    if data[:4] == b"wOFF" or data[:4] == b"wOF2":
        return FileType.FONT

    return FileType.UNKNOWN


def calculate_entropy(data: bytes) -> float:
    """Calculate Shannon entropy of data"""
    if not data:
        return 0.0

    byte_counts = [0] * 256
    for byte in data:
        byte_counts[byte] += 1

    length = len(data)
    entropy = 0.0
    for count in byte_counts:
        if count > 0:
            p = count / length
            entropy -= p * math.log2(p)

    return entropy


def calculate_chi_square(data: bytes) -> float:
    """Calculate chi-square statistic for randomness test"""
    if not data:
        return 0.0

    byte_counts = [0] * 256
    for byte in data:
        byte_counts[byte] += 1

    expected = len(data) / 256
    chi_square = sum((count - expected) ** 2 / expected for count in byte_counts)
    return chi_square


def find_strings(data: bytes, min_length: int = 4) -> list[tuple[int, str]]:
    """Extract printable ASCII strings from binary data"""
    strings = []
    current = []
    start_offset = 0

    for i, byte in enumerate(data):
        if 32 <= byte < 127:
            if not current:
                start_offset = i
            current.append(chr(byte))
        else:
            if len(current) >= min_length:
                strings.append((start_offset, "".join(current)))
            current = []

    if len(current) >= min_length:
        strings.append((start_offset, "".join(current)))

    return strings


def hex_dump(data: bytes, offset: int = 0, length: int = 256) -> str:
    """Create hex dump of data"""
    result = []
    chunk = data[offset : offset + length]

    for i in range(0, len(chunk), 16):
        line_data = chunk[i : i + 16]
        hex_part = " ".join(f"{b:02x}" for b in line_data)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in line_data)
        result.append(f"{offset + i:08x}  {hex_part:<48}  {ascii_part}")

    return "\n".join(result)
