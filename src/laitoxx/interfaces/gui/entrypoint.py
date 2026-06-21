import datetime
import logging
import os
import sys
import webbrowser

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from laitoxx.core.settings.app_settings import settings
from laitoxx.core.settings.paths import ICONS_DIR
from laitoxx.core.settings.tos import is_accepted as check_user_agreement
from laitoxx.interfaces.gui.dialogs import UserAgreementDialog
from laitoxx.interfaces.gui.main_window import MainWindow

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
log_filename = os.path.join(
    LOG_DIR, f"gui_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout),
    ],
)

# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.info("Application starting...")

PROJECT_SITE = "https://laitoxx.wtf"


def _open_project_site():
    if not settings.open_website_on_startup:
        return
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        import requests

        from laitoxx.core.netcheck import build_proxies
        proxies = build_proxies(settings.proxy)
        requests.head(PROJECT_SITE, proxies=proxies, timeout=5,
                      allow_redirects=True, verify=False)
        webbrowser.open(PROJECT_SITE)
    except Exception:
        logging.info("Project site unreachable, skipping auto-open.")


def main():
    app = QApplication(sys.argv)

    icon_path = os.path.join(ICONS_DIR, "ico.ico")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(os.path.dirname(__file__), "icons", "ico.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    if not check_user_agreement():
        agreement = UserAgreementDialog()
        if not (agreement.exec() and agreement.agreed):
            sys.exit(0)
    _open_project_site()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical(f"Unhandled exception at top level: {e}", exc_info=True)
        sys.exit(1)
