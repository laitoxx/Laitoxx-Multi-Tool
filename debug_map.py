import sys
import os

from laitoxx.interfaces.gui.network_info_window import NetworkInfoWindow
from PyQt6.QtWidgets import QApplication

app = QApplication(sys.argv)
win = NetworkInfoWindow(mode="ip")
win.input_field.setText("1.1.1.1")
win._load_empty_map(37.386, -122.083, 11, "1.1.1.1", "1.1.1.1")

def save_html(html):
    with open("debug_output.html", "w") as f:
        f.write(html)
    app.quit()

win.map_view.page().toHtml(save_html)
app.exec()
