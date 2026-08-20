"""Process execution and normalization helpers for optional local scanners."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from laitoxx.core.external_tools import ExternalToolError, run_external_tool

from .models import ProviderResult

CVE_RE = re.compile(r"CVE-\d{4}-\d{4,}", re.IGNORECASE)
HIGH_VALUE_PORTS = (
    21,
    22,
    23,
    25,
    53,
    80,
    110,
    111,
    135,
    139,
    143,
    389,
    443,
    445,
    465,
    587,
    631,
    636,
    993,
    995,
    1433,
    1521,
    2049,
    2083,
    2375,
    2376,
    3000,
    3306,
    3389,
    4222,
    4646,
    5432,
    5601,
    5672,
    5900,
    5984,
    6379,
    6443,
    7474,
    7687,
    8000,
    8080,
    8081,
    8086,
    8088,
    8443,
    8500,
    8880,
    9000,
    9042,
    9090,
    9092,
    9200,
    9300,
    10000,
    10250,
    11211,
    15672,
    27017,
)
OSV_ECOSYSTEMS = {
    "django": "PyPI",
    "flask": "PyPI",
    "jinja2": "PyPI",
    "requests": "PyPI",
    "jquery": "npm",
    "react": "npm",
    "next.js": "npm",
    "express": "npm",
    "lodash": "npm",
    "rails": "RubyGems",
    "spring": "Maven",
    "laravel": "Packagist",
}
MAX_OUTPUT = 2_000_000


def entity_id(kind: str, value: str) -> str:
    return f"{kind}:{value.casefold()}"


def normalized_url(value: str) -> str:
    return value if "://" in value else f"https://{value}"


def service_value(host: str, port: int) -> str:
    return f"[{host}]:{port}" if ":" in host and not host.startswith("[") else f"{host}:{port}"


def find_executable(*names: str) -> str:
    for name in names:
        env_name = re.sub(r"[^A-Z0-9]", "_", name.upper())
        configured = os.getenv(f"LAITOXX_{env_name}_PATH", "").strip()
        suffixes = (".exe", ".bat", ".cmd", "") if os.name == "nt" else ("",)
        local_roots = (
            Path(sys.executable).parent,
            Path.cwd() / "venv" / ("Scripts" if os.name == "nt" else "bin"),
        )
        if configured and Path(configured).is_file():
            return configured
        for root in local_roots:
            for suffix in suffixes:
                candidate = root / f"{name}{suffix}"
                if candidate.is_file():
                    return str(candidate)
        candidate = shutil.which(name)
        if candidate:
            return candidate
    return ""


def run_process(
    name: str,
    args: list[str],
    timeout: int,
) -> tuple[subprocess.CompletedProcess[str] | None, ProviderResult | None]:
    if not args or not args[0]:
        return None, ProviderResult(
            name,
            "skipped",
            error=f"{name} is not installed or is not available in PATH",
        )
    started = time.perf_counter()
    try:
        result = run_external_tool(
            name,
            args,
            shell=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(5, timeout),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None, ProviderResult(
            name,
            "unavailable",
            error=f"Stopped after the configured {timeout}s time budget",
            duration_ms=round((time.perf_counter() - started) * 1000),
        )
    except (OSError, ExternalToolError) as exc:
        return None, ProviderResult(name, "unavailable", error=str(exc))
    result.stdout = (result.stdout or "")[:MAX_OUTPUT]
    result.stderr = (result.stderr or "")[:20_000]
    if result.returncode not in {0, 1}:
        message = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else f"exit code {result.returncode}"
        return None, ProviderResult(
            name,
            "error",
            error=message,
            duration_ms=round((time.perf_counter() - started) * 1000),
        )
    return result, None


def json_lines(text: str) -> list[dict]:
    records = []
    for line in text.splitlines():
        try:
            item = json.loads(line)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(item, dict):
            records.append(item)
    return records


def technology_metadata(value: str) -> dict[str, str]:
    pattern = r"^(.+?)[\s:/]+v?(\d+(?:\.\d+){0,5}(?:[-+._][a-z0-9.-]+)?)$"
    match = re.match(pattern, value.strip(), re.I)
    product = match.group(1).strip() if match else value.strip()
    version = match.group(2).strip() if match else ""
    ecosystem = OSV_ECOSYSTEMS.get(product.casefold(), "")
    return {
        "source": "httpx Fingerprinting",
        "product": product,
        "version": version,
        "ecosystem": ecosystem,
    }
