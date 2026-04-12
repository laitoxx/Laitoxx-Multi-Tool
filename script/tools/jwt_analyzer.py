"""
JWT Analyzer — decode, inspect, and brute-force HMAC-signed JWTs.

Supported algorithms: HS256, HS384, HS512

Modes
-----
1. Analyze  — decode header + payload, highlight dangerous claims,
              detect alg:none vulnerability.
2. Crack    — brute-force the HMAC secret via a wordlist file
              (logic ported from jwt-cracker-main Node.js project).

GUI  → jwt_analyzer_tool({"token": "...", "mode": "analyze"})
       jwt_analyzer_tool({"token": "...", "mode": "crack", "wordlist": "/path/to/list.txt"})
CLI  → jwt_analyzer_tool()
"""

import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone

from ..shared_utils import Color

_SUPPORTED_ALGOS = {"HS256": "sha256", "HS384": "sha384", "HS512": "sha512"}


def _b64_decode(segment: str) -> bytes:
    """URL-safe base64 decode with automatic padding."""
    segment += "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment)


def _parse_jwt(token: str):
    """Parse JWT into (header, payload, signature, raw_header, raw_payload) or None."""
    parts = token.strip().split(".")
    if len(parts) != 3:
        return None
    raw_header, raw_payload, raw_sig = parts
    try:
        header  = json.loads(_b64_decode(raw_header))
        payload = json.loads(_b64_decode(raw_payload))
        sig     = _b64_decode(raw_sig)
        return header, payload, sig, raw_header, raw_payload
    except Exception:
        return None


def _verify_signature(secret: str, content: str, raw_sig: str, algo: str) -> bool:
    """Verify HMAC signature for the given algorithm."""
    digest = _SUPPORTED_ALGOS[algo]
    computed = hmac.new(secret.encode(), content.encode(), digest).digest()
    computed_b64 = (
        base64.urlsafe_b64encode(computed)
        .rstrip(b"=")
        .decode()
    )
    return computed_b64 == raw_sig


def _print_header(header: dict):
    print(f"{Color.DARK_RED}┌─[ {Color.LIGHT_RED}Header {Color.DARK_RED}]" + "─" * 31)
    for k, v in header.items():
        color = Color.RED if k == "alg" and str(v).lower() == "none" else Color.WHITE
        print(f"{Color.DARK_GRAY}  - {Color.LIGHT_RED}{k:<14}{color}{v}")

    alg = header.get("alg", "")
    if str(alg).lower() == "none":
        print(f"\n{Color.DARK_GRAY}  [{Color.RED}!{Color.DARK_GRAY}]{Color.RED}"
              f" ALG:NONE vulnerability — signature not verified!")
    elif alg not in _SUPPORTED_ALGOS:
        print(f"\n{Color.DARK_GRAY}  [{Color.YELLOW}!{Color.DARK_GRAY}]{Color.YELLOW}"
              f" Algorithm '{alg}' is not HS256/384/512 — cracking not supported.")


