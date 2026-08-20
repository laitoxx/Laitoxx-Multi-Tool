"""Advanced multi-source internet exposure scanner."""

from .engine import AdvancedWebScanner
from .models import ScanReport, normalize_target
from .options import ScanOptions

__all__ = ["AdvancedWebScanner", "ScanOptions", "ScanReport", "advanced_web_scanner_tool", "normalize_target"]


def advanced_web_scanner_tool():
    """Registry marker; the GUI is opened by ToolInputController."""
    return None
