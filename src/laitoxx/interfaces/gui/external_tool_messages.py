"""Localized presentation for structured external-executable failures."""

from __future__ import annotations

from laitoxx.core.external_tools import ExternalToolError
from laitoxx.core.localization.i18n import translator


def external_tool_message(error: object) -> str:
    if not isinstance(error, ExternalToolError):
        return str(error)
    if error.security_suspected:
        key = "external_tool_security_blocked"
    elif error.permission_or_security:
        key = "external_tool_permission_or_security"
    else:
        key = "external_tool_unavailable"
    return translator.get(
        key,
        tool=error.tool,
        path=error.executable,
        error=error.system_error,
    )
