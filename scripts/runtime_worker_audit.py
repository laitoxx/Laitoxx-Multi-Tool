"""Runtime lifecycle checks for shared worker and stream primitives."""

from __future__ import annotations

import builtins
import threading
import time

from PyQt6.QtCore import QCoreApplication, QThread

from laitoxx.interfaces.gui.worker import Worker
from laitoxx.interfaces.gui.worker_io import SignalWriter, _InputOverride, remove_ansi_codes, stop_and_detach_thread


def worker_success_error_cancel() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])

    updates: list[str] = []
    errors: list[str] = []
    finished: list[bool] = []
    worker = Worker(lambda data: print(f"\x1b[31m{data['value']}\x1b[0m"), {"value": "ok"})
    worker.update.connect(updates.append)
    worker.error.connect(errors.append)
    worker.finished.connect(lambda: finished.append(True))
    worker.run()
    app.processEvents()
    assert "ok" in "".join(updates) and "\x1b" not in "".join(updates)
    assert not errors and finished == [True]

    errors.clear()
    failed = Worker(lambda: (_ for _ in ()).throw(ValueError("boom")))
    failed.error.connect(errors.append)
    failed.run()
    app.processEvents()
    assert errors == ["An error occurred: boom"]

    called = []
    cancelled = Worker(lambda: called.append(True))
    cancelled.finished.connect(lambda: finished.append(True))
    cancelled.cancel()
    cancelled.run()
    assert not called and len(finished) == 2


def input_isolation() -> None:
    original = builtins.input
    assert original("fallback") if False else True
    with _InputOverride("outer"):
        assert builtins.input() == "outer"
        with _InputOverride("inner"):
            assert builtins.input() == "inner"
        assert builtins.input() == "outer"

    barrier = threading.Barrier(3)
    seen: list[str] = []

    def read(value: str) -> None:
        with _InputOverride(value):
            barrier.wait()
            seen.append(builtins.input())
            barrier.wait()

    threads = [threading.Thread(target=read, args=(value,)) for value in ("one", "two")]
    for thread in threads:
        thread.start()
    barrier.wait()
    barrier.wait()
    for thread in threads:
        thread.join(1)
    assert sorted(seen) == ["one", "two"]


def stream_and_thread_lifecycle() -> None:
    emitted: list[str] = []
    cancelled = threading.Event()
    writer = SignalWriter(emitted.append, transform=str.upper, max_buffer=512, cancel_event=cancelled)
    assert writer.write("one") == 3
    assert writer.write(" two\n") == 5
    assert emitted == ["ONE TWO\n"]
    writer.write("discard")
    cancelled.set()
    writer.flush()
    assert emitted == ["ONE TWO\n"]
    assert remove_ansi_codes("\x1b[31mred\x1b[0m") == "red"

    thread = QThread()
    thread.start()
    deadline = time.monotonic() + 2
    while not thread.isRunning() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert thread.isRunning()
    stop_and_detach_thread(thread)
    assert thread.wait(2000)
    stop_and_detach_thread(thread)


def main() -> int:
    for case in (worker_success_error_cancel, input_isolation, stream_and_thread_lifecycle):
        case()
        print(f"PASS {case.__name__}")
    print("cases=3 failed=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
