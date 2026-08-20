"""Small, bounded second-stage banner probes for Masscan discoveries."""

from __future__ import annotations

import socket
import ssl
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from .fingerprints import fingerprint_banner
from .models import ServiceObservation

TLS_PORTS = {443, 465, 636, 853, 990, 993, 995, 2376, 5986, 8443}
HTTP_PORTS = {80, 443, 3000, 5000, 5601, 5985, 5986, 8000, 8008, 8080, 8081, 8443, 8888, 9000, 9200}
CancelCheck = Callable[[], bool]
ProbeProgress = Callable[[int, int], None]


def _recv(sock: socket.socket) -> bytes:
    chunks = []
    total = 0
    while total < 16_384:
        try:
            chunk = sock.recv(min(4096, 16_384 - total))
        except TimeoutError:
            break
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if len(chunk) < 4096:
            break
    return b"".join(chunks)


def probe_banner(observation: ServiceObservation, timeout: float = 1.5) -> str:
    """Read a greeting or send a harmless HTTP HEAD probe to an open TCP port."""
    with socket.create_connection((observation.ip, observation.port), timeout=timeout) as raw:
        raw.settimeout(0.45)
        sock: socket.socket = raw
        if observation.port in TLS_PORTS:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            sock = context.wrap_socket(raw, server_hostname=observation.ip)
            sock.settimeout(timeout)
        greeting = _recv(sock)
        if greeting:
            return greeting.decode("utf-8", errors="replace")
        if observation.service == "http" or observation.port in HTTP_PORTS or observation.service == "unknown":
            request = f"HEAD / HTTP/1.0\r\nHost: {observation.ip}\r\nConnection: close\r\n\r\n"
            sock.sendall(request.encode("ascii"))
            sock.settimeout(timeout)
            return _recv(sock).decode("utf-8", errors="replace")
    return ""


def service_from_banner(current: str, banner: str) -> str:
    upper = banner.lstrip().upper()
    if upper.startswith("SSH-"):
        return "ssh"
    if upper.startswith("HTTP/"):
        return "http"
    if upper.startswith("220"):
        lowered = banner.casefold()
        if "smtp" in lowered or "esmtp" in lowered:
            return "smtp"
        if "ftp" in lowered:
            return "ftp"
    if banner.startswith(("+PONG", "-ERR unknown command", "+OK")) and current == "redis":
        return "redis"
    return current


def enrich_banners(
    observations: list[ServiceObservation],
    *,
    cancelled: CancelCheck | None = None,
    progress: ProbeProgress | None = None,
    limit: int = 256,
) -> int:
    candidates = [item for item in observations if not item.banner][:limit]
    if not candidates:
        return 0
    completed = 0
    with ThreadPoolExecutor(max_workers=min(16, len(candidates)), thread_name_prefix="service-probe") as executor:
        futures = {executor.submit(probe_banner, item): item for item in candidates}
        for future in as_completed(futures):
            if cancelled and cancelled():
                for pending in futures:
                    pending.cancel()
                break
            observation = futures[future]
            try:
                banner = future.result()
            except (OSError, ssl.SSLError):
                banner = ""
            if banner:
                observation.banner = banner[:16_384]
                observation.service = service_from_banner(observation.service, observation.banner)
                matches = fingerprint_banner(observation.service, observation.banner)
                observation.fingerprint = matches[0] if matches else None
            completed += 1
            if progress:
                progress(completed, len(candidates))
    return completed
