"""Shared execution primitives for long running feature services."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import asdict, dataclass


class OperationCancelled(RuntimeError):
    """Raised when a cooperative operation receives a cancellation request."""


@dataclass(frozen=True)
class ProgressEvent:
    """Serializable progress update emitted by a feature service."""

    phase: str
    completed: int = 0
    total: int = 0
    message: str = ""
    item: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class OperationIssue:
    """A recoverable or fatal provider issue attached to a report."""

    source: str
    message: str
    code: str = "provider_error"
    recoverable: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


ProgressCallback = Callable[[ProgressEvent], None]


class JobControl:
    """Thread safe cooperative cancellation and pause control."""

    def __init__(self) -> None:
        self._cancelled = threading.Event()
        self._paused = False
        self._condition = threading.Condition()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    @property
    def paused(self) -> bool:
        with self._condition:
            return self._paused

    def cancel(self) -> None:
        self._cancelled.set()
        with self._condition:
            self._paused = False
            self._condition.notify_all()

    def pause(self) -> None:
        with self._condition:
            if not self.cancelled:
                self._paused = True

    def resume(self) -> None:
        with self._condition:
            self._paused = False
            self._condition.notify_all()

    def checkpoint(self) -> None:
        if self.cancelled:
            raise OperationCancelled("Operation cancelled")
        with self._condition:
            while self._paused and not self.cancelled:
                self._condition.wait(timeout=0.25)
        if self.cancelled:
            raise OperationCancelled("Operation cancelled")


def emit_progress(callback: ProgressCallback | None, event: ProgressEvent) -> None:
    """Emit a progress event without letting presentation errors stop work."""

    if callback is None:
        return
    try:
        callback(event)
    except Exception:
        return
