"""Application composition root.

Only this module knows how infrastructure, settings and the PyQt presentation
layer are assembled. Feature modules stay independent from application startup.
"""

from __future__ import annotations

import datetime
import logging
import sys
import webbrowser
from pathlib import Path

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

try:
    if hasattr(Qt.ApplicationAttribute, "AA_ShareOpenGLContexts"):
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
    from PyQt6 import QtWebEngineWidgets  # noqa: F401
except Exception:
    pass

from laitoxx.core.settings.app_settings import settings
from laitoxx.core.settings.network_manager import NetworkManager
from laitoxx.core.settings.paths import ICONS_DIR, LOGS_DIR
from laitoxx.core.settings.tos import is_accepted as check_user_agreement
from laitoxx.interfaces.gui.dialogs import UserAgreementDialog
from laitoxx.interfaces.gui.main_window import MainWindow

PROJECT_SITE = "https://laitoxx.wtf"


def configure_logging() -> Path:
    """Configure application logging and return the active log path."""
    log_dir = Path(LOGS_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"gui_{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}.log"
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_path), logging.StreamHandler(sys.stdout)],
    )
    return log_path


def _open_project_site() -> None:
    if not settings.open_website_on_startup:
        return
    try:
        import requests
        import urllib3

        from laitoxx.core.netcheck import build_proxies

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        requests.head(
            PROJECT_SITE,
            proxies=build_proxies(settings.proxy),
            timeout=5,
            allow_redirects=True,
            verify=False,
        )
        webbrowser.open(PROJECT_SITE)
    except Exception:
        logging.info("Project site unreachable, skipping auto-open.")


def create_application(argv: list[str] | None = None) -> tuple[QApplication, MainWindow | None]:
    """Build the QApplication and main window without entering the event loop."""
    app = QApplication(argv if argv is not None else sys.argv)
    NetworkManager.apply(settings.proxy)

    icon_path = Path(ICONS_DIR) / "ico.ico"
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))

    if not check_user_agreement():
        agreement = UserAgreementDialog()
        if not (agreement.exec() and agreement.agreed):
            return app, None

    _open_project_site()
    return app, MainWindow()


def main() -> None:
    """Launch the desktop application."""
    configure_logging()
    logging.info("Application starting...")
    try:
        app, window = create_application()
        if window is None:
            raise SystemExit(0)
        window.show()
        raise SystemExit(app.exec())
    except SystemExit:
        raise
    except Exception as exc:
        logging.critical("Unhandled exception at top level: %s", exc, exc_info=True)
        raise SystemExit(1) from exc
