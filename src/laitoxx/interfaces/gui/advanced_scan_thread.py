# ruff: noqa: F405
from .advanced_web_scanner_support import *  # noqa: F403


class _ScanThread(QThread):
    provider_done = pyqtSignal(str, object)
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, target: str, options: ScanOptions):
        super().__init__()
        self.target = target
        self.options = options

    def run(self):
        try:
            scanner = AdvancedWebScanner(
                self.options,
                progress=lambda name, result: self.provider_done.emit(name, result),
            )
            self.completed.emit(scanner.scan(self.target))
        except Exception as exc:
            self.failed.emit(str(exc))
