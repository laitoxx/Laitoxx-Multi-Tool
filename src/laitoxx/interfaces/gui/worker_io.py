import builtins
import io
import re
import threading

from PyQt6.QtCore import QThread

# Global registry to keep references to stopped threads until they finish
# naturally, preventing "QThread: Destroyed while thread is still running" crashes.

_zombie_threads = []


def stop_and_detach_thread(thread: QThread, worker=None):
    """Safely stops a thread without blocking the GUI."""
    global _zombie_threads
    if thread and thread.isRunning():
        if worker and hasattr(worker, "cancel"):
            worker.cancel()
        thread.quit()
        thread.setParent(None)
        _zombie_threads.append(thread)

    # Clean up finished zombies
    _zombie_threads = [t for t in _zombie_threads if t.isRunning()]


def remove_ansi_codes(text):
    return re.sub(r"(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]", "", text)


_input_local = threading.local()

_original_input = builtins.input


def _thread_local_input(prompt=""):
    value = getattr(_input_local, "value", None)
    if value is not None:
        return value
    return _original_input(prompt)


builtins.input = _thread_local_input


class _InputOverride:
    """Context manager: sets per-thread input value and restores it on exit."""

    def __init__(self, value):
        self._value = value
        self._prev = None

    def __enter__(self):
        self._prev = getattr(_input_local, "value", None)
        _input_local.value = self._value
        return self

    def __exit__(self, *_):
        _input_local.value = self._prev


class SignalWriter(io.TextIOBase):
    def __init__(self, emit, transform=None, max_buffer=4096, cancel_event=None):
        self._emit = emit
        self._transform = transform or (lambda s: s)
        self._max_buffer = max(512, int(max_buffer))
        self._buf = []
        self._size = 0
        self._cancel_event = cancel_event

    def write(self, s):
        if self._cancel_event and self._cancel_event.is_set():
            return 0
        if not s:
            return 0
        self._buf.append(s)
        self._size += len(s)
        if "\n" in s or self._size >= self._max_buffer:
            self.flush()
        return len(s)

    def flush(self):
        if self._cancel_event and self._cancel_event.is_set():
            self._buf.clear()
            self._size = 0
            return
        if not self._buf:
            return
        text = "".join(self._buf)
        self._buf.clear()
        self._size = 0
        text = self._transform(text)
        if text:
            self._emit(text)
