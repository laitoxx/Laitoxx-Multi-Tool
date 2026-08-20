"""Bounded Masscan subprocess orchestration and result enrichment."""

from __future__ import annotations

import ipaddress
import json
import os
import queue
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

from laitoxx.core.external_tools import popen_external_tool
from laitoxx.core.settings.paths import CACHE_DIR, TOOLS_DIR

from .banner_probe import enrich_banners
from .fingerprints import fingerprint_banner, service_for_port
from .models import MasscanOptions, MasscanReport, ServiceObservation

Progress = Callable[[float, str], None]
CancelCheck = Callable[[], bool]
_PROGRESS_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)%\s+done", re.IGNORECASE)
_PORT_TOKEN_RE = re.compile(r"^(\d+)(?:-(\d+))?$")


def find_masscan() -> str:
    name = "masscan.exe" if os.name == "nt" else "masscan"
    configured = os.getenv("LAITOXX_MASSCAN_PATH", "").strip()
    candidates = [
        Path(configured).expanduser() if configured else None,
        TOOLS_DIR / name,
        Path(sys.executable).resolve().parent / name,
    ]
    located = shutil.which("masscan")
    if located:
        candidates.append(Path(located))
    for candidate in candidates:
        if candidate and candidate.is_file():
            return str(candidate)
    return ""


def normalize_target(value: str) -> tuple[str, list[str]]:
    raw = (value or "").strip()
    if not raw:
        raise ValueError("Enter an IPv4 address, CIDR, or domain")
    parsed = urlparse(raw) if "://" in raw else None
    host = (parsed.hostname if parsed else raw) or raw
    try:
        network = ipaddress.ip_network(host, strict=False)
        if network.version != 4:
            raise ValueError("This Masscan workspace currently supports IPv4 targets")
        if network.num_addresses > 65_536:
            raise ValueError("The GUI limits one scan to 65,536 addresses (/16); split larger authorized scopes")
        return str(network) if "/" in host else str(network.network_address), []
    except ValueError as exc:
        if "/" in host or re.fullmatch(r"[\d.:]+", host):
            raise ValueError(str(exc)) from exc
    try:
        addresses = sorted({item[4][0] for item in socket.getaddrinfo(host, None, socket.AF_INET)})
    except socket.gaierror as exc:
        raise ValueError(f"Could not resolve domain: {host}") from exc
    if not addresses:
        raise ValueError(f"Domain has no IPv4 address: {host}")
    warnings = [f"{host} resolved to {addresses[0]}"]
    if len(addresses) > 1:
        warnings.append(f"Only the first of {len(addresses)} IPv4 addresses is scanned")
    return addresses[0], warnings


def validate_ports(value: str) -> str:
    tokens = [token.strip() for token in (value or "").split(",") if token.strip()]
    if not tokens:
        raise ValueError("Enter at least one TCP port or range")
    normalized = []
    total = 0
    for token in tokens:
        match = _PORT_TOKEN_RE.fullmatch(token)
        if not match:
            raise ValueError(f"Invalid port token: {token}")
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if not (1 <= start <= end <= 65535):
            raise ValueError(f"Port range is outside 1-65535: {token}")
        total += end - start + 1
        normalized.append(str(start) if start == end else f"{start}-{end}")
    if total > 65_535:
        raise ValueError("Port selection exceeds the TCP port space")
    return ",".join(normalized)


def _port_count(ports: str) -> int:
    count = 0
    for token in ports.split(","):
        start, separator, end = token.partition("-")
        count += int(end) - int(start) + 1 if separator else 1
    return count


def _decode_banner(service: dict) -> str:
    value = service.get("banner") or service.get("data") or ""
    return str(value).replace("\\x0a", "\n").replace("\\x0d", "\r").replace("\\r", "\r").replace("\\n", "\n")[:16_384]


