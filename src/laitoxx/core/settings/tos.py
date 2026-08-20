"""Terms-of-Service acceptance state.

Acceptance is bound to the current machine via a hash of the hostname and
OS username. If the archive is transferred to another machine the stored
token will not match and the ToS dialog will be shown again.
"""

import hashlib
import os
import socket

from .paths import TOS_FILE


def _machine_token() -> str:
    """Return a short hash that identifies this machine/user combination."""
    raw = f"{socket.gethostname()}::{os.getlogin()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def is_accepted() -> bool:
    token = _machine_token()
    if os.path.exists(TOS_FILE):
        with open(TOS_FILE, encoding="utf-8") as f:
            return f.read().strip() == token
    return False


def mark_accepted():
    token = _machine_token()
    os.makedirs(os.path.dirname(TOS_FILE), exist_ok=True)
    with open(TOS_FILE, "w", encoding="utf-8") as f:
        f.write(token)