def _print_payload(payload: dict):
    print(f"\n{Color.DARK_RED}├─[ {Color.LIGHT_RED}Payload {Color.DARK_RED}]" + "─" * 30)
    now = datetime.now(timezone.utc).timestamp()

    for k, v in payload.items():
        display = v
        if k in ("exp", "iat", "nbf") and isinstance(v, (int, float)):
            try:
                dt = datetime.fromtimestamp(v, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                display = f"{v}  ({dt})"
            except Exception:
                pass

        color = Color.WHITE
        if k == "exp" and isinstance(v, (int, float)) and v < now:
            color = Color.RED
            display = f"{display}  ← EXPIRED"
        elif k == "exp" and isinstance(v, (int, float)):
            color = Color.LIGHT_GREEN

        print(f"{Color.DARK_GRAY}  - {Color.LIGHT_RED}{k:<14}{color}{display}")

    sensitive_keys = {"password", "passwd", "secret", "token", "key", "apikey", "api_key"}
    found_sensitive = [k for k in payload if k.lower() in sensitive_keys]
    if found_sensitive:
        print(f"\n{Color.DARK_GRAY}  [{Color.RED}!{Color.DARK_GRAY}]{Color.RED}"
              f" Sensitive claim(s) in payload: {', '.join(found_sensitive)}")


def _analyze(token: str):
    result = _parse_jwt(token)
    if not result:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED}"
              f" Invalid JWT format (expected header.payload.signature).")
        return

    header, payload, _, raw_header, raw_payload = result

    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE}"
          f" JWT Analysis\n")
    _print_header(header)
    _print_payload(payload)

    print(f"\n{Color.DARK_RED}├─[ {Color.LIGHT_RED}Raw Segments {Color.DARK_RED}]" + "─" * 26)
    print(f"{Color.DARK_GRAY}  {Color.LIGHT_RED}Header:  {Color.DARK_GRAY}{raw_header}")
    print(f"{Color.DARK_GRAY}  {Color.LIGHT_RED}Payload: {Color.DARK_GRAY}{raw_payload}")

    print(f"\n{Color.DARK_RED}└" + "─" * 45)
    print(f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Analysis complete.")


def _crack(token: str, wordlist_path: str):
    result = _parse_jwt(token)
    if not result:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED}"
              f" Invalid JWT format.")
        return

    header, _, _, raw_header, raw_payload = result
    alg = header.get("alg", "")

    if alg not in _SUPPORTED_ALGOS:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED}"
              f" Algorithm '{alg}' not supported for cracking. Only HS256/384/512.")
        return

    raw_sig = token.strip().split(".")[2]
    content = f"{raw_header}.{raw_payload}"

    def _count_lines(path: str):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                for idx, _ in enumerate(fh, start=1):
                    pass
            return idx if "idx" in locals() else 0
        except OSError:
            return None

    total = _count_lines(wordlist_path)
    if total == 0:
        total = None

    if total:
        print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}!{Color.DARK_GRAY}]{Color.LIGHT_BLUE}"
              f" JWT Cracker - {Color.WHITE}{alg}{Color.LIGHT_BLUE}"
              f" - {Color.WHITE}{total:,} words\n")
    else:
        print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}!{Color.DARK_GRAY}]{Color.LIGHT_BLUE}"
              f" JWT Cracker - {Color.WHITE}{alg}{Color.LIGHT_BLUE}"
              f" - {Color.WHITE}unknown words\n")

    digest = _SUPPORTED_ALGOS[alg]
    found = None

    try:
        fh = open(wordlist_path, "r", encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        print(f"{Color.DARK_GRAY}[{Color.RED}x{Color.DARK_GRAY}]{Color.RED}"
              f" Wordlist file not found: {wordlist_path}")
        return

    with fh:
        for i, secret in enumerate(fh, start=1):
            secret = secret.strip()
            if not secret:
                continue

            computed = hmac.new(secret.encode(), content.encode(), digest).digest()
            computed_b64 = base64.urlsafe_b64encode(computed).rstrip(b"=").decode()

            if computed_b64 == raw_sig:
                found = secret
                break

            if i % 10000 == 0:
                if total:
                    pct = i / total * 100
                    print(f"\r{Color.DARK_GRAY}  Progress: {Color.LIGHT_RED}{i:,}{Color.DARK_GRAY}"
                          f"/{total:,}  ({pct:.1f}%)  last: {Color.WHITE}{secret[:40]}",
                          end="", flush=True)
                else:
                    print(f"\r{Color.DARK_GRAY}  Progress: {Color.LIGHT_RED}{i:,}{Color.DARK_GRAY}"
                          f"  last: {Color.WHITE}{secret[:40]}",
                          end="", flush=True)
    print()

    print(f"\n{Color.DARK_RED}└" + "─" * 45)
    if found:
        print(f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN}"
              f" SECRET FOUND: {Color.WHITE}{found}")
    else:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED}"
              f" Secret not found in wordlist.")

def jwt_analyzer_tool(data=None):
    if data:
        token    = data.get("token", "").strip()
        mode     = data.get("mode", "analyze")
        wordlist = data.get("wordlist", "")
    else:
        print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
              f" JWT Analyzer\n")
        print(f"  {Color.DARK_GRAY}[{Color.DARK_RED}1{Color.DARK_GRAY}]{Color.DARK_RED} Analyze token")
        print(f"  {Color.DARK_GRAY}[{Color.DARK_RED}2{Color.DARK_GRAY}]{Color.DARK_RED} Crack secret (wordlist)\n")

        mode_sel = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Select mode: "
        ).strip()
        mode = "crack" if mode_sel == "2" else "analyze"

        token = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
            f" Enter JWT token: {Color.RESET}"
        ).strip()

        wordlist = ""
        if mode == "crack":
            wordlist = input(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
                f" Enter wordlist path: {Color.RESET}"
            ).strip()

    if not token:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No token provided.")
        return

    if mode == "crack":
        if not wordlist:
            print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No wordlist path provided.")
            return
        _crack(token, wordlist)
    else:
        _analyze(token)
