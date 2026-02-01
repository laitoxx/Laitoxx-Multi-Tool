from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Type, NoReturn, Optional
import datetime

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon


class Env:
    def __init__(self):
        self.logs_dir = Path(__file__).parent / "logs"
        self.logs_dir.mkdir(exist_ok=True)

    def setup(self) -> None:
        self._disable_gevent()
        self._restore_ssl()
        self._exc_handler()

    def _disable_gevent(self) -> None:
        try:
            import importlib
            gevent_monkey = importlib.import_module('gevent.monkey')
            if hasattr(gevent_monkey, 'patch_all'):
                gevent_monkey.patch_all = lambda *_, **__: None
        except ImportError:
            pass

    def _restore_ssl(self) -> None:
        try:
            import ssl
            if getattr(ssl.SSLContext, '__module__', '') != 'ssl':
                self.ssl_context(ssl)
        except Exception:
            pass

    def ssl_context(self, mod) -> None:
        try:
            import gevent.ssl
            if hasattr(gevent.ssl, 'orig_SSLContext'):
                mod.SSLContext = gevent.ssl.orig_SSLContext
        except ImportError:
            pass

    def _exc_handler(self) -> None:
        def handler(exc_type: Type, exc_value: Exception, exc_tb) -> None:
            if issubclass(exc_type, RecursionError):
                self._log_err(exc_type, exc_value, exc_tb)
            sys.__excepthook__(exc_type, exc_value, exc_tb)

        sys.excepthook = handler

    def _log_err(self, exc_type: Type, exc_value: Exception, exc_tb) -> None:
        try:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = self.logs_dir / f"recursion_error_{timestamp}.log"

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(''.join(traceback.format_exception(
                    exc_type, exc_value, exc_tb)))

            print(f"RecursionError saved to: {filename}", file=sys.stderr)
        except Exception:
            pass


class App:
    def __init__(self):
        self.app: Optional[QApplication] = None

    def run(self) -> NoReturn:
        guard = Env()
        guard.setup()

        from gui import MainWindow

        self.app = QApplication(sys.argv)
        self._set_icon()

        if not self._check_agreement():
            sys.exit(0)

        window = MainWindow()
        window.show()
        sys.exit(self.app.exec())

    def _set_icon(self) -> None:
        icon_path = Path(__file__).parent / "icons" / "ico.ico"
        if icon_path.exists():
            self.app.setWindowIcon(QIcon(str(icon_path)))

    def _check_agreement(self) -> bool:
        from gui import check_user_agreement, UserAgreementDialog

        if check_user_agreement():
            return True

        dialog = UserAgreementDialog()
        return dialog.exec() and getattr(dialog, 'agreed', False)


def main() -> None:
    launcher = App()
    launcher.run()


if __name__ == '__main__':
    main()
