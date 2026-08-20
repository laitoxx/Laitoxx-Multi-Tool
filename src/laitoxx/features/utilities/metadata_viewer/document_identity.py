"""Identity and IOC extraction from local documents without external calls."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from PIL import ExifTags, Image

from laitoxx.features.utilities.ioc_extractor import extract_entities

PRINTABLE = re.compile(rb"[\x20-\x7e]{5,}")
PDF_FIELDS = ("Author", "Creator", "Producer", "Title", "Subject")


def _printable_text(raw: bytes, limit: int = 2_000_000) -> str:
    return "\n".join(match.decode("utf-8", errors="replace") for match in PRINTABLE.findall(raw[:limit]))


def _pdf_metadata(raw: bytes) -> dict:
    text = raw.decode("latin-1", errors="ignore")
    result = {}
    for field in PDF_FIELDS:
        match = re.search(rf"/{field}\s*\((.*?)(?<!\\)\)", text, re.S)
        if match:
            result[field.lower()] = match.group(1).replace(r"\(", "(").replace(r"\)", ")")[:500]
    return result


def _office_metadata(path: Path) -> tuple[dict, str]:
    metadata = {}
    collected = []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if name == "docProps/core.xml":
                root = ElementTree.fromstring(archive.read(name))
                for child in root:
                    metadata[child.tag.rsplit("}", 1)[-1]] = child.text or ""
            if name.endswith(".xml") and (
                name.startswith("word/") or name.startswith("ppt/") or name.startswith("xl/")
            ):
                content = archive.read(name).decode("utf-8", errors="ignore")
                collected.extend(re.findall(r">([^<>]{2,})<", content))
    return metadata, " ".join(collected)


def _image_metadata(path: Path) -> dict:
    with Image.open(path) as image:
        result = {"format": image.format, "mode": image.mode, "size": image.size}
        exif = image.getexif()
        result["exif"] = {ExifTags.TAGS.get(tag, str(tag)): str(value) for tag, value in exif.items()}
        return result


def extract_document_identity(path: str) -> dict:
    file = Path(path)
    raw = file.read_bytes()
    suffix = file.suffix.lower()
    metadata = {}
    text = _printable_text(raw)
    if suffix == ".pdf":
        metadata = _pdf_metadata(raw)
    elif suffix in {".docx", ".xlsx", ".pptx", ".odt"} and zipfile.is_zipfile(file):
        metadata, text = _office_metadata(file)
    elif suffix in {".png", ".jpg", ".jpeg", ".tiff", ".webp", ".bmp"}:
        metadata = _image_metadata(file)
    entities = extract_entities(text + "\n" + json.dumps(metadata, ensure_ascii=False, default=str))
    identity_keys = {
        key: value
        for key, value in metadata.items()
        if any(token in key.casefold() for token in ("author", "creator", "company", "lastmodifiedby"))
    }
    return {
        "file": str(file),
        "size": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "metadata": metadata,
        "identity": identity_keys,
        "entities": [{"kind": entity.kind, "value": entity.value} for entity in entities],
    }


def document_identity_tool(path: str | None = None):
    result = extract_document_identity(path if path is not None else input())
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return result
