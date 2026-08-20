"""Verify that declared dependencies are used and represented in the license inventory."""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

IMPORTS_BY_DISTRIBUTION = {
    "aiohttp": {"aiohttp"},
    "aiohttp-socks": {"aiohttp_socks"},
    "beautifulsoup4": {"bs4"},
    "binwalk": {"binwalk"},
    "colorama": {"colorama"},
    "cryptography": {"cryptography"},
    "dnspython": {"dns"},
    "duckdb": {"duckdb"},
    "hachoir": {"hachoir"},
    "hashid": {"hashid"},
    "httpx": {"httpx"},
    "kreuzberg": {"kreuzberg"},
    "lupa": {"lupa"},
    "mutagen": {"mutagen"},
    "networkx": {"networkx"},
    "numpy": {"numpy"},
    "olefile": {"olefile"},
    "oletools": {"oletools"},
    "opencv-python-headless": {"cv2"},
    "osmnx": {"osmnx"},
    "paketlib": {"paketlib"},
    "pdfid": {"pdfid"},
    "pefile": {"pefile"},
    "pillow": {"PIL"},
    "protobuf": {"google.protobuf"},
    "pycryptodomex": {"Cryptodome"},
    "pyexiv2": {"pyexiv2"},
    "pymongo": {"bson", "pymongo"},
    "pyqt6": {"PyQt6"},
    "pyqt6-webengine": {"PyQt6.QtWebEngineCore", "PyQt6.QtWebEngineWidgets"},
    "python-magic": {"magic"},
    "requests": {"requests"},
    "tinytag": {"tinytag"},
    "truststore": {"truststore"},
    "xattr": {"xattr"},
}

INDIRECT_DEPENDENCIES = {
    "pysocks": "enables SOCKS proxy support in requests",
}


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).casefold()


def _requirements() -> list[str]:
    result = []
    for raw_line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        match = re.match(r"[A-Za-z0-9_.-]+", line)
        if match:
            result.append(_normalize(match.group(0)))
    return result


def _source_imports() -> set[str]:
    imports: set[str] = set()
    paths = [*(ROOT / "src").rglob("*.py"), *(ROOT / "scripts").rglob("*.py")]
    paths.extend(path for path in (ROOT / "gui.py", ROOT / "start.py") if path.exists())
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                imports.add(node.module)
    return imports


def _license_packages() -> list[str]:
    text = (ROOT / "THIRD_PARTY_LICENSES.md").read_text(encoding="utf-8")
    section = text.split("## Declared Python dependencies", 1)[-1]
    rows = re.findall(r"^\|\s*([^|]+?)\s*\|", section, flags=re.MULTILINE)
    return [_normalize(name) for name in rows if name.casefold() not in {"package", "---"}]


def main() -> int:
    failures: list[str] = []
    requirements = _requirements()
    if len(requirements) != len(set(requirements)):
        failures.append("requirements.txt contains duplicate distributions")

    mapped = set(IMPORTS_BY_DISTRIBUTION) | set(INDIRECT_DEPENDENCIES)
    for dependency in sorted(set(requirements) - mapped):
        failures.append(f"dependency has no audited import mapping: {dependency}")
    for dependency in sorted(mapped - set(requirements)):
        failures.append(f"audited dependency is no longer declared: {dependency}")

    imports = _source_imports()
    for dependency in requirements:
        candidates = IMPORTS_BY_DISTRIBUTION.get(dependency)
        if candidates and not any(
            imported == candidate or imported.startswith(candidate + ".")
            for imported in imports
            for candidate in candidates
        ):
            failures.append(f"declared dependency is not imported: {dependency}")

    licensed = _license_packages()
    if licensed != requirements:
        missing = sorted(set(requirements) - set(licensed))
        stale = sorted(set(licensed) - set(requirements))
        if missing:
            failures.append(f"dependencies missing from license inventory: {', '.join(missing)}")
        if stale:
            failures.append(f"stale dependencies in license inventory: {', '.join(stale)}")
        if not missing and not stale:
            failures.append("license inventory dependency order differs from requirements.txt")

    license_root = ROOT / "licenses" / "python"
    stale_license_dirs = sorted(
        child.name
        for child in license_root.iterdir()
        if child.is_dir() and _normalize(child.name) not in set(requirements)
    )
    if stale_license_dirs:
        failures.append(f"stale Python license directories: {', '.join(stale_license_dirs)}")

    if failures:
        print("Dependency verification failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"Dependency verification passed ({len(requirements)} declared distributions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
