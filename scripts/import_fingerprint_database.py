"""Import Divener's generated fingerprint database as immutable app resources."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REDISTRIBUTABLE_SOURCES = {
    "custom",
    "fingerprinthub",
    "hassh",
    "ja3",
    "nerva",
    "nuclei",
    "recog",
}
RUNTIME_SOURCES = {"custom", "fingerprinthub", "nerva", "recog"}


def import_database(source: Path, destination: Path, allowed_sources: set[str] | None = None) -> dict:
    source = source.resolve()
    destination = destination.resolve()
    if not source.is_dir():
        raise RuntimeError(f"Fingerprint database does not exist: {source}")
    destination.mkdir(parents=True, exist_ok=True)
    runtime_destination = destination.parent / "runtime_index"
    runtime_destination.mkdir(parents=True, exist_ok=True)
    allowed = {item.casefold() for item in (allowed_sources or REDISTRIBUTABLE_SOURCES)}
    for stale in destination.glob("*.json"):
        stale.unlink()
    for stale in runtime_destination.glob("*.json"):
        stale.unlink()
    imported = []
    runtime_imported = []
    for path in sorted(source.glob("*.json")):
        # Validate before copying so a broken source never becomes a packaged asset.
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise RuntimeError(f"{path.name} must contain a JSON list")
        data = [
            row for row in data if isinstance(row, dict) and str(row.get("source_project", "")).casefold() in allowed
        ]
        if not data:
            continue
        target = destination / path.name
        target.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        imported.append(
            {
                "name": path.name,
                "records": len(data),
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            }
        )
        runtime_rows = [
            row
            for row in data
            if str(row.get("source_project", "")).casefold() in RUNTIME_SOURCES
            and str(row.get("match_type", "")).casefold() in {"regex", "text"}
        ]
        if runtime_rows:
            runtime_target = runtime_destination / path.name
            runtime_target.write_text(
                json.dumps(runtime_rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
            )
            runtime_imported.append({"name": path.name, "records": len(runtime_rows)})
    manifest = {
        "format": 1,
        "source": source.name,
        "source_projects": sorted(allowed),
        "files": len(imported),
        "records": sum(item["records"] for item in imported),
        "entries": imported,
        "runtime_index": {
            "directory": runtime_destination.name,
            "files": len(runtime_imported),
            "records": sum(item["records"] for item in runtime_imported),
        },
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument(
        "--sources",
        nargs="+",
        default=sorted(REDISTRIBUTABLE_SOURCES),
        help="Source-project labels to include; defaults exclude copyleft/NPSL datasets",
    )
    args = parser.parse_args()
    result = import_database(args.source, args.destination, set(args.sources))
    print(f"Imported {result['records']} fingerprints in {result['files']} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
