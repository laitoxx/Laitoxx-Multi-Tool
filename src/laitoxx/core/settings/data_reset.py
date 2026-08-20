"""Bounded factory reset for application-owned settings and generated data."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .app_settings import settings
from .paths import CACHE_DIR, GRAPHS_DIR, LUA_PLUGIN_SETTINGS_FILE, REPORTS_DIR


@dataclass(slots=True)
class DataResetResult:
    removed_files: int = 0
    errors: list[str] = field(default_factory=list)


def _remove_file(path: Path, result: DataResetResult) -> None:
    try:
        path.unlink(missing_ok=True)
        result.removed_files += 1
    except OSError as exc:
        result.errors.append(f"{path}: {exc}")


def _clear_directory(directory: Path, result: DataResetResult) -> None:
    """Remove a known application directory's contents, but keep its root."""
    if not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)
        return
    for child in list(directory.iterdir()):
        try:
            if child.is_dir() and not child.is_symlink():
                result.removed_files += sum(1 for item in child.rglob("*") if item.is_file())
                shutil.rmtree(child)
            else:
                _remove_file(child, result)
        except OSError as exc:
            result.errors.append(f"{child}: {exc}")


def reset_application_data() -> DataResetResult:
    """Reset settings and remove only explicitly application-owned artifacts."""
    result = DataResetResult()
    result.errors.extend(settings.reset_to_defaults())

    try:
        LUA_PLUGIN_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        LUA_PLUGIN_SETTINGS_FILE.write_text("{}\n", encoding="utf-8")
    except OSError as exc:
        result.errors.append(f"{LUA_PLUGIN_SETTINGS_FILE}: {exc}")

    for directory in (CACHE_DIR, REPORTS_DIR, GRAPHS_DIR):
        _clear_directory(Path(directory), result)

    return result
