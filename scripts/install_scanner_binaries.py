"""Install standalone Advanced Web Scanner binaries using only Python stdlib.

The installer resolves an exact, pinned GitHub release, selects the archive for
the current OS/CPU, verifies the SHA-256 published by GitHub, and extracts only
the expected executable.  No Go, Ruby, package manager, or shell pipeline is
required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from laitoxx.core.external_tools import (  # noqa: E402
    ExternalToolError,
    missing_after_verification,
    normalize_external_tool_error,
    run_external_tool,
)

TOOLS = {
    "nuclei": ("projectdiscovery/nuclei", "v3.11.0"),
    "httpx": ("projectdiscovery/httpx", "v1.10.0"),
    "naabu": ("projectdiscovery/naabu", "v2.6.1"),
}
USER_AGENT = "Laitoxx-Scanner-Binary-Installer/1.0"


def _request(url: str) -> urllib.request.Request:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token and urlparse(url).hostname == "api.github.com":
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers)


def platform_slug() -> tuple[str, str]:
    systems = {"Windows": "windows", "Linux": "linux", "Darwin": "macOS"}
    machines = {
        "amd64": "amd64",
        "x86_64": "amd64",
        "x64": "amd64",
        "i386": "386",
        "i686": "386",
        "x86": "386",
        "aarch64": "arm64",
        "arm64": "arm64",
    }
    system = systems.get(platform.system())
    machine = machines.get(platform.machine().casefold())
    if not system or not machine:
        raise RuntimeError(f"Unsupported platform: {platform.system()} {platform.machine()}")
    return system, machine


def release_metadata(repository: str, version: str) -> dict:
    url = f"https://api.github.com/repos/{repository}/releases/tags/{version}"
    with urllib.request.urlopen(_request(url), timeout=30) as response:
        return json.load(response)


def select_asset(metadata: dict, tool: str, version: str, system: str, machine: str) -> dict:
    numeric = version.removeprefix("v")
    expected = f"{tool}_{numeric}_{system}_{machine}.zip".casefold()
    for asset in metadata.get("assets", []):
        if str(asset.get("name", "")).casefold() == expected:
            return asset
    raise RuntimeError(f"Release {version} has no {system}/{machine} archive for {tool}")


def _download(url: str, destination: Path) -> str:
    digest = hashlib.sha256()
    with urllib.request.urlopen(_request(url), timeout=90) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
            digest.update(chunk)
    return digest.hexdigest()


def _published_digest(metadata: dict, asset: dict, temp_dir: Path) -> str:
    digest = str(asset.get("digest") or "")
    if digest.startswith("sha256:"):
        return digest.split(":", 1)[1].casefold()
    checksum_asset = next(
        (item for item in metadata.get("assets", []) if "checksum" in str(item.get("name", "")).casefold()),
        None,
    )
    if not checksum_asset:
        raise RuntimeError(f"No SHA-256 is published for {asset.get('name')}")
    checksum_path = temp_dir / str(checksum_asset["name"])
    _download(str(checksum_asset["browser_download_url"]), checksum_path)
    for line in checksum_path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.replace("*", " ").split()
        if len(parts) >= 2 and parts[-1] == asset.get("name"):
            return parts[0].casefold()
    raise RuntimeError(f"Checksum file has no entry for {asset.get('name')}")


def _extract_binary(archive: Path, tool: str, destination: Path) -> Path:
    executable = f"{tool}.exe" if os.name == "nt" else tool
    with zipfile.ZipFile(archive) as bundle:
        member = next((name for name in bundle.namelist() if Path(name).name.casefold() == executable.casefold()), None)
        if not member:
            raise RuntimeError(f"{archive.name} does not contain {executable}")
        destination.mkdir(parents=True, exist_ok=True)
        target = destination / executable
        temporary = destination / f".{executable}.tmp"
        try:
            with bundle.open(member) as source, temporary.open("wb") as output:
                shutil.copyfileobj(source, output)
            temporary.chmod(0o755)
            temporary.replace(target)
        except OSError as error:
            raise normalize_external_tool_error(
                tool, target, "be installed", error, existed_before=temporary.is_file()
            ) from error
        if not target.is_file():
            raise missing_after_verification(tool, target, "start its version check")
        return target


def install_tool(tool: str, destination: Path) -> Path:
    repository, version = TOOLS[tool]
    system, machine = platform_slug()
    metadata = release_metadata(repository, version)
    asset = select_asset(metadata, tool, version, system, machine)
    with tempfile.TemporaryDirectory(prefix=f"laitoxx-{tool}-") as temporary:
        temp_dir = Path(temporary)
        archive = temp_dir / str(asset["name"])
        expected = _published_digest(metadata, asset, temp_dir)
        try:
            actual = _download(str(asset["browser_download_url"]), archive)
        except OSError as error:
            raise normalize_external_tool_error(
                tool,
                archive,
                "download its verified release",
                error,
                existed_before=archive.is_file(),
            ) from error
        if actual != expected:
            raise RuntimeError(f"SHA-256 mismatch for {asset['name']}: expected {expected}, got {actual}")
        try:
            target = _extract_binary(archive, tool, destination)
        except OSError as error:
            raise normalize_external_tool_error(
                tool,
                destination / (f"{tool}.exe" if os.name == "nt" else tool),
                "be extracted",
                error,
                existed_before=archive.is_file(),
            ) from error
    probe = run_external_tool(
        tool,
        [str(target), "-version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    if probe.returncode not in {0, 1}:
        raise RuntimeError(f"{tool} was extracted but failed its version check")
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dest", type=Path, required=True, help="venv bin/Scripts directory")
    parser.add_argument("--tools", nargs="+", choices=tuple(TOOLS), default=tuple(TOOLS))
    args = parser.parse_args()
    failures = 0
    for tool in args.tools:
        try:
            target = install_tool(tool, args.dest.resolve())
            print(f"[OK] {tool} installed and verified: {target}")
        except Exception as exc:
            failures += 1
            print(f"[WARNING] {tool} was not installed: {exc}", file=sys.stderr)
    nuclei = args.dest.resolve() / ("nuclei.exe" if os.name == "nt" else "nuclei")
    if nuclei.is_file():
        try:
            completed = run_external_tool(
                "Nuclei",
                [str(nuclei), "-update-templates", "-silent"],
                timeout=120,
                capture_output=True,
                check=False,
            )
            if completed.returncode == 0:
                print("[OK] Nuclei templates initialized")
            else:
                print(
                    "[WARNING] Nuclei templates could not be initialized; retry from the scanner settings",
                    file=sys.stderr,
                )
        except (OSError, ExternalToolError, subprocess.TimeoutExpired) as exc:
            print(f"[WARNING] Nuclei templates will need to be initialized later: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