def parse_masscan_json(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return []
    text = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = []
        for line in text.splitlines():
            line = line.strip().rstrip(",")
            if not line or line in {"[", "]"}:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                data.append(item)
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def observations_from_records(records: list[dict]) -> list[ServiceObservation]:
    observations: list[ServiceObservation] = []
    seen: set[tuple[str, int, str]] = set()
    for record in records:
        ip = str(record.get("ip") or "").strip()
        for port_data in record.get("ports") or []:
            try:
                port = int(port_data.get("port"))
            except (AttributeError, TypeError, ValueError):
                continue
            protocol = str(port_data.get("proto") or "tcp").casefold()
            key = (ip, port, protocol)
            if not ip or key in seen:
                continue
            seen.add(key)
            service_data = port_data.get("service") or {}
            detected = str(service_data.get("name") or "").strip().casefold()
            service = detected or service_for_port(port, protocol)
            banner = _decode_banner(service_data)
            matches = fingerprint_banner(service, banner)
            observations.append(
                ServiceObservation(
                    ip=ip,
                    port=port,
                    protocol=protocol,
                    state=str(port_data.get("status") or "open"),
                    reason=str(port_data.get("reason") or ""),
                    ttl=port_data.get("ttl") if isinstance(port_data.get("ttl"), int) else None,
                    service=service,
                    banner=banner,
                    fingerprint=matches[0] if matches else None,
                )
            )
    return sorted(observations, key=lambda item: (ipaddress.ip_address(item.ip), item.port, item.protocol))


class MasscanRunner:
    def __init__(self, executable: str = "") -> None:
        self.executable = executable or find_masscan()
        self._process: subprocess.Popen | None = None

    def cancel(self) -> None:
        process = self._process
        if process and process.poll() is None:
            process.terminate()

    def scan(
        self,
        target: str,
        options: MasscanOptions | None = None,
        *,
        progress: Progress | None = None,
        cancelled: CancelCheck | None = None,
    ) -> MasscanReport:
        if not self.executable:
            raise RuntimeError("Masscan is not installed; use the Install Masscan button")
        options = options or MasscanOptions()
        resolved, warnings = normalize_target(target)
        ports = validate_ports(options.ports)
        rate = max(1, min(int(options.rate), 10_000))
        address_count = ipaddress.ip_network(resolved, strict=False).num_addresses
        estimated_seconds = address_count * _port_count(ports) / rate
        if estimated_seconds > 900:
            raise ValueError(
                f"This scan is estimated to take {estimated_seconds / 60:.1f} minutes; "
                "narrow the scope/ports or raise the rate within the 10,000 pps limit"
            )
        deadline = time.monotonic() + max(60.0, min(1200.0, estimated_seconds * 2 + 30.0))
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        with tempfile.NamedTemporaryFile(prefix="masscan-", suffix=".json", dir=CACHE_DIR, delete=False) as output:
            output_path = Path(output.name)
        command = [
            self.executable,
            resolved,
            "-p",
            ports,
            "--rate",
            str(rate),
            "--wait",
            str(max(0, min(options.wait_seconds, 10))),
            "--output-format",
            "json",
            "--output-filename",
            str(output_path),
        ]
        if options.banners:
            command.append("--banners")
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            self._process = popen_external_tool(
                "Masscan",
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
            )
            stderr_lines = []
            assert self._process.stderr is not None
            line_queue: queue.Queue[str | None] = queue.Queue()

            def read_stderr() -> None:
                assert self._process is not None and self._process.stderr is not None
                for stderr_line in self._process.stderr:
                    line_queue.put(stderr_line)
                line_queue.put(None)

            reader = threading.Thread(target=read_stderr, name="masscan-stderr", daemon=True)
            reader.start()
            while True:
                if cancelled and cancelled():
                    self.cancel()
                    raise RuntimeError("Masscan scan cancelled")
                if time.monotonic() >= deadline:
                    self.cancel()
                    raise RuntimeError("Masscan exceeded its bounded runtime")
                try:
                    line = line_queue.get(timeout=0.1)
                except queue.Empty:
                    line = ""
                if line is None:
                    break
                if line:
                    stderr_lines.append(line)
                    match = _PROGRESS_RE.search(line)
                    if match and progress:
                        progress(float(match.group(1)) * (0.8 if options.banners else 1.0), line.strip())
                elif self._process.poll() is not None:
                    break
            return_code = self._process.wait(timeout=5)
            records = parse_masscan_json(output_path)
            if return_code != 0:
                detail = "".join(stderr_lines)[-3000:].strip()
                hint = " On Windows, install Npcap and run Laitoxx with administrator rights."
                raise RuntimeError(
                    f"Masscan exited with code {return_code}: {detail}.{hint if os.name == 'nt' else ''}"
                )
            observations = observations_from_records(records)
            if options.banners:
                enrich_banners(
                    observations,
                    cancelled=cancelled,
                    progress=(
                        lambda checked, total: (
                            progress(
                                80.0 + (20.0 * checked / max(1, total)),
                                f"Fingerprinting services: {checked}/{total}",
                            )
                            if progress
                            else None
                        )
                    ),
                )
                if len(observations) > 256:
                    warnings.append("Banner enrichment was limited to the first 256 open services")
            report = MasscanReport(
                target=target,
                resolved_target=resolved,
                options=MasscanOptions(
                    ports=ports, rate=rate, banners=options.banners, wait_seconds=options.wait_seconds
                ),
                observations=observations,
                command=command,
                duration_ms=round((time.monotonic() - started) * 1000),
                warnings=warnings,
                raw_records=records[:1000],
            )
            if progress:
                progress(100.0, "Masscan scan complete")
            return report
        finally:
            self._process = None
            try:
                output_path.unlink(missing_ok=True)
            except OSError:
                pass
