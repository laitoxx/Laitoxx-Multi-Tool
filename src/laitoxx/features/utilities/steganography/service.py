"""Application service for image steganography and steganalysis."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from .algorithms import (
    ChromaSteganography,
    decode_dct,
    decode_palette,
    decode_pngchunk,
    decode_pvd,
    decode_textoverlay,
    encode_dct,
    encode_palette,
    encode_pngchunk,
    encode_pvd,
    encode_textoverlay,
)
from .api import create_config
from .archive_decoders import jpeg_decode
from .bit_codec import calculate_capacity
from .crypto import decrypt, encrypt
from .decoder import decode as decode_lsb
from .encoder import encode as encode_lsb
from .extraction_scan import scan_image
from .image_analysis import analyze_image, detect_encoding
from .image_formats import bmp_analysis, gif_analysis
from .method_catalog import IMAGE_METHODS, get_method
from .payload_container import pack_method_payload, unpack_method_payload
from .png_reporting import png_full_analysis


@dataclass(frozen=True, slots=True)
class StegOptions:
    method: str = "LSB"
    channels: str = "RGB"
    bits: int = 1
    compress: bool = True
    strategy: str = "interleaved"
    robustness: str = "medium"
    pvd_direction: str = "horizontal"
    pvd_range: str = "wu-tsai"
    palette_colors: int = 256
    png_keyword: str = "stEg"

    def to_engine_config(self, *, seed: int | None = None, strategy: str | None = None):
        return create_config(
            channels=self.channels,
            bits=self.bits,
            compress=self.compress,
            strategy=strategy or self.strategy,
            seed=seed,
        )


class SteganographyService:
    @staticmethod
    def _password_seed(password: str) -> int:
        return int.from_bytes(hashlib.sha256(password.encode("utf-8")).digest()[:4], "big") or 1

    @staticmethod
    def _pack(method: str, payload: bytes, password: str) -> bytes:
        body = encrypt(payload, password) if password else payload
        return pack_method_payload(method, body, encrypted=bool(password))

    @staticmethod
    def _unpack(method: str, data: bytes, password: str) -> bytes:
        try:
            payload, encrypted = unpack_method_payload(data, method)
        except ValueError:
            # Compatibility with images produced before the method envelope.
            return decrypt(data, password) if password else data
        if encrypted and not password:
            raise ValueError(f"{method} payload is encrypted; enter the password")
        if not encrypted:
            return payload
        try:
            return decrypt(payload, password)
        except Exception as exc:
            raise ValueError("Wrong password or corrupted encrypted payload") from exc

    def capacity(self, image_path: str, options: StegOptions) -> int:
        method = options.method.upper()
        with Image.open(image_path) as image:
            width, height = image.size
            if method in {"LSB", "SPREAD"}:
                return int(calculate_capacity(image, options.to_engine_config())["usable_bytes"])
            if method == "DCT":
                return max(0, ((width // 8) * (height // 8)) // 8 - 32)
            if method == "PVD":
                return max(0, width * height * 3 // 4 - 32)
            if method == "PALETTE":
                return max(0, width * height // 8 - options.palette_colors - 32)
            if method == "CHROMA":
                return max(0, width * height // 4 - 32)
            if method in {"PNGCHUNK", "TEXTOVERLAY"}:
                return 16 * 1024 * 1024
        return 0

    def encode(
        self, image_path: str, output_path: str, payload: bytes, options: StegOptions, password: str = ""
    ) -> str:
        if not payload:
            raise ValueError("Payload is empty")
        method = get_method(options.method)
        if not method.available:
            raise RuntimeError(f"{method.label}: {method.unavailable_reason}")
        if method.requires_password and not password:
            raise ValueError(f"{method.label} requires a password")
        if method.id == "TEXTOVERLAY" and password:
            raise ValueError("Text Overlay does not support encryption")
        extension = Path(image_path).suffix.lower()
        if extension not in method.extensions:
            raise ValueError(f"{method.label} supports: {', '.join(method.extensions)}")

        output = str(Path(output_path).with_suffix(".png"))
        packed = self._pack(method.id, payload, password)
        if method.id == "LSB":
            with Image.open(image_path) as image:
                image.load()
                encode_lsb(image, packed, options.to_engine_config(), output)
        elif method.id == "SPREAD":
            seed = self._password_seed(password)
            with Image.open(image_path) as image:
                image.load()
                encode_lsb(image, packed, options.to_engine_config(seed=seed, strategy="randomized"), output)
        elif method.id == "PVD":
            encode_pvd(image_path, output, packed, options.pvd_direction, options.pvd_range)
        elif method.id == "DCT":
            encode_dct(image_path, packed, output, options.robustness)
        elif method.id == "PALETTE":
            encode_palette(image_path, output, packed, options.palette_colors)
        elif method.id == "CHROMA":
            if ChromaSteganography is None:
                raise RuntimeError("OpenCV is required for chroma steganography")
            ChromaSteganography().encode(image_path, packed, output)
        elif method.id == "PNGCHUNK":
            packed_text = packed.hex()
            encode_pngchunk(image_path, output, packed_text, options.png_keyword)
        elif method.id == "TEXTOVERLAY":
            encode_textoverlay(image_path, output, payload.decode("utf-8"))
        else:
            raise RuntimeError(f"Encoding is not implemented for {method.id}")
        return output

    def decode(self, image_path: str, password: str = "", options: StegOptions | None = None) -> bytes:
        options = options or StegOptions()
        method = get_method(options.method)
        if method.requires_password and not password:
            raise ValueError(f"{method.label} requires a password")
        if not method.available:
            raise RuntimeError(f"{method.label}: {method.unavailable_reason}")
        if method.id == "LSB":
            with Image.open(image_path) as image:
                image.load()
                raw = decode_lsb(image, config=options.to_engine_config(), verify_checksum=True)
        elif method.id == "SPREAD":
            seed = self._password_seed(password)
            with Image.open(image_path) as image:
                image.load()
                raw = decode_lsb(
                    image,
                    config=options.to_engine_config(seed=seed, strategy="randomized"),
                    verify_checksum=True,
                )
        elif method.id == "PVD":
            raw = decode_pvd(image_path, options.pvd_direction, options.pvd_range)
        elif method.id == "DCT":
            raw = decode_dct(image_path)
        elif method.id == "PALETTE":
            raw = bytes(decode_palette(image_path))
        elif method.id == "CHROMA":
            if ChromaSteganography is None:
                raise RuntimeError("OpenCV is required for chroma steganography")
            raw = ChromaSteganography().decode(image_path)
        elif method.id == "PNGCHUNK":
            text = decode_pngchunk(image_path, options.png_keyword)
            if not text:
                raise ValueError(f"No PNG text chunk named {options.png_keyword!r} found")
            raw = bytes.fromhex(text)
        elif method.id == "TEXTOVERLAY":
            return decode_textoverlay(image_path).encode("utf-8")
        else:
            raise RuntimeError(f"Decoding is not implemented for {method.id}")
        return self._unpack(method.id, bytes(raw), password)

    def extract_all(self, image_path: str, password: str = "", progress=None) -> dict[str, Any]:
        return scan_image(image_path, password, progress).to_dict()

    def analyze(self, image_path: str, password: str = "") -> dict[str, Any]:
        with Image.open(image_path) as image:
            image.load()
            report = analyze_image(image)
            report["detected_encoding"] = detect_encoding(image, password=password or None)
        report["extraction_methods"] = [
            {
                "id": method.id,
                "available": method.available,
                "requires_password": method.requires_password,
                "extractable": method.extractable,
                "reason": method.unavailable_reason,
            }
            for method in IMAGE_METHODS
        ]
        raw = Path(image_path).read_bytes()
        analyzer = {
            ".png": png_full_analysis,
            ".jpg": jpeg_decode,
            ".jpeg": jpeg_decode,
            ".gif": gif_analysis,
            ".bmp": bmp_analysis,
        }.get(Path(image_path).suffix.lower())
        if analyzer:
            report["deep_analysis"] = analyzer(raw)
        return report

    def analyze_json(self, image_path: str, password: str = "") -> str:
        return json.dumps(self.analyze(image_path, password), ensure_ascii=False, indent=2, default=str)

    def inject_png_text(self, image_path: str, output_path: str, text: str, keyword: str = "Comment") -> str:
        options = StegOptions(method="PNGCHUNK", png_keyword=keyword)
        return self.encode(image_path, output_path, text.encode("utf-8"), options)


service = SteganographyService()
