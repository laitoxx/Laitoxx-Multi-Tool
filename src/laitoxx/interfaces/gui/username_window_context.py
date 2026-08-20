"""Support namespace for UsernameOsintWindow slices."""

from .username_widget_accent_button import _AccentButton as _AccentButton
from .username_widget_correlation_worker import _CorrelationWorker as _CorrelationWorker
from .username_widget_ghost_button import _GhostButton as _GhostButton
from .username_widget_glass_panel import _GlassPanel as _GlassPanel
from .username_widget_result_row import _ResultRow as _ResultRow
from .username_widget_section_label import _SectionLabel as _SectionLabel
from .username_widget_stat_card import _StatCard as _StatCard
from .username_window_base import *  # noqa: F403
from .username_window_base import __all__ as _base_all

__all__ = [
    *_base_all,
    "_GlassPanel",
    "_AccentButton",
    "_GhostButton",
    "_SectionLabel",
    "_StatCard",
    "_ResultRow",
    "_CorrelationWorker",
]
