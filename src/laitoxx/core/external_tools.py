"""Safe process boundary and user-facing diagnostics for external tools."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

_SECURITY_WINERRORS = {225, 577, 1260}
_POSSIBLE_SECURITY_WINERRORS = {5}
_SECURITY_MARKERS = (
    "antivirus",
    "anti-virus",
    "avast",
    "quarantine",
    "potentially unwanted",
    "contains a virus",
    "blocked by group policy",
)
_MAX_SECURITY_LOG_BYTES = 512 * 1024


class ExternalToolError(RuntimeError):
    """A normalized failure at the boundary of a non-Python executable."""

    def __init__(
        self,
        tool: str,
        executable: str | Path,
        operation: str,
        system_error: str,
        *,
        security_suspected: bool = False,
        permission_or_security: bool = False,
    ) -> None:
        self.tool = tool
        self.executable = str(executable)
        self.operation = operation
        self.system_error = system_error
        self.security_suspected = security_suspected
        self.permission_or_security = permission_or_security
        if security_suspected:
            explanation = (
                "Antivirus or other security software (including Avast) likely blocked or quarantined the file. "
                "Check its quarantine/history and allow only this exact executable after verifying and trusting it; "
                "do not disable protection globally."
            )
        elif permission_or_security:
            explanation = (
                "Access was denied. File permissions or security software (including Avast) may be responsible. "
                "Check the file permissions and antivirus quarantine/history; allow only this exact trusted file."
            )
        else:
            explanation = "Verify that the tool is installed and that the configured executable path is valid."
        super().__init__(
            f"{tool} could not {operation}.\nPath: {self.executable}\nSystem error: {system_error}\n{explanation}"
        )


def _path_from_command(command: Sequence[str | os.PathLike[str]]) -> Path:
    return Path(os.fspath(command[0])).expanduser() if command else Path("")


def _avast_block_recorded(executable: str | Path) -> bool:
    """Check Avast Hardened Mode's bounded local log for this exact path."""
    if os.name != "nt":
        return False
    program_data = os.getenv("PROGRAMDATA", "").strip()
    if not program_data:
        return False
    log_path = Path(program_data) / "Avast Software" / "Avast" / "log" / "hardenedmode.log"
    try:
        size = log_path.stat().st_size
        with log_path.open("rb") as stream:
            stream.seek(max(0, size - _MAX_SECURITY_LOG_BYTES))
            raw = stream.read(_MAX_SECURITY_LOG_BYTES)
    except OSError:
        return False
    encoding = "utf-16-le" if raw.count(b"\x00") > len(raw) // 4 else "utf-8"
    text = raw.decode(encoding, errors="replace").casefold()
    expected = str(Path(executable).resolve()).casefold()
    return any("blocked:" in line and expected in line for line in text.splitlines())


def normalize_external_tool_error(
    tool: str,
    executable: str | Path,
    operation: str,
    error: OSError,
    *,
    existed_before: bool = False,
) -> ExternalToolError:
    """Classify an OS launch/access error without claiming every missing file is AV activity."""
    winerror = getattr(error, "winerror", None)
    text = str(error)
    folded = text.casefold()
    exists_after = Path(executable).is_file()
    vanished = existed_before and not exists_after
    avast_recorded = _avast_block_recorded(executable)
    security_suspected = bool(
        vanished
        or avast_recorded
        or winerror in _SECURITY_WINERRORS
        or any(marker in folded for marker in _SECURITY_MARKERS)
    )
    permission_or_security = bool(
        not security_suspected
        and os.name == "nt"
        and (winerror in _POSSIBLE_SECURITY_WINERRORS or isinstance(error, PermissionError))
    )
    if vanished:
        text = f"{text}; the executable existed immediately before launch but then disappeared"
    if avast_recorded:
        text = f"{text}; Avast Hardened Mode recorded this exact executable as blocked"
    return ExternalToolError(
        tool,
        executable,
        operation,
        text,
        security_suspected=security_suspected,
        permission_or_security=permission_or_security,
    )


def missing_after_verification(tool: str, executable: str | Path, operation: str) -> ExternalToolError:
    """Report a verified/generated executable disappearing before its next use."""
    return ExternalToolError(
        tool,
        executable,
        operation,
        "the verified executable disappeared before it could be used",
        security_suspected=True,
    )


def popen_external_tool(
    tool: str,
    command: Sequence[str | os.PathLike[str]],
    *,
    operation: str = "start",
    **kwargs: Any,
) -> subprocess.Popen:
    executable = _path_from_command(command)
    existed_before = executable.is_file()
    try:
        return subprocess.Popen(command, **kwargs)  # noqa: S603
    except OSError as error:
        raise normalize_external_tool_error(
            tool, executable, operation, error, existed_before=existed_before
        ) from error


def run_external_tool(
    tool: str,
    command: Sequence[str | os.PathLike[str]],
    *,
    operation: str = "run",
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    executable = _path_from_command(command)
    existed_before = executable.is_file()
    try:
        return subprocess.run(command, **kwargs)  # noqa: S603
    except OSError as error:
        raise normalize_external_tool_error(
            tool, executable, operation, error, existed_before=existed_before
        ) from error
