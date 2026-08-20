"""Background username-check worker independent from the dialog."""

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from laitoxx.features.osint.username_osint.checker import UsernameChecker


class CheckWorker(QObject):
    progress = pyqtSignal(int, int, object)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, sites, username, max_workers=50):
        super().__init__()
        self.sites = sites
        self.username = username
        self.max_workers = max_workers
        self._cancelled = False
        self._checker: UsernameChecker | None = None

    def cancel(self):
        self._cancelled = True
        if self._checker:
            self._checker.cancel()

    @pyqtSlot()
    def run(self):
        try:
            self._checker = UsernameChecker(
                self.sites,
                max_workers=self.max_workers,
                progress_callback=self._on_progress,
            )
            results = self._checker.check_username(self.username)
            if not self._cancelled:
                self.finished.emit(results)
        except Exception as exc:
            if not self._cancelled:
                self.error.emit(str(exc))

    def _on_progress(self, checked, total, result):
        if not self._cancelled:
            self.progress.emit(checked, total, result)
