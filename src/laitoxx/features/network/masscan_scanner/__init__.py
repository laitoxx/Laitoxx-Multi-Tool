"""Masscan discovery with local, explainable service fingerprinting.

Keep this package initializer side-effect free.  In particular, the standalone
source installer imports ``masscan_scanner.installer`` before the application's
settings directories are available or writable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import MasscanOptions, MasscanReport, ServiceObservation
    from .scanner import MasscanRunner


def masscan_scanner_tool(_data=None):
    """Registry placeholder; the GUI opens the dedicated workspace."""
    return None


def __getattr__(name: str) -> Any:
    """Load the public runtime types only when application code requests them."""
    if name == "MasscanRunner":
        from .scanner import MasscanRunner

        return MasscanRunner
    if name in {"MasscanOptions", "MasscanReport", "ServiceObservation"}:
        from . import models

        return getattr(models, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["MasscanOptions", "MasscanReport", "MasscanRunner", "ServiceObservation", "masscan_scanner_tool"]
