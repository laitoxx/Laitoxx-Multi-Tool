"""Application-level tool descriptors and lazy handler loading.

The catalog contains metadata only. Feature modules are imported when a tool is
actually executed, so one optional dependency cannot break the whole GUI at
startup.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from importlib import import_module


@dataclass
class ToolSpec:
    """Declarative description of a tool exposed by the application."""

    handler: str
    input_type: str | None
    prompt: str | None
    desc: str
    threaded: bool
    disabled: bool = False
    _resolved_handler: Callable | None = field(default=None, init=False, repr=False)

    @property
    def func(self) -> Callable:
        """Resolve ``package.module:callable`` once, on first use."""
        if self._resolved_handler is None:
            module_name, separator, attribute = self.handler.partition(":")
            if not separator or not module_name or not attribute:
                raise ValueError(f"Invalid tool handler: {self.handler!r}")
            module = import_module(module_name)
            resolved = getattr(module, attribute)
            if not callable(resolved):
                raise TypeError(f"Tool handler is not callable: {self.handler}")
            self._resolved_handler = resolved
        return self._resolved_handler
