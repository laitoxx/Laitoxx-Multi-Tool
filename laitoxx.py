import sys
from PyQt6.QtWidgets import QApplication
from gui import MainWindow

def main():
    """
    This is the main entry point for the Laitoxx application.
    It initializes and shows the main GUI window.
    """
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
