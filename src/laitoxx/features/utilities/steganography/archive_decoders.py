"""Focused steganography decoder and analysis operations."""
# ruff: noqa: E702 - compact decoder branches are intentionally kept together.

from __future__ import annotations

import io
import struct
from typing import Any


def zip_decode(data: bytes) -> dict[str, Any]:
    """Extract steg data from ZIP - comments, nested ZIPs, trailing data."""
    import zipfile

    results = {"found": False, "findings": []}
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        if zf.comment:
            results["comment"] = zf.comment.decode("utf-8", errors="replace")[:200]
            results["found"] = True
            results["findings"].append(f"ZIP comment: {results['comment'][:60]}")
        for name in zf.namelist():
            if any(s in name.lower() for s in ["secret", "hidden", "steg", "flag", "inner.zip"]):
                content = zf.read(name)
                if content[:2] == b"PK":
                    inner = zipfile.ZipFile(io.BytesIO(content))
                    for iname in inner.namelist():
                        ic = inner.read(iname).decode("utf-8", errors="replace")
                        results["findings"].append(f"Nested {iname}: {ic[:100]}")
                        results["found"] = True
                    inner.close()
                else:
                    results["findings"].append(f"{name}: {content.decode('utf-8', errors='replace')[:100]}")
                    results["found"] = True
        zf.close()
        eocd = data.rfind(b"PK\x05\x06")
        if eocd >= 0:
            eocd_size = 22 + struct.unpack("<H", data[eocd + 20 : eocd + 22])[0]
            if eocd + eocd_size < len(data):
                trailing = data[eocd + eocd_size :]
                results["findings"].append(
                    f"Trailing ({len(trailing)}b): {trailing.decode('utf-8', errors='replace')[:60]}"
                )
                results["found"] = True
    except Exception as e:
        results["error"] = str(e)
    results["suspicious"] = results["found"]
    return results


def tar_decode(data: bytes) -> dict[str, Any]:
    """Extract steg data from TAR - PAX headers, file contents."""
    import tarfile

    results = {"found": False, "findings": []}
    try:
        tf = tarfile.open(fileobj=io.BytesIO(data))
        # Note: we only READ members, never extract to filesystem - no path traversal risk
        for member in tf.getmembers():
            if hasattr(member, "pax_headers") and member.pax_headers:
                for k, v in member.pax_headers.items():
                    results["findings"].append(f"PAX {k}: {str(v)[:100]}")
                    results["found"] = True
            if member.isfile():
                f = tf.extractfile(member)
                if f:
                    results["findings"].append(f"{member.name}: {f.read(200).decode('utf-8', errors='replace')[:100]}")
        tf.close()
    except Exception as e:
        results["error"] = str(e)
    results["suspicious"] = results["found"]
    return results


def gzip_decode(data: bytes) -> dict[str, Any]:
    """Extract steg data from GZip - FEXTRA, FCOMMENT fields."""
    results = {"found": False, "findings": []}
    if len(data) < 10 or data[:2] != b"\x1f\x8b":
        return results
    flags = data[3]
    pos = 10
    if flags & 0x04 and pos + 2 <= len(data):
        xlen = struct.unpack("<H", data[pos : pos + 2])[0]
        pos += 2
        extra = data[pos : pos + xlen]
        results["findings"].append(f"FEXTRA ({xlen}b): {extra.decode('utf-8', errors='replace')[:60]}")
        results["found"] = True
        pos += xlen
    if flags & 0x08:
        end = data.index(0, pos)
        pos = end + 1
    if flags & 0x10:
        end = data.index(0, pos)
        comment = data[pos:end].decode("utf-8", errors="replace")
        results["findings"].append(f"FCOMMENT: {comment[:60]}")
        results["found"] = True
    results["suspicious"] = results["found"]
    return results


def sqlite_decode(data: bytes) -> dict[str, Any]:
    """Extract steg data from SQLite - hidden tables."""
    import os
    import sqlite3
    import tempfile

    results = {"found": False, "findings": []}
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        tmp.write(data)
        tmp.close()
        conn = sqlite3.connect(tmp.name)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in c.fetchall()]
        results["tables"] = tables
        for table in tables:
            if any(s in table.lower() for s in ["steg", "hidden", "secret", "payload", "_steg"]):
                c.execute(f'SELECT * FROM "{table}" LIMIT 10')
                for row in c.fetchall():
                    results["findings"].append(f"{table}: {' | '.join(str(v)[:80] for v in row)[:150]}")
                    results["found"] = True
        conn.close()
        os.unlink(tmp.name)
    except Exception as e:
        results["error"] = str(e)
    results["suspicious"] = results["found"]
    return results


