"""Terms-of-Service acceptance state.

Acceptance is bound to the current machine via a hash of the hostname and
OS username. If the archive is transferred to another machine the stored
token will not match and the ToS dialog will be shown again.
"""
import hashlib
import os
import socket

from .paths import LEGACY_AGREEMENT, TOS_FILE


def _machine_token() -> str:
    """Return a short hash that identifies this machine/user combination."""
    raw = f"{socket.gethostname()}::{os.getlogin()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _migrate_if_needed():
    """Upgrade a bare 'agreed' file to a machine-bound token."""
    if not os.path.exists(TOS_FILE):
        return
    with open(TOS_FILE, "r", encoding="utf-8") as f:
        stored = f.read().strip()
    if stored == "agreed":
        # Old format — rewrite as machine-bound token so future checks work.
        with open(TOS_FILE, "w", encoding="utf-8") as f:
            f.write(_machine_token())


def is_accepted() -> bool:
    _migrate_if_needed()
    token = _machine_token()
    if os.path.exists(TOS_FILE):
        with open(TOS_FILE, "r", encoding="utf-8") as f:
            return f.read().strip() == token
    # Legacy file: treat as accepted only if it matches this machine's token.
    # A bare "agreed" from an old install is intentionally rejected here so
    # users who received a pre-agreed archive still see the ToS dialog.
    if os.path.exists(LEGACY_AGREEMENT):
        with open(LEGACY_AGREEMENT, "r", encoding="utf-8") as f:
            return f.read().strip() == token
    return False


def mark_accepted():
    token = _machine_token()
    os.makedirs(os.path.dirname(TOS_FILE), exist_ok=True)
    with open(TOS_FILE, "w", encoding="utf-8") as f:
        f.write(token)
    try:
        with open(LEGACY_AGREEMENT, "w", encoding="utf-8") as f:
            f.write(token)
    except OSError:
        pass
