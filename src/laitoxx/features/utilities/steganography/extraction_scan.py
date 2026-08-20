"""Exhaustive, opt-in extraction across supported image methods."""

from __future__ import annotations

import base64
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from PIL import Image

from .algorithms import ChromaSteganography, decode_dct, decode_palette, decode_pngchunk, decode_pvd
from .api import create_config
from .crypto import decrypt
from .decoder import decode as decode_lsb
from .models import CHANNEL_PRESETS
from .payload_container import unpack_method_payload


@dataclass(slots=True)
class ExtractionMatch:
    method: str
    parameters: dict[str, object]
    payload: bytes | None = None
    confidence: int = 100
    locked: bool = False
    message: str = ""

    def to_dict(self) -> dict:
        result = asdict(self)
        payload = result.pop("payload")
        if payload is not None:
            result["size"] = len(payload)
            result["payload_base64"] = base64.b64encode(payload).decode("ascii")
            try:
                text = payload.decode("utf-8")
                result["text"] = text
                result["text_preview"] = text[:500]
            except UnicodeDecodeError:
                result["hex_preview"] = payload[:128].hex(" ")
        return result


@dataclass(slots=True)
class ExtractionScan:
    matches: list[ExtractionMatch] = field(default_factory=list)
    attempted: int = 0
    skipped: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "attempted": self.attempted,
            "matches": [match.to_dict() for match in self.matches],
            "skipped": self.skipped,
        }


def _unwrap(data: bytes, method: str, password: str) -> tuple[bytes | None, bool]:
    payload, encrypted = unpack_method_payload(data, method)
    if not encrypted:
        return payload, False
    if not password:
        return None, True
    return decrypt(payload, password), False


ProgressCallback = Callable[[int, int, str], None]


def _try(
    scan: ExtractionScan,
    method: str,
    parameters: dict,
    loader: Callable[[], bytes],
    password: str,
    advance: Callable[[str], None],
) -> None:
    advance(method)
    try:
        raw = loader()
        if not raw:
            return
        payload, locked = _unwrap(bytes(raw), method, password)
        scan.matches.append(
            ExtractionMatch(
                method,
                parameters,
                payload,
                locked=locked,
                message="Password required" if locked else "Validated checksum and method envelope",
            )
        )
    except Exception:
        # Each algorithm is an isolation boundary: malformed carrier data and
        # authentication failures must not abort the remaining scan.
        return


def scan_image(
    image_path: str,
    password: str = "",
    progress: ProgressCallback | None = None,
) -> ExtractionScan:
    """Try all safe method/parameter combinations and return validated matches."""
    path = Path(image_path)
    scan = ExtractionScan()
    total = 360 + (120 if password else 0) + 1 + 9 + 1 + 1 + (3 if path.suffix.lower() == ".png" else 0)

    def advance(label: str) -> None:
        scan.attempted += 1
        if progress:
            progress(scan.attempted, total, label)

    with Image.open(path) as opened:
        opened.load()
        image = opened.copy()

    # ST3GG LSB headers make false positives vanishingly unlikely.  Try every
    # channel set, depth and non-keyed placement strategy.
    for channels in CHANNEL_PRESETS:
        for bits in range(1, 9):
            for strategy in ("interleaved", "sequential", "spread"):
                config = create_config(channels, bits, True, strategy)
                advance(f"LSB {channels}/{bits} {strategy}")
                try:
                    raw = decode_lsb(image, config=config, verify_checksum=True)
                except Exception:
                    continue
                try:
                    payload, locked = _unwrap(raw, "LSB", password)
                except Exception:
                    # Legacy ST3GG payloads had no method envelope.
                    payload, locked = raw, False
                scan.matches.append(
                    ExtractionMatch(
                        "LSB",
                        {"channels": channels, "bits": bits, "strategy": strategy},
                        payload,
                        locked=locked,
                        message="Password required" if locked else "Validated ST3GG header and checksum",
                    )
                )

    if password:
        seed = int.from_bytes(__import__("hashlib").sha256(password.encode()).digest()[:4], "big") or 1
        for channels in CHANNEL_PRESETS:
            for bits in range(1, 9):
                config = create_config(channels, bits, True, "randomized", seed=seed)
                advance(f"SPREAD {channels}/{bits}")
                try:
                    raw = decode_lsb(image, config=config, verify_checksum=True)
                    payload, encrypted = unpack_method_payload(raw, "SPREAD")
                    scan.matches.append(
                        ExtractionMatch(
                            "SPREAD",
                            {"channels": channels, "bits": bits},
                            decrypt(payload, password) if encrypted else payload,
                        )
                    )
                except Exception:
                    continue
    else:
        scan.skipped.append({"method": "SPREAD", "reason": "Password is required"})

    _try(scan, "DCT", {}, lambda: decode_dct(str(path)), password, advance)
    for direction in ("horizontal", "vertical", "both"):
        for range_type in ("wu-tsai", "wide", "narrow"):
            _try(
                scan,
                "PVD",
                {"direction": direction, "range": range_type},
                lambda d=direction, r=range_type: decode_pvd(str(path), d, r),
                password,
                advance,
            )
    _try(scan, "PALETTE", {}, lambda: bytes(decode_palette(str(path))), password, advance)
    if ChromaSteganography is not None:
        _try(
            scan,
            "CHROMA",
            {"space": "YCbCr", "channels": "Cb+Cr"},
            lambda: ChromaSteganography().decode(str(path)),
            password,
            advance,
        )
    else:
        advance("CHROMA unavailable")
    if path.suffix.lower() == ".png":
        for keyword in ("stEg", "Comment", "Description"):
            _try(
                scan,
                "PNGCHUNK",
                {"keyword": keyword},
                lambda k=keyword: bytes.fromhex(decode_pngchunk(str(path), k)),
                password,
                advance,
            )
    scan.skipped.append(
        {
            "method": "F5",
            "reason": (
                "Password is required" if not password else "A lossless JPEG coefficient backend is not installed"
            ),
        }
    )
    scan.skipped.append({"method": "TEXTOVERLAY", "reason": "OCR output cannot be checksum-validated automatically"})
    unique = {}
    for match in scan.matches:
        key = (match.method, match.payload, match.locked)
        unique.setdefault(key, match)
    scan.matches = list(unique.values())
    return scan
