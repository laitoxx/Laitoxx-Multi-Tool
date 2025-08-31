import sys
import traceback

# Early monkeypatch guard: disable gevent.monkey.patch_all before any imports that
# might trigger monkey-patching run. This must run as early as possible.
try:
    import importlib
    gevent_monkey = importlib.import_module('gevent.monkey')
    # Replace patch_all with a no-op to prevent unpredictable global monkeypatching
    if hasattr(gevent_monkey, 'patch_all'):
        gevent_monkey.patch_all = lambda *a, **k: None
    # Log a short diagnostic file
    try:
        import os, datetime
        logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        with open(os.path.join(logs_dir, f'gevent_guard_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'), 'w', encoding='utf-8') as fh:
            fh.write('gevent.monkey.patch_all disabled by startup guard\n')
    except Exception:
        pass
except Exception:
    # gevent not installed or import failed — ignore
    pass

from PyQt6.QtWidgets import QApplication
from gui import MainWindow


def _global_excepthook(exc_type, exc_value, exc_tb):
    """Global excepthook that captures RecursionError tracebacks to a file for diagnosis."""
    try:
        if issubclass(exc_type, RecursionError):
            tb_text = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
            # Write a timestamped dump to logs for later inspection
            import datetime, os
            logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            filename = os.path.join(logs_dir, f"recursion_traceback_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(tb_text)
            # Print short message to stderr so user sees it
            sys.stderr.write(f"RecursionError captured and written to {filename}\n")
        # Delegate to default handler afterwards
    except Exception:
        pass
    # Call the default handler to preserve normal behavior
    sys.__excepthook__(exc_type, exc_value, exc_tb)


def main():
    """
    This is the main entry point for the Laitoxx application.
    It initializes and shows the main GUI window.
    """
    # Install global excepthook early
    sys.excepthook = _global_excepthook

    # --- SSL monkeypatch protection (restore stdlib SSLContext if overridden) ---
    try:
        import ssl as _ssl
        # If SSLContext implementation is not from stdlib, try to restore
        ssl_module = getattr(_ssl.SSLContext, '__module__', '')
        if ssl_module != 'ssl':
            # Attempt to locate original in common monkeypatchers
            restored = False
            try:
                import gevent.ssl as _gevent_ssl  # type: ignore
                if getattr(_gevent_ssl, 'orig_SSLContext', None):
                    _ssl.SSLContext = _gevent_ssl.orig_SSLContext
                    restored = True
            except Exception:
                pass

            # Log diagnostic information
            try:
                import os, datetime
                logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
                os.makedirs(logs_dir, exist_ok=True)
                with open(os.path.join(logs_dir, f'ssl_patch_diag_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'), 'w', encoding='utf-8') as fh:
                    fh.write(f'ssl.SSLContext module before restore: {ssl_module}\n')
                    fh.write(f'restored_from_gevent: {restored}\n')
            except Exception:
                pass
    except Exception:
        # If anything goes wrong while checking/restoring SSL, ignore and continue
        pass

    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
