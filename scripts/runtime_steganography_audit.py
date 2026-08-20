"""Round-trip and exhaustive extraction audit for image steganography."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from laitoxx.features.utilities.steganography.service import StegOptions, service


def main() -> int:
    payload = "ST3GG runtime - скрытые данные 👋".encode()
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        cover = root / "cover.png"
        pixels = np.random.default_rng(42).integers(0, 256, (512, 512, 3), dtype=np.uint8)
        Image.fromarray(pixels, "RGB").save(cover)

        outputs = {}
        for method in ("LSB", "SPREAD", "PVD", "DCT", "PALETTE", "CHROMA", "PNGCHUNK"):
            options = StegOptions(method=method, bits=2 if method in {"LSB", "SPREAD"} else 1)
            password = "secret" if method == "SPREAD" else ""
            output = service.encode(str(cover), str(root / method), payload, options, password)
            assert service.decode(output, password, options) == payload
            outputs[method] = output
            print(f"PASS roundtrip_{method.lower()}")

        progress = []
        scan = service.extract_all(
            outputs["DCT"],
            progress=lambda current, total, label: progress.append((current, total, label)),
        )
        assert any(match["method"] == "DCT" and match.get("text") == payload.decode() for match in scan["matches"])
        assert scan["attempted"] >= 375
        assert progress and progress[-1][0] == progress[-1][1] == scan["attempted"]
        assert [item[0] for item in progress] == list(range(1, scan["attempted"] + 1))
        print("PASS exhaustive_scan")

        spread_scan = service.extract_all(outputs["SPREAD"], "secret")
        assert any(match["method"] == "SPREAD" for match in spread_scan["matches"])
        print("PASS password_scan")

        analysis = service.analyze(str(cover))
        assert analysis["detection"]["level"] in {"LOW", "MEDIUM", "HIGH"}
        assert analysis["extraction_methods"]
        print("PASS image_analysis")

        try:
            service.encode(str(cover), str(root / "f5"), payload, StegOptions(method="F5"), "secret")
        except RuntimeError as exc:
            assert "coefficient backend" in str(exc)
        else:
            raise AssertionError("F5 must not silently use a non-F5 fallback")
        print("PASS unavailable_f5_guard")

    print("steganography runtime audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
