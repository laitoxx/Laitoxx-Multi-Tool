"""User-facing image steganography method definitions."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec

HAS_OPENCV = find_spec("cv2") is not None


@dataclass(frozen=True, slots=True)
class StegMethod:
    id: str
    label: str
    description: str
    extensions: tuple[str, ...]
    requires_password: bool = False
    extractable: bool = True
    available: bool = True
    unavailable_reason: str = ""


IMAGE_METHODS = (
    StegMethod(
        "LSB", "LSB (Least Significant Bit)", "ST3GG header with selectable channels and bit depth.", (".png", ".bmp")
    ),
    StegMethod(
        "PVD",
        "PVD (Pixel Value Differencing)",
        "Embeds data in differences between neighbouring pixels.",
        (".png", ".bmp"),
    ),
    StegMethod(
        "DCT",
        "DCT (Frequency domain)",
        "Embeds data in 8×8 luminance frequency blocks.",
        (".png", ".jpg", ".jpeg"),
        available=HAS_OPENCV,
        unavailable_reason="OpenCV is not installed." if not HAS_OPENCV else "",
    ),
    StegMethod(
        "SPREAD",
        "Spread Spectrum (password-based)",
        "Uses a password-derived permutation to distribute the ST3GG payload.",
        (".png",),
        True,
    ),
    StegMethod("PALETTE", "Palette (Color index)", "Encodes bits through palette-index parity.", (".png",)),
    StegMethod(
        "CHROMA",
        "Chroma (YCbCr)",
        "Hides two bits per pixel in chroma parity.",
        (".png", ".bmp"),
        available=HAS_OPENCV,
        unavailable_reason="OpenCV is not installed." if not HAS_OPENCV else "",
    ),
    StegMethod(
        "PNGCHUNK", "PNG Chunks (Metadata)", "Stores a validated payload in a PNG ancillary text chunk.", (".png",)
    ),
    StegMethod(
        "F5",
        "F5 (JPEG domain)",
        "Password-keyed JPEG coefficient extraction.",
        (".jpg", ".jpeg"),
        True,
        available=False,
        unavailable_reason="A lossless JPEG coefficient backend is not installed.",
    ),
    StegMethod(
        "TEXTOVERLAY",
        "Text Overlay",
        "Renders low-opacity text into pixels; extraction requires OCR.",
        (".png",),
        extractable=False,
    ),
)

METHOD_BY_ID = {method.id: method for method in IMAGE_METHODS}
AUTO_METHOD_ID = "AUTO"


def get_method(method_id: str) -> StegMethod:
    try:
        return METHOD_BY_ID[method_id.upper()]
    except KeyError as exc:
        raise ValueError(f"Unknown steganography method: {method_id}") from exc


def method_choices(*, include_auto: bool = False) -> list[tuple[str, str]]:
    choices = [(method.id, method.label) for method in IMAGE_METHODS]
    if include_auto:
        choices.insert(0, (AUTO_METHOD_ID, "Try all applicable methods"))
    return choices
