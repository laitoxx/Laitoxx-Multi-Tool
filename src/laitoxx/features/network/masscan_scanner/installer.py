"""Install Masscan from a pinned official GitHub release source archive."""

from __future__ import annotations

import hashlib
import os
import platform
import shutil
import ssl
import tarfile
import tempfile
import urllib.request
from collections.abc import Callable
from pathlib import Path

from laitoxx.core.external_tools import (
    missing_after_verification,
    normalize_external_tool_error,
    run_external_tool,
)

MASSCAN_VERSION = "1.3.2"
SOURCE_URL = f"https://github.com/robertdavidgraham/masscan/archive/refs/tags/{MASSCAN_VERSION}.tar.gz"
SOURCE_SHA256 = "0363e82c07e6ceee68a2da48acd0b2807391ead9a396cf9c70b53a2a901e3d5f"
SOURCE_REPOSITORY = "https://github.com/robertdavidgraham/masscan.git"
# Peeled commit behind the signed/annotated 1.3.2 tag object bfba957b…
SOURCE_COMMIT = "06902c40d1494881c17b7968ef530e1d6bbd320c"
USER_AGENT = "Laitoxx-Masscan-Installer/1.0"
Progress = Callable[[str], None]


def _ssl_context():
    try:
        import truststore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        return ssl.create_default_context()


def _download(destination: Path, progress: Progress | None) -> None:
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": USER_AGENT})
    digest = hashlib.sha256()
    with urllib.request.urlopen(request, timeout=90, context=_ssl_context()) as response, destination.open("wb") as out:
        while chunk := response.read(1024 * 1024):
            out.write(chunk)
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != SOURCE_SHA256:
        raise RuntimeError(f"Masscan source SHA-256 mismatch: expected {SOURCE_SHA256}, got {actual}")
    if progress:
        progress(f"Verified official Masscan {MASSCAN_VERSION} source archive")


def _safe_extract(archive: Path, destination: Path) -> Path:
    destination = destination.resolve()
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        for member in members:
            resolved = (destination / member.name).resolve()
            if destination != resolved and destination not in resolved.parents:
                raise RuntimeError(f"Unsafe path in Masscan archive: {member.name}")
            if member.issym() or member.islnk():
                raise RuntimeError(f"Links are not allowed in Masscan archive: {member.name}")
        bundle.extractall(destination, members=members)
    roots = [path for path in destination.iterdir() if path.is_dir()]
    if len(roots) != 1 or not (roots[0] / "Makefile").is_file():
        raise RuntimeError("Official archive has an unexpected layout")
    return roots[0]


