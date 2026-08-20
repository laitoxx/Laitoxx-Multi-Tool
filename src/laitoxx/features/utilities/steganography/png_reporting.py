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

from .image_formats import png_detect_embedded_png, png_filter_analysis
from .png_pixels import png_bit_plane_analysis, png_chi_square_analysis, png_extract_lsb
from .png_structure import png_analyze_idat, png_detect_appended_data, png_extract_text_chunks, png_parse_chunks


def png_color_histogram_analysis(data: bytes) -> dict[str, Any]:
    """Analyze color histogram for LSB steganography indicators"""
    if not HAS_PIL or not HAS_NUMPY:
        return {"error": "PIL or numpy not available"}

    try:
        img = Image.open(io.BytesIO(data))

        if img.mode == "P":
            img = img.convert("RGB")

        pixels = np.array(img)
        results = {}

        channel_names = ["Red", "Green", "Blue"][: pixels.shape[2] if len(pixels.shape) > 2 else 1]

        for ch_idx, ch_name in enumerate(channel_names):
            channel = pixels[:, :, ch_idx].flatten()

            # Calculate histogram
            hist, _ = np.histogram(channel, bins=256, range=(0, 256))

            # Pairs of Values (PoV) analysis
            # In natural images, adjacent histogram bins have similar counts
            # LSB embedding creates anomalies in pairs (2k, 2k+1)
            pair_diffs = []
            for i in range(0, 256, 2):
                if hist[i] + hist[i + 1] > 0:
                    diff = abs(hist[i] - hist[i + 1]) / (hist[i] + hist[i + 1])
                    pair_diffs.append(diff)

            avg_pair_diff = np.mean(pair_diffs) if pair_diffs else 0

            results[ch_name] = {
                "unique_values": int(np.sum(hist > 0)),
                "avg_pair_difference": float(avg_pair_diff),
                "suspicious": avg_pair_diff < 0.05,  # Very similar pairs suggest LSB
            }

        return {
            "found": True,
            "channels": results,
            "suspicious": any(r["suspicious"] for r in results.values()),
            "interpretation": "Similar histogram pair values may indicate LSB steganography",
        }

    except Exception as e:
        return {"error": str(e), "found": False}


def png_visual_attack(data: bytes) -> dict[str, Any]:
    """Generate visual attack images for bit plane analysis"""
    if not HAS_PIL or not HAS_NUMPY:
        return {"error": "PIL or numpy not available"}

    try:
        img = Image.open(io.BytesIO(data))

        if img.mode == "P":
            img = img.convert("RGB")

        pixels = np.array(img)

        # Extract LSB planes and scale to full intensity
        lsb_images = {}

        channel_names = ["Red", "Green", "Blue"]
        for ch_idx, ch_name in enumerate(channel_names):
            if ch_idx < pixels.shape[2]:
                # LSB plane scaled to 0 or 255
                lsb = (pixels[:, :, ch_idx] & 1) * 255
                lsb_images[ch_name] = lsb.tolist()  # Can be reconstructed client-side

        # Combined RGB LSB
        combined = np.zeros_like(pixels)
        for ch_idx in range(min(3, pixels.shape[2])):
            combined[:, :, ch_idx] = (pixels[:, :, ch_idx] & 1) * 255

        return {
            "found": True,
            "image_size": [int(pixels.shape[1]), int(pixels.shape[0])],
            "channel_lsb_available": list(lsb_images.keys()),
            "interpretation": "Visual inspection of LSB planes can reveal hidden patterns",
        }

    except Exception as e:
        return {"error": str(e), "found": False}


def png_steg_signature_scan(data: bytes) -> dict[str, Any]:
    """Scan for known steganography tool signatures"""
    signatures = {
        b"STEG": "Stegosaurus Wrecks",
        b"openstego": "OpenStego",
        b"steghide": "Steghide",
        b"F5": "F5 Algorithm",
        b"jphide": "JPHide",
        b"outguess": "OutGuess",
        b"invisible secrets": "Invisible Secrets",
        b"camouflage": "Camouflage",
        b"snow": "SNOW",
        b"\x00\x00\x00\x01steg": "Generic Steg Header",
    }

    found = []

    for sig, tool_name in signatures.items():
        pos = data.find(sig)
        if pos != -1:
            found.append(
                {
                    "signature": sig.hex() if not sig.isascii() else sig.decode("ascii", errors="replace"),
                    "tool": tool_name,
                    "offset": pos,
                }
            )

    # Also check LSB extracted data
    lsb_result = png_extract_lsb(data, bits=1, channels="RGB")
    if lsb_result.get("raw_data"):
        lsb_data = lsb_result["raw_data"][:1000]
        for sig, tool_name in signatures.items():
            if sig in lsb_data:
                found.append(
                    {
                        "signature": sig.hex() if not sig.isascii() else sig.decode("ascii", errors="replace"),
                        "tool": tool_name,
                        "location": "LSB_extracted",
                    }
                )

    return {"found": len(found) > 0, "signatures": found, "suspicious": len(found) > 0}


def png_full_analysis(data: bytes) -> dict[str, Any]:
    """Run all PNG analysis tools and compile results"""
    results = {"file_type": "PNG", "analyses": {}}

    # Run all PNG analysis tools
    analyses = [
        ("chunk_parse", png_parse_chunks),
        ("text_chunks", png_extract_text_chunks),
        ("appended_data", png_detect_appended_data),
        ("idat_analysis", png_analyze_idat),
        ("chi_square", png_chi_square_analysis),
        ("bit_planes", png_bit_plane_analysis),
        ("histogram", png_color_histogram_analysis),
        ("filter_analysis", png_filter_analysis),
        ("embedded_png", png_detect_embedded_png),
        ("steg_signatures", png_steg_signature_scan),
    ]

    suspicious_count = 0

    for name, func in analyses:
        try:
            result = func(data)
            results["analyses"][name] = result
            if result.get("suspicious"):
                suspicious_count += 1
        except Exception as e:
            results["analyses"][name] = {"error": str(e)}

    results["suspicious_indicators"] = suspicious_count
    results["overall_suspicious"] = suspicious_count >= 2
    results["summary"] = f"Found {suspicious_count} suspicious indicators"

    return results
