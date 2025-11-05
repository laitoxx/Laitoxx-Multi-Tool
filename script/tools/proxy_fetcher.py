import requests
from ..shared_utils import Color
_gevent_orig_ssl = None
try:
    # If gevent has monkeypatched ssl but preserved the original class as
    # orig_SSLContext, keep a reference to it for local use (do not overwrite
    # the global ssl.SSLContext — that breaks SSLSocket subclassing).
    import gevent.ssl as _gevent_ssl  # type: ignore
    _gevent_orig_ssl = getattr(_gevent_ssl, 'orig_SSLContext', None)
except Exception:
    _gevent_orig_ssl = None
    # No gevent or no orig_SSLContext available

PROXY_SCRAPER_RAW = {
    'http': 'https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/main/http.txt',
    'socks4': 'https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/main/socks4.txt',
    'socks5': 'https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/main/socks5.txt'
}


def choose_proxy_type_gui_fallback():
    """Return 'http'|'socks4'|'socks5' using a PyQt dialog when available, else console input."""
    # Try PyQt dialog when running inside the GUI
    try:
        from PyQt6.QtWidgets import QApplication, QComboBox
        from PyQt6.QtCore import Qt
        from gui import CustomInputDialog
        import threading

        app = QApplication.instance()
        if app is not None and threading.current_thread() is threading.main_thread():
            dialog = CustomInputDialog(None, "Proxy Type Selection", "Select proxy type:")
            dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
            dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

            combo = QComboBox()
            combo.addItems(['http', 'socks4', 'socks5'])
            dialog.layout.insertWidget(1, combo)
            dialog.input_text.hide()

            # Set default size and make sure dialog appears in front
            dialog.resize(300, 150)
            dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            
            result = dialog.exec()
            if result == 1:  # QDialog.Accepted
                return combo.currentText()
            return 'http'  # Default to http on cancel
    except Exception as e:
        print(f"GUI dialog failed: {str(e)}")
        # PyQt not available or failed — fall back to console
        pass

    # Console fallback
    choice = input(f"{Color.DARK_GRAY}  - {Color.WHITE}Select (1-3) [1]: {Color.RESET}")
    if choice is None:
        return None
    choice = choice.strip() or '1'
    mapping = {'1': 'http', '2': 'socks4', '3': 'socks5'}
    return mapping.get(choice, 'http')


def get_proxy_list():
    """Fetches proxy lists by type (http/socks4/socks5) from ProxyScraper raw files.

    The function asks the user which proxy type to download, fetches the corresponding
    raw GitHub file, cleans the list (keeps lines that look like IP:PORT), and offers
    to display or save the result. No validation or active checking is performed to
    avoid recursion/SSL issues; keep it as a simple fetcher.
    """
    # Choose proxy type via GUI dialog when available, else console
    proxy_type = choose_proxy_type_gui_fallback()
    if not proxy_type:
        return

    url = PROXY_SCRAPER_RAW.get(proxy_type)
    if not url:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Unsupported proxy type.")
        return

    print(f"\n{Color.DARK_GRAY}[{Color.LIGHT_BLUE}i{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Downloading {proxy_type} proxies from ProxyScraper...")

    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    try:
        # Disable SSL verification
        resp = session.get(url, timeout=20, verify=False)
        resp.raise_for_status()
        text = resp.text
    except requests.exceptions.RequestException as e:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Failed to fetch proxies: {e}")
        return

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    proxies = [p for p in lines if ':' in p]

    if not proxies:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No proxies found in the file.")
        return

    print(f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Fetched {len(proxies)} proxies ({proxy_type}).")

    # Display list: use GUI message box with option to open a viewer dialog when available
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog, QVBoxLayout, QTextEdit, QFileDialog
        import threading
        app = QApplication.instance()
        if app is not None and threading.current_thread() is threading.main_thread():
            resp = QMessageBox.question(None, 'Proxy fetcher', 'Display the list of fetched proxies?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
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
            # Save prompt
            save_resp = QMessageBox.question(None, 'Proxy fetcher', 'Save proxies to file?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if save_resp == QMessageBox.StandardButton.Yes:
                suggested = f"proxies_{proxy_type}.txt"
                filename, _ = QFileDialog.getSaveFileName(None, 'Save proxies', suggested, 'Text Files (*.txt);;All Files (*)')
                if filename:
                    try:
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write('\n'.join(proxies))
                        print(f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Saved {len(proxies)} proxies to {filename}")
                    except Exception as e:
                        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Failed to save file: {e}")
            return
    except Exception:
        # GUI not available or dialog failed; fall back to console
        pass

    # Console fallback for display/save
    show = input(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Display the list? (y/n) [n]: {Color.RESET}")
    if show and show.strip().lower() == 'y':
        for i, p in enumerate(proxies, 1):
            print(f"  {Color.DARK_GRAY}[{i:03d}]{Color.WHITE} {p}")

    save = input(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.WHITE} Save to file? (y/n) [y]: {Color.RESET}")
    if save is None or save.strip().lower() != 'n':
        filename = f"proxies_{proxy_type}.txt"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(proxies))
            print(f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Saved {len(proxies)} proxies to {filename}")
        except Exception as e:
            print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Failed to save file: {e}")
