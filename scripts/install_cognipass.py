"""Build the pinned CogniPass source for the current CPU and install it locally."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from laitoxx.core.external_tools import (  # noqa: E402
    missing_after_verification,
    normalize_external_tool_error,
    run_external_tool,
)

COGNIPASS_REPOSITORY = "BadPrivacyclub/CogniPass"
COGNIPASS_COMMIT = "1062c39102a8868e2a48a7496047eb24497d67bd"
COGNIPASS_ARCHIVE_SHA256 = "30b3a57e8ca1fcf7dd026e1262a7be4c50f9eaebb9d42615c8c912f84fe89996"
COGNIPASS_ARCHIVE_URL = f"https://codeload.github.com/{COGNIPASS_REPOSITORY}/zip/{COGNIPASS_COMMIT}"
COGNIPASS_REPOSITORY_URL = f"https://github.com/{COGNIPASS_REPOSITORY}.git"
STACK_BUFFER_PATCH = "heap-allocate-16mib-buffered-writer"
ZIGLANG_PACKAGE = "ziglang==0.13.0.post1"


def ensure_zig_toolchain() -> str:
    """Install the supported bundled Zig toolchain when it is not available."""
    version_command = [sys.executable, "-m", "ziglang", "version"]
    probe = run_external_tool("Zig toolchain", version_command, capture_output=True, text=True)
    if probe.returncode != 0:
        print(f"Installing bundled Zig toolchain ({ZIGLANG_PACKAGE})...")
        run_external_tool(
            "Python package installer",
            [sys.executable, "-m", "pip", "install", ZIGLANG_PACKAGE],
            check=True,
        )
        probe = run_external_tool("Zig toolchain", version_command, check=True, capture_output=True, text=True)
    return probe.stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verified_archive_hash(path: Path) -> str:
    try:
        return _sha256(path)
    except OSError as error:
        raise normalize_external_tool_error(
            "CogniPass source archive",
            path,
            "be verified",
            error,
            existed_before=path.is_file(),
        ) from error


def _download_archive(destination: Path) -> None:
    request = urllib.request.Request(
        COGNIPASS_ARCHIVE_URL,
        headers={"User-Agent": "Laitoxx-CogniPass-Builder/1.0"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:  # noqa: S310
        with destination.open("wb") as stream:
            shutil.copyfileobj(response, stream)


def _clone_repository(destination: Path) -> Path:
    """Clone through Git when Python's local TLS trust store rejects codeload."""
    run_external_tool(
        "Git",
        ["git", "clone", "--filter=blob:none", "--no-checkout", COGNIPASS_REPOSITORY_URL, str(destination)],
        check=True,
    )
    run_external_tool(
        "Git",
        ["git", "-C", str(destination), "checkout", "--detach", COGNIPASS_COMMIT],
        check=True,
    )
    actual_commit = run_external_tool(
        "Git",
        ["git", "-C", str(destination), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if actual_commit != COGNIPASS_COMMIT:
        raise RuntimeError(f"CogniPass commit mismatch: expected {COGNIPASS_COMMIT}, got {actual_commit}")
    if not (destination / "src" / "main.zig").is_file():
        raise RuntimeError("Cloned CogniPass repository has an unexpected layout")
    return destination


def _extract_safely(archive: Path, destination: Path) -> Path:
    destination = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            target = (destination / member.filename).resolve()
            if destination != target and destination not in target.parents:
                raise RuntimeError(f"Unsafe path in CogniPass archive: {member.filename}")
        bundle.extractall(destination)
    candidates = sorted(destination.glob("*/src/main.zig"))
    if len(candidates) != 1:
        raise RuntimeError("CogniPass source archive has an unexpected layout")
    return candidates[0].parent.parent


def _apply_compatibility_patches(source_root: Path) -> list[str]:
    """Keep CogniPass's 16 MiB I/O buffer without overflowing process stacks."""
    source = source_root / "src" / "main.zig"
    text = source.read_text(encoding="utf-8")
    original = """    var bw = std.io.BufferedWriter(16 * 1024 * 1024, @TypeOf(file.writer())){ .unbuffered_writer = file.writer() };
    const w = bw.writer();
"""
    replacement = """    const BufferedFileWriter = std.io.BufferedWriter(16 * 1024 * 1024, @TypeOf(file.writer()));
    const bw = try alloc.create(BufferedFileWriter);
    bw.* = .{ .unbuffered_writer = file.writer() };
    const w = bw.writer();
"""
    if original in text:
        source.write_text(text.replace(original, replacement, 1), encoding="utf-8")
        return [STACK_BUFFER_PATCH]
    if replacement in text:
        return [STACK_BUFFER_PATCH]
    raise RuntimeError("CogniPass buffered writer changed; refusing to apply an unsafe patch")


def zig_build_command(source_root: Path, output_name: str = "cognipass") -> list[str]:
    """Return the reproducible cpu-native build command used by both installers."""
    del source_root  # The path is supplied as subprocess cwd, not as an argument.
    return [
        sys.executable,
        "-m",
        "ziglang",
        "build-exe",
        "src/main.zig",
        "-O",
        "ReleaseFast",
        "-mcpu=native",
        "-flto",
        "-fstrip",
        "--name",
        output_name,
    ]


def _probe_binary(binary: Path) -> None:
    """Exercise one tiny deterministic generation; CogniPass has no read-only version flag."""
    with tempfile.TemporaryDirectory(prefix="laitoxx-cognipass-probe-") as temporary:
        probe_dir = Path(temporary)
        probe_name = "probe.txt"
        interactive_input = "\n".join(("Alice", "", "", "", "", "", "n", "n", "n", "8", "8", "1", probe_name, ""))
        completed = run_external_tool(
            "CogniPass",
            [str(binary), "--interactive"],
            operation="pass its installation check",
            cwd=probe_dir,
            input=interactive_input,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
        output = probe_dir / probe_name
        if completed.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
            detail = (completed.stderr or completed.stdout or "no output file")[-1000:].strip()
            raise RuntimeError(f"CogniPass failed its generation check: {detail}")


def install_cognipass(destination: Path, archive: Path | None = None) -> Path:
    destination = destination.expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="laitoxx-cognipass-") as temporary:
        temporary_path = Path(temporary)
        acquisition = "verified archive"
        if archive is not None:
            local_archive = archive.resolve()
            actual_hash = _verified_archive_hash(local_archive)
            if actual_hash != COGNIPASS_ARCHIVE_SHA256:
                raise RuntimeError(
                    f"CogniPass source checksum mismatch: expected {COGNIPASS_ARCHIVE_SHA256}, got {actual_hash}"
                )
            source_root = _extract_safely(local_archive, temporary_path / "source")
        else:
            local_archive = temporary_path / "cognipass.zip"
            print(f"Downloading CogniPass source at {COGNIPASS_COMMIT[:12]}...")
            try:
                _download_archive(local_archive)
            except urllib.error.URLError as error:
                reason = getattr(error, "reason", None)
                if isinstance(reason, OSError):
                    classified = normalize_external_tool_error(
                        "CogniPass source archive",
                        local_archive,
                        "be downloaded",
                        reason,
                        existed_before=local_archive.is_file(),
                    )
                    if classified.security_suspected or classified.permission_or_security:
                        raise classified from error
                print(f"Archive TLS download failed ({error}); falling back to verified git checkout...")
                acquisition = "verified git checkout"
                source_root = _clone_repository(temporary_path / "repository")
            except OSError as error:
                raise normalize_external_tool_error(
                    "CogniPass source archive",
                    local_archive,
                    "be downloaded",
                    error,
                    existed_before=local_archive.is_file(),
                ) from error
            else:
                actual_hash = _verified_archive_hash(local_archive)
                if actual_hash != COGNIPASS_ARCHIVE_SHA256:
                    raise RuntimeError(
                        f"CogniPass source checksum mismatch: expected {COGNIPASS_ARCHIVE_SHA256}, got {actual_hash}"
                    )
                source_root = _extract_safely(local_archive, temporary_path / "source")
        patches = _apply_compatibility_patches(source_root)
        version = ensure_zig_toolchain()
        print(f"Building CogniPass with Zig {version}, ReleaseFast, native CPU and LTO...")
        run_external_tool("Zig compiler", zig_build_command(source_root), cwd=source_root, check=True)
        built = source_root / ("cognipass.exe" if os.name == "nt" else "cognipass")
        if not built.is_file():
            raise missing_after_verification("CogniPass", built, "finish installation")
        installed = destination / built.name
        try:
            shutil.copy2(built, installed)
        except OSError as error:
            raise normalize_external_tool_error(
                "CogniPass", installed, "be installed", error, existed_before=built.is_file()
            ) from error
        if os.name != "nt":
            installed.chmod(installed.stat().st_mode | 0o111)
        if not installed.is_file():
            raise missing_after_verification("CogniPass", installed, "start its installation check")
        _probe_binary(installed)
        license_path = source_root / "LICENSE"
        if license_path.is_file():
            shutil.copy2(license_path, destination / "cognipass.LICENSE.txt")
        metadata = {
            "repository": f"https://github.com/{COGNIPASS_REPOSITORY}",
            "commit": COGNIPASS_COMMIT,
            "source_sha256": COGNIPASS_ARCHIVE_SHA256,
            "acquisition": acquisition,
            "zig_version": version,
            "optimization": "ReleaseFast",
            "cpu": "native",
            "lto": True,
            "stripped": True,
            "patches": patches,
        }
        (destination / "cognipass.build.json").write_text(
            json.dumps(metadata, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"CogniPass installed: {installed}")
        return installed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dest", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    try:
        install_cognipass(args.dest, args.archive)
    except (OSError, RuntimeError, subprocess.SubprocessError, zipfile.BadZipFile) as error:
        print(f"[ERROR] CogniPass installation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
