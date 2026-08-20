"""Application adapter for the locally compiled CogniPass generator."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from laitoxx.core.external_tools import popen_external_tool


class CogniPassError(RuntimeError):
    pass


class CogniPassCancelled(CogniPassError):
    pass


@dataclass(slots=True)
class ChildProfile:
    first_name: str
    birth_date: str = ""


@dataclass(slots=True)
class CogniPassProfile:
    first_name: str = ""
    last_name: str = ""
    middle_name: str = ""
    birth_date: str = ""
    pet: str = ""
    team: str = ""
    spouse_first_name: str = ""
    spouse_last_name: str = ""
    spouse_birth_date: str = ""
    children: list[ChildProfile] = field(default_factory=list)
    pin_only: bool = False
    minimum_length: int = 8
    maximum_length: int = 32
    count: int = 10_000
    output_path: Path = Path("cognipass.txt")


@dataclass(slots=True)
class CogniPassResult:
    output_path: Path
    line_count: int
    file_size: int
    preview: list[str]
    process_output: str


def find_cognipass_binary() -> Path | None:
    executable = "cognipass.exe" if os.name == "nt" else "cognipass"
    configured = os.getenv("LAITOXX_COGNIPASS_PATH", "").strip()
    candidates = [
        Path(configured) if configured else None,
        Path(sys.executable).resolve().parent / executable,
        Path(sys.prefix) / ("Scripts" if os.name == "nt" else "bin") / executable,
    ]
    located = shutil.which("cognipass")
    if located:
        candidates.append(Path(located))
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate.resolve()
    return None


def _validate_ascii_name(value: str, label: str) -> str:
    value = value.strip()
    if value and (not value.isascii() or not value.isalpha()):
        raise CogniPassError(f"{label} must contain English letters only")
    return value


def _validate_context(value: str, label: str) -> str:
    value = value.strip()
    if value and (not value.isascii() or any(not (char.isalnum() or char == " ") for char in value)):
        raise CogniPassError(f"{label} may contain English letters, digits and spaces only")
    return value


def _validate_date(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        return ""
    try:
        parsed = datetime.strptime(value, "%d.%m.%Y")
    except ValueError as error:
        raise CogniPassError(f"{label} must use DD.MM.YYYY") from error
    if parsed.year < 1900 or parsed.date() > datetime.now().date():
        raise CogniPassError(f"{label} is outside the supported date range")
    return value


def validate_profile(profile: CogniPassProfile) -> CogniPassProfile:
    profile.first_name = _validate_ascii_name(profile.first_name, "First name")
    profile.last_name = _validate_ascii_name(profile.last_name, "Last name")
    profile.middle_name = _validate_ascii_name(profile.middle_name, "Middle name")
    profile.birth_date = _validate_date(profile.birth_date, "Birth date")
    profile.pet = _validate_context(profile.pet, "Pet")
    profile.team = _validate_context(profile.team, "Team")
    profile.spouse_first_name = _validate_ascii_name(
        profile.spouse_first_name,
        "Spouse first name",
    )
    profile.spouse_last_name = _validate_ascii_name(
        profile.spouse_last_name,
        "Spouse last name",
    )
    profile.spouse_birth_date = _validate_date(
        profile.spouse_birth_date,
        "Spouse birth date",
    )
    for index, child in enumerate(profile.children, 1):
        child.first_name = _validate_ascii_name(child.first_name, f"Child {index} name")
        child.birth_date = _validate_date(child.birth_date, f"Child {index} birth date")
        if not child.first_name:
            raise CogniPassError(f"Child {index} name is empty")
    if profile.minimum_length < 1 or profile.maximum_length > 128:
        raise CogniPassError("Password length must be between 1 and 128")
    if profile.minimum_length > profile.maximum_length:
        raise CogniPassError("Minimum length cannot exceed maximum length")
    if profile.count < 0 or profile.count > 10_000_000:
        raise CogniPassError("Candidate count must be between 0 and 10,000,000")
    if not any(
        (
            profile.first_name,
            profile.last_name,
            profile.middle_name,
            profile.birth_date,
            profile.pet,
            profile.team,
            profile.spouse_first_name,
            profile.spouse_last_name,
            profile.spouse_birth_date,
            profile.children,
        )
    ):
        raise CogniPassError("Add at least one piece of target information")
    profile.output_path = Path(profile.output_path).expanduser().resolve()
    return profile


def build_interactive_input(profile: CogniPassProfile, temporary_name: str) -> str:
    """Build the exact stdin sequence expected by CogniPass v1.0."""
    spouse = bool(profile.spouse_first_name or profile.spouse_last_name or profile.spouse_birth_date)
    lines = [
        profile.first_name,
        profile.last_name,
        profile.middle_name,
        profile.birth_date,
        profile.pet,
        profile.team,
        "y" if spouse else "n",
    ]
    if spouse:
        lines.extend(
            (
                profile.spouse_first_name,
                profile.spouse_last_name,
                profile.spouse_birth_date,
            )
        )
    lines.append("y" if profile.children else "n")
    if profile.children:
        lines.append(str(len(profile.children)))
        for child in profile.children:
            lines.extend((child.first_name, child.birth_date))
    lines.extend(
        (
            "y" if profile.pin_only else "n",
            str(profile.minimum_length),
            str(profile.maximum_length),
            str(profile.count),
            temporary_name,
        )
    )
    return "\n".join(lines) + "\n"


def generate_candidates(
    profile: CogniPassProfile,
    *,
    cancel_check: Callable[[], bool] | None = None,
    timeout: float = 3600,
) -> CogniPassResult:
    profile = validate_profile(profile)
    binary = find_cognipass_binary()
    if binary is None:
        raise CogniPassError("CogniPass is not installed. Run install.bat or install.sh to build it for this CPU.")
    output = profile.output_path
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".cognipass-",
        suffix=".txt",
        dir=output.parent,
    )
    os.close(descriptor)
    temporary_path = Path(temporary)
    temporary_path.unlink(missing_ok=True)
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process: subprocess.Popen | None = None
    try:
        process = popen_external_tool(
            "CogniPass",
            [str(binary), "--interactive"],
            cwd=output.parent,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creation_flags,
        )
        captured: dict[str, str] = {"stdout": "", "stderr": ""}
        communication_error: list[BaseException] = []

        def communicate() -> None:
            try:
                stdout, stderr = process.communicate(input=build_interactive_input(profile, temporary_path.name))
                captured["stdout"] = stdout or ""
                captured["stderr"] = stderr or ""
            except BaseException as error:  # retained and raised on the caller thread
                communication_error.append(error)

        communicator = threading.Thread(
            target=communicate,
            name="cognipass-stdio",
            daemon=True,
        )
        communicator.start()
        started = time.monotonic()
        while process.poll() is None:
            if cancel_check and cancel_check():
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
                communicator.join(timeout=2)
                raise CogniPassCancelled("Generation cancelled")
            if time.monotonic() - started > timeout:
                process.kill()
                process.wait(timeout=2)
                communicator.join(timeout=2)
                raise CogniPassError("CogniPass generation timed out")
            time.sleep(0.05)
        communicator.join(timeout=5)
        if communicator.is_alive():
            raise CogniPassError("CogniPass output streams did not close after the process exited")
        if communication_error:
            raise CogniPassError(f"CogniPass communication failed: {communication_error[0]}")
        stdout = captured["stdout"]
        stderr = captured["stderr"]
        if process.returncode:
            detail = (stderr or stdout).strip()
            raise CogniPassError(detail or f"CogniPass exited with code {process.returncode}")
        if not temporary_path.is_file():
            raise CogniPassError((stdout or "CogniPass did not create an output file").strip())
        preview: list[str] = []
        line_count = 0
        with temporary_path.open(encoding="utf-8", errors="replace") as stream:
            for line in stream:
                value = line.rstrip("\r\n")
                if len(preview) < 100:
                    preview.append(value)
                line_count += 1
        file_size = temporary_path.stat().st_size
        os.replace(temporary_path, output)
        return CogniPassResult(output, line_count, file_size, preview, stdout.strip())
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
        temporary_path.unlink(missing_ok=True)


def cognipass_tool(*_args, **_kwargs):
    return "CogniPass is available through its dedicated utility window."