def _clone_source(destination: Path) -> Path:
    """Fallback to the exact official tag commit when the release CDN is unavailable."""
    run_external_tool(
        "Git",
        ["git", "clone", "--filter=blob:none", "--no-checkout", SOURCE_REPOSITORY, str(destination)],
        operation="clone the official Masscan repository",
        check=True,
    )
    run_external_tool(
        "Git",
        ["git", "-C", str(destination), "checkout", "--detach", SOURCE_COMMIT],
        operation="check out Masscan 1.3.2",
        check=True,
    )
    actual = run_external_tool(
        "Git",
        ["git", "-C", str(destination), "rev-parse", "HEAD"],
        operation="verify the Masscan source revision",
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if actual != SOURCE_COMMIT:
        raise RuntimeError(f"Masscan source revision mismatch: expected {SOURCE_COMMIT}, got {actual}")
    if not (destination / "Makefile").is_file():
        raise RuntimeError("Official Masscan repository has an unexpected layout")
    return destination


def _apply_windows_compatibility(source: Path, progress: Progress | None) -> None:
    """Apply the minimal fixes needed by current 64-bit MinGW to upstream 1.3.2."""
    if platform.system() != "Windows":
        return
    timer = source / "src" / "pixie-timer.c"
    text = timer.read_text(encoding="utf-8")
    old = "int\nclock_gettime(int X, struct timeval *tv)"
    new = "int\nwin_clock_gettime(int X, struct timeval *tv)"
    if old in text:
        timer.write_text(text.replace(old, new, 1), encoding="utf-8")
    elif new not in text:
        raise RuntimeError("Masscan timer source changed; refusing to apply an unknown MinGW patch")
    safe_strings = source / "src" / "string_s.c"
    safe_text = safe_strings.read_text(encoding="utf-8")
    marker = "#ifdef __GNUC__\n\nerrno_t localtime_s"
    replacement = "#if defined(__GNUC__) && !defined(WIN32)\n\nerrno_t localtime_s"
    if marker in safe_text:
        safe_strings.write_text(safe_text.replace(marker, replacement, 1), encoding="utf-8")
    elif replacement not in safe_text:
        raise RuntimeError("Masscan safe-string source changed; refusing to apply an unknown MinGW patch")
    if progress:
        progress("Applied the upstream-compatible Windows timer fix")


def _build(source: Path, progress: Progress | None) -> Path:
    system = platform.system()
    make = shutil.which("mingw32-make") if system == "Windows" else shutil.which("make")
    make = make or shutil.which("gmake")
    if not make:
        requirement = "MinGW (mingw32-make + gcc)" if system == "Windows" else "make and a C compiler"
        raise RuntimeError(f"Masscan {MASSCAN_VERSION} is source-only; install {requirement} and retry")
    if system not in {"Windows", "Linux", "Darwin", "FreeBSD"}:
        raise RuntimeError(f"Unsupported Masscan build platform: {system}")
    compiler_names = ("gcc", "clang") if system == "Windows" else ("cc", "gcc", "clang")
    compiler = next((path for name in compiler_names if (path := shutil.which(name))), None)
    if not compiler:
        if system == "Windows":
            requirement = "MinGW gcc or clang (and ensure its bin directory is in PATH)"
        elif system == "Darwin":
            requirement = "a C compiler (run 'xcode-select --install')"
        else:
            requirement = "a C compiler (for Debian/Ubuntu: sudo apt install build-essential)"
        raise RuntimeError(f"Masscan {MASSCAN_VERSION} cannot be compiled: install {requirement} and retry")
    jobs = str(max(1, min(os.cpu_count() or 1, 8)))
    if progress:
        progress(f"Building Masscan for {system}/{platform.machine()} with {jobs} jobs")
    build_command = [make, f"-j{jobs}"]
    if system == "Windows":
        # The upstream Makefile relies on the usually-set OS variable. Some
        # launchers omit it, causing a Unix `which`/`cc` probe on Windows.
        build_command.extend(("OS=Windows_NT", f"CC={Path(compiler).name}", "FLAGS2="))
    else:
        build_command.append(f"CC={compiler}")
    completed = run_external_tool(
        "Masscan build tool",
        build_command,
        cwd=source,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        check=False,
    )
    executable = source / "bin" / ("masscan.exe" if system == "Windows" else "masscan")
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout)[-3000:]
        raise RuntimeError(f"Masscan build failed:\n{detail}")
    if not executable.is_file():
        raise missing_after_verification("Masscan", executable, "finish installation")
    return executable


def install_masscan(destination: Path, progress: Progress | None = None) -> Path:
    """Download, verify, build, and install the executable for the current OS."""
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="laitoxx-masscan-") as temporary:
        temp_dir = Path(temporary)
        archive = temp_dir / f"masscan-{MASSCAN_VERSION}.tar.gz"
        if progress:
            progress(f"Downloading official Masscan {MASSCAN_VERSION} source")
        download_error: Exception | None = None
        for attempt in range(1, 3):
            try:
                _download(archive, progress)
                source = _safe_extract(archive, temp_dir / "source")
                break
            except OSError as error:
                classified = normalize_external_tool_error(
                    "Masscan",
                    archive,
                    "download its verified source",
                    error,
                    existed_before=archive.is_file(),
                )
                if classified.security_suspected or classified.permission_or_security:
                    raise classified from error
                download_error = error
            except (RuntimeError, tarfile.TarError) as error:
                download_error = error
            if progress and attempt < 2:
                progress(f"Masscan release download failed (attempt {attempt}/2); retrying")
        else:
            if progress:
                progress(
                    "Release archive remained unavailable; using the exact official 1.3.2 Git revision "
                    f"({download_error})"
                )
            source = _clone_source(temp_dir / "repository")
        _apply_windows_compatibility(source, progress)
        built = _build(source, progress)
        target = destination / built.name
        temporary_target = destination / f".{built.name}.tmp"
        try:
            shutil.copy2(built, temporary_target)
            temporary_target.chmod(0o755)
            temporary_target.replace(target)
        except OSError as error:
            raise normalize_external_tool_error(
                "Masscan", target, "be installed", error, existed_before=built.is_file()
            ) from error
        if not target.is_file():
            raise missing_after_verification("Masscan", target, "start its version check")
    probe = run_external_tool(
        "Masscan",
        [str(target), "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    if probe.returncode not in {0, 1}:
        raise RuntimeError("Masscan was built but failed its version check")
    if progress:
        progress(f"Installed Masscan: {target}")
    return target