# ============== DOCUMENT DECODERS ==============


def pdf_decode(data: bytes) -> dict[str, Any]:
    """Extract steg data from PDF - JS, forms, XMP, trailing data."""
    import re as _re

    results = {"found": False, "findings": []}
    if not data.startswith(b"%PDF"):
        return results
    text = data.decode("latin-1", errors="replace")
    if "/JavaScript" in text or "/JS " in text:
        results["findings"].append("JavaScript detected")
        results["found"] = True
        for m in _re.finditer(r"/JS\s*\(([^)]+)\)", text):
            results["findings"].append(f"JS: {m.group(1)[:80]}")
    if "/AcroForm" in text:
        for m in _re.finditer(r"/V\s*\(([^)]+)\)", text):
            results["findings"].append(f"Form: {m.group(1)[:80]}")
            results["found"] = True
    eof = data.rfind(b"%%EOF")
    if eof >= 0:
        trailing = data[eof + 5 :].strip()
        if trailing:
            results["findings"].append(
                f"Post-EOF ({len(trailing)}b): {trailing.decode('utf-8', errors='replace')[:80]}"
            )
            results["found"] = True
    xmp = data.find(b"<x:xmpmeta")
    if xmp >= 0:
        xmp_end = data.find(b"</x:xmpmeta>", xmp)
        if xmp_end >= 0:
            xmp_data = data[xmp : xmp_end + 12].decode("utf-8", errors="replace")
            for m in _re.finditer(r"<dc:description>([^<]+)</dc:description>", xmp_data):
                results["findings"].append(f"XMP desc: {m.group(1)[:80]}")
                results["found"] = True
    results["suspicious"] = results["found"]
    return results


def jpeg_decode(data: bytes) -> dict[str, Any]:
    """Extract steg data from JPEG - COM markers, APP segments."""
    results = {"found": False, "findings": []}
    if len(data) < 2 or data[:2] != b"\xff\xd8":
        return results
    pos = 2
    while pos < len(data) - 4:
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos + 1]
        if marker == 0xFE:  # COM
            length = struct.unpack(">H", data[pos + 2 : pos + 4])[0]
            comment = data[pos + 4 : pos + 2 + length].decode("utf-8", errors="replace")
            results["findings"].append(f"COM: {comment[:100]}")
            results["found"] = True
            pos += 2 + length
        elif 0xE0 <= marker <= 0xEF:
            length = struct.unpack(">H", data[pos + 2 : pos + 4])[0]
            if marker not in (0xE0, 0xE1):
                seg = data[pos + 4 : pos + 2 + length]
                text = seg.decode("utf-8", errors="replace")
                if any(s in text.lower() for s in ["st3gg", "steg", "secret"]):
                    results["findings"].append(f"APP{marker - 0xE0}: {text[:80]}")
                    results["found"] = True
            pos += 2 + length
        elif marker in (0xDA, 0xD9):
            break
        else:
            try:
                length = struct.unpack(">H", data[pos + 2 : pos + 4])[0]
                pos += 2 + length
            except Exception:
                break
    results["suspicious"] = results["found"]
    return results


def svg_decode(data: bytes) -> dict[str, Any]:
    """Extract steg data from SVG - comments, data attributes, metadata."""
    import re as _re

    results = {"found": False, "findings": []}
    try:
        text = data.decode("utf-8", errors="replace")
        for m in _re.finditer(r"<!--(.*?)-->", text, _re.DOTALL):
            c = m.group(1).strip()
            if len(c) > 5:
                results["findings"].append(f"Comment: {c[:80]}")
                results["found"] = True
        for m in _re.finditer(r'data-\w+="([^"]*)"', text):
            results["findings"].append(f"Data attr: {m.group(1)[:80]}")
            results["found"] = True
        meta = text.find("<metadata")
        if meta >= 0:
            meta_end = text.find("</metadata>", meta)
            if meta_end >= 0:
                for m in _re.finditer(r"<dc:description>([^<]+)</dc:description>", text[meta:meta_end]):
                    results["findings"].append(f"Description: {m.group(1)[:80]}")
                    results["found"] = True
    except Exception as e:
        results["error"] = str(e)
    results["suspicious"] = results["found"]
    return results
