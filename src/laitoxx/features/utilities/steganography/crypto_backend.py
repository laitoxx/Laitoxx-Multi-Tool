"""Optional cryptography backend capability detection."""

import subprocess
import sys

# Probe native bindings in a child process first: a broken Rust/OpenSSL wheel
# can terminate the interpreter before Python gets a chance to raise an
# exception.  Use the active interpreter so this also works in Windows venvs.
HAS_CRYPTO = False
Cipher = algorithms = default_backend = modes = padding = None
try:
    probe = subprocess.run(
        [sys.executable, "-c", "from cryptography.exceptions import InvalidSignature"],
        capture_output=True,
        timeout=5,
    )
    if probe.returncode == 0:
        from cryptography.hazmat.backends import default_backend as _default_backend
        from cryptography.hazmat.primitives import padding as _padding
        from cryptography.hazmat.primitives.ciphers import Cipher as _Cipher
        from cryptography.hazmat.primitives.ciphers import algorithms as _algorithms
        from cryptography.hazmat.primitives.ciphers import modes as _modes

        Cipher = _Cipher
        algorithms = _algorithms
        default_backend = _default_backend
        modes = _modes
        padding = _padding
        HAS_CRYPTO = True
except Exception:
    HAS_CRYPTO = False
