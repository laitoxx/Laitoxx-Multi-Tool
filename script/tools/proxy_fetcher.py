import requests

from typing import Dict, Any
from ..shared_utils import Color

_gevent_orig_ssl = None
try:
    import gevent.ssl as _gevent_ssl  # type: ignore
    _gevent_orig_ssl = getattr(_gevent_ssl, 'orig_SSLContext', None)
except Exception:
    _gevent_orig_ssl = None

PROXY_SCRAPER_RAW: Dict[str, str] = {
    'http': 'https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/main/http.txt',
    'socks4': 'https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/main/socks4.txt',
    'socks5': 'https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/main/socks5.txt'
}


def choose_proxy_type_gui_fallback() -> Any | str | None:
    try:
        import threading

        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QApplication, QComboBox

        from gui import CustomInputDialog

        app = QApplication.instance()
        if app is not None and threading.current_thread() is threading.main_thread():
            dialog = CustomInputDialog(
                None, "Proxy Type Selection", "Select proxy type:")
            dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
            dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

            combo = QComboBox()
            combo.addItems(['http', 'socks4', 'socks5'])
            dialog.layout.insertWidget(1, combo)
            dialog.input_text.hide()

            dialog.resize(300, 150)
            dialog.setWindowFlags(dialog.windowFlags() |
                                  Qt.WindowType.WindowStaysOnTopHint)

            result = dialog.exec()
            if result == 1:
                return combo.currentText()
            return 'http'
    except Exception as e:
        print(f"GUI dialog failed: {str(e)}")
        pass

    choice = input(
        f"{Color.DARK_GRAY}  - {Color.WHITE}Select (1-3) [1]: {Color.RESET}")
    if choice is None:
        return None
    choice = choice.strip() or '1'
    mapping = {'1': 'http', '2': 'socks4', '3': 'socks5'}
    return mapping.get(choice, 'http')


def get_proxy_list() -> None:
    proxy_type = choose_proxy_type_gui_fallback()
    if not proxy_type:
        return

    url = PROXY_SCRAPER_RAW.get(proxy_type)
    if not url:
        print(
            f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Unsupported proxy type.")
        return

    print(
        f"\n{Color.DARK_GRAY}[{Color.LIGHT_BLUE}i{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Downloading {proxy_type} proxies from ProxyScraper...")

    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    try:
        resp = session.get(url, timeout=20, verify=False)
        resp.raise_for_status()
        text = resp.text
    except requests.exceptions.RequestException as e:
        print(
            f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Failed to fetch proxies: {e}")
        return

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    proxies = [p for p in lines if ':' in p]

    if not proxies:
        print(
            f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No proxies found in the file.")
        return

    print(
        f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Fetched {len(proxies)} proxies ({proxy_type}).")

    try:
        import threading

        from PyQt6.QtWidgets import (QApplication, QDialog, QFileDialog,
                                     QMessageBox, QTextEdit, QVBoxLayout)
        app = QApplication.instance()
        if app is not None and threading.current_thread() is threading.main_thread():
            resp = QMessageBox.question(None, 'Proxy fetcher', 'Display the list of fetched proxies?',
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if resp == QMessageBox.StandardButton.Yes:
                dlg = QDialog()
                dlg.setWindowTitle('Proxies')
                layout = QVBoxLayout(dlg)
                te = QTextEdit()
                te.setReadOnly(True)
                te.setPlainText('\n'.join(proxies))
                layout.addWidget(te)
                dlg.resize(800, 600)
                dlg.exec()
            save_resp = QMessageBox.question(
                None, 'Proxy fetcher', 'Save proxies to file?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if save_resp == QMessageBox.StandardButton.Yes:
                suggested = f"proxies_{proxy_type}.txt"
                filename, _ = QFileDialog.getSaveFileName(
                    None, 'Save proxies', suggested, 'Text Files (*.txt);;All Files (*)')
                if filename:
                    try:
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write('\n'.join(proxies))
                        print(
                            f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Saved {len(proxies)} proxies to {filename}")
                    except Exception as e:
                        print(
                            f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Failed to save file: {e}")
            return
    except Exception:
        pass

    show = input(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Display the list? (y/n) [n]: {Color.RESET}")
    if show and show.strip().lower() == 'y':
        for i, p in enumerate(proxies, 1):
            print(f"  {Color.DARK_GRAY}[{i:03d}]{Color.WHITE} {p}")

    save = input(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Save to file? (y/n) [y]: {Color.RESET}")
    if save is None or save.strip().lower() != 'n':
        filename = f"proxies_{proxy_type}.txt"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(proxies))
            print(
                f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Saved {len(proxies)} proxies to {filename}")
        except Exception as e:
            print(
                f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Failed to save file: {e}")
