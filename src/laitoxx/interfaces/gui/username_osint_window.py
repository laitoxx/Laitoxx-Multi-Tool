"""Composition root for UsernameOsintWindow."""
# ruff: noqa: F405

from .username_window_context import *  # noqa: F403
from .username_window_part1 import UsernameOsintMixin1
from .username_window_part2 import UsernameOsintMixin2
from .username_window_part3 import UsernameOsintMixin3
from .username_window_part4 import UsernameOsintMixin4


class UsernameOsintWindow(UsernameOsintMixin1, UsernameOsintMixin2, UsernameOsintMixin3, UsernameOsintMixin4, QDialog):
    def __init__(self, parent=None, theme_data=None, lua_plugins=None):
        super().__init__(parent)
        self.theme_data = theme_data or {}
        self._theme = self.theme_data
        self.lua_plugins = lua_plugins or []
        self._results: list[CheckResult] = []
        self._nickname_variants: list[str] = []
        self._thread: QThread | None = None
        self._worker: _CheckWorker | None = None
        self._avatar_downloader = AvatarDownloader()
        self._avatar_paths: dict[str, str] = {}
        self._db = SiteDB()
        self._db.load()
        self._is_searching = False
        self._correlation_worker: _CorrelationWorker | None = None
        self._recheck_jobs: list[tuple[QThread, _CheckWorker]] = []

        self.setWindowTitle(_t("uo_title", "Username OSINT"))
        self.setMinimumSize(820, 520)
        self.resize(1060, 660)

        self._build_ui()
        self._apply_global_style()
        self._restyle_widgets(self._theme)
