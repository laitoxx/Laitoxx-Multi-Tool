from __future__ import annotations

import json
from urllib.parse import urlparse

from .local_runtime import (
    CVE_RE as _CVE_RE,
)
from .local_runtime import (
    HIGH_VALUE_PORTS as _HIGH_VALUE_PORTS,
)
from .local_runtime import (
    entity_id as _id,
)
from .local_runtime import (
    find_executable as _find,
)
from .local_runtime import (
    json_lines as _json_lines,
)
from .local_runtime import (
    normalized_url as _url,
)
from .local_runtime import (
    run_process as _run_process,
)
from .local_runtime import (
    service_value as _service_value,
)
from .local_runtime import (
    technology_metadata as _technology_metadata,
)
from .models import Entity, ProviderResult, Relation
from .quota import QuotaExceeded, ledger


def naabu_scan(target: str, *, rate_limit: int = 25, timeout: int = 60) -> ProviderResult:
    """Discover a bounded set of high-value TCP services on an authorized target."""
    name = "Naabu Port Discovery"
    executable = _find("naabu")
    host = urlparse(_url(target)).hostname or target
    result, failure = _run_process(
        name,
        [
            executable,
            "-host",
            host,
            "-p",
            ",".join(map(str, _HIGH_VALUE_PORTS)),
            "-json",
            "-silent",
            "-verify",
            "-exclude-cdn",
            "-no-stdin",
            "-duc",
            "-scan-type",
            "CONNECT",
            "-Pn",
            "-rate",
            str(max(1, min(rate_limit, 50))),
            "-retries",
            "1",
            "-timeout",
            "1000",
        ],
        timeout,
    )
    if failure:
        return failure
    from .domain.exposure import classify_service

    records = _json_lines(result.stdout)
    entities, relations = [], []
    for item in records:
        try:
            port = int(item.get("port"))
        except (TypeError, ValueError):
            continue
        ip = str(item.get("ip") or item.get("host") or host).strip()
        observed_host = str(item.get("host") or host).strip()
        if not ip:
            continue
        classification = classify_service(port)
        service = _service_value(ip, port)
        metadata = {
            "port": port,
            "protocol": "tcp",
            "host": observed_host,
            "ip": ip,
            "source": name,
            "actively_verified": True,
            **classification,
        }
        entities.extend(
            (
                Entity("ip", ip),
                Entity("service", service, label=f"{classification['service_name']} · {port}", metadata=metadata),
            )
        )
        relations.append(
            Relation(
                _id("ip", ip),
                _id("service", service),
                "exposes",
                name,
                "high",
                True,
                f"TCP/{port} accepted a verified connection",
            )
        )
        if observed_host and observed_host.casefold() != ip.casefold():
            entities.append(Entity("domain", observed_host))
            relations.append(
                Relation(_id("domain", observed_host), _id("ip", ip), "active_resolves_to", name, "high", True)
            )
    return ProviderResult(
        name,
        "ok" if records else "no_data",
        {"records": records[:200], "ports": list(_HIGH_VALUE_PORTS)},
        entities,
        relations,
    )


def httpx_fingerprint(target: str, *, rate_limit: int = 5, timeout: int = 60) -> ProviderResult:
    name = "httpx Fingerprinting"
    executable = _find("httpx")
    result, failure = _run_process(
        name,
        [
            executable,
            "-u",
            _url(target),
            "-json",
            "-silent",
            "-status-code",
            "-title",
            "-tech-detect",
            "-server",
            "-ip",
            "-cname",
            "-tls-grab",
            "-location",
            "-content-type",
            "-content-length",
            "-response-time",
            "-websocket",
            "-cdn",
            "-asn",
            "-favicon",
            "-jarm",
            "-no-color",
            "-rl",
            str(max(1, rate_limit)),
            "-t",
            "2",
            "-timeout",
            "8",
            "-retries",
            "0",
        ],
        timeout,
    )
    if failure:
        return failure
    records = _json_lines(result.stdout)
    entities, relations = [], []
    from .domain.exposure import classify_service

    for item in records:
        url = str(item.get("url") or item.get("input") or _url(target))
        url_id = _id("url", url)
        parsed = urlparse(url)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        title = str(item.get("title") or "")
        technologies = [str(value).strip() for value in item.get("tech", []) or [] if str(value).strip()]
        classification = classify_service(port, str(item.get("webserver") or ""), " ".join(technologies), title)
        entities.append(
            Entity(
                "url",
                url,
                metadata={
                    "status_code": item.get("status_code"),
                    "title": title,
                    "webserver": item.get("webserver", ""),
                    "content_type": item.get("content_type", ""),
                    "content_length": item.get("content_length"),
                    "location": item.get("location", ""),
                    "response_time": item.get("response_time", ""),
                    "cdn": item.get("cdn", False),
                    "websocket": item.get("websocket", False),
                    "source": name,
                },
            )
        )
        fingerprints = {
            "favicon": item.get("favicon") or item.get("favicon_hash") or item.get("favicon_mmh3"),
            "jarm": item.get("jarm"),
        }
        for fingerprint_type, fingerprint in fingerprints.items():
            fingerprint = str(fingerprint or "").strip()
            if not fingerprint:
                continue
            value = f"{fingerprint_type}:{fingerprint}"
            entities.append(
                Entity(
                    "web_fingerprint",
                    value,
                    label=fingerprint_type.upper(),
                    metadata={
                        "fingerprint_type": fingerprint_type,
                        "fingerprint": fingerprint,
                        "source": name,
                        "collision_prone": fingerprint_type == "favicon",
                        "explanation": (
                            "A reusable HTTP/TLS fingerprint for correlation. Matching values are supporting evidence only "
                            "and do not prove common ownership."
                        ),
                    },
                )
            )
            relations.append(
                Relation(
                    url_id,
                    _id("web_fingerprint", value),
                    "has_web_fingerprint",
                    name,
                    "medium",
                    True,
                    f"{fingerprint_type.upper()} fingerprint observed during active validation",
                )
            )
        for technology in technologies:
            entities.append(Entity("technology", technology, metadata=_technology_metadata(technology)))
            relations.append(Relation(url_id, _id("technology", technology), "uses_technology", name, "high", True))
        addresses = item.get("a") or []
        ip = str(
            item.get("host_ip") or item.get("ip") or (addresses[0] if isinstance(addresses, list) and addresses else "")
        ).strip()
        if ip:
            entities.append(Entity("ip", ip))
            relations.append(Relation(url_id, _id("ip", ip), "http_endpoint", name, "high", True))
            service = _service_value(ip, port)
            service_metadata = {
                "port": port,
                "protocol": parsed.scheme or "http",
                "host": parsed.hostname or "",
                "ip": ip,
                "url": url,
                "status_code": item.get("status_code"),
                "title": title,
                "technologies": technologies,
                "source": name,
                "actively_verified": True,
                **classification,
            }
            entities.append(
                Entity(
                    "service", service, label=f"{classification['service_name']} · {port}", metadata=service_metadata
                )
            )
            relations.append(
                Relation(
                    _id("ip", ip),
                    _id("service", service),
                    "exposes",
                    name,
                    "high",
                    True,
                    f"HTTP {item.get('status_code', '')} {title}".strip(),
                )
            )
            relations.append(Relation(url_id, _id("service", service), "identifies_service", name, "high", True))
        tls = item.get("tls") or {}
        subject = str(tls.get("subject_dn") or tls.get("subject_cn") or "").strip() if isinstance(tls, dict) else ""
        serial = str(tls.get("serial") or "").strip() if isinstance(tls, dict) else ""
        if subject or serial:
            certificate = serial or subject
            entities.append(
                Entity("certificate", certificate, label=subject or serial, metadata={"source": name, **tls})
            )
            relations.append(
                Relation(url_id, _id("certificate", certificate), "presents_certificate", name, "high", True)
            )
    return ProviderResult(name, "ok" if records else "no_data", {"records": records[:100]}, entities, relations)


def nuclei_scan(target: str, *, rate_limit: int = 5, timeout: int = 90) -> ProviderResult:
    name = "Nuclei"
    executable = _find("nuclei")
    result, failure = _run_process(
        name,
        [
            executable,
            "-u",
            _url(target),
            "-jsonl",
            "-silent",
            "-no-color",
            "-duc",
            "-severity",
            "info,low,medium,high,critical",
            "-rl",
            str(max(1, rate_limit)),
            "-c",
            "2",
            "-bs",
            "1",
            "-timeout",
            "8",
            "-retries",
            "0",
            "-tc",
            "severity != 'info' || contains(tags,'exposure') || contains(tags,'misconfig') || contains(tags,'panel') || contains(tags,'login') || contains(tags,'tech')",
            "-etags",
            "dos,fuzz,intrusive,headless,bruteforce,default-login,default-logins",
        ],
        timeout,
    )
    if failure:
        return failure
    records = _json_lines(result.stdout)
    entities, relations = [], []
    root = _id("url", _url(target))
    for item in records:
        info = item.get("info") or {}
        template_id = str(item.get("template-id") or item.get("templateID") or "nuclei-finding")
        title = str(info.get("name") or template_id)
        evidence = str(item.get("matched-at") or item.get("host") or _url(target))
        severity = str(info.get("severity") or "unknown").lower()
        tags = [str(tag).casefold() for tag in info.get("tags", []) or []]
        cves = sorted({match.upper() for match in _CVE_RE.findall(json.dumps(item))})
        if cves:
            for cve in cves:
                entities.append(
                    Entity(
                        "cve",
                        cve,
                        metadata={
                            "severity": severity,
                            "validation_sources": [name],
                            "scanner_evidence": evidence,
                            "template_id": template_id,
                        },
                    )
                )
                relations.append(
                    Relation(root, _id("cve", cve), "validated_vulnerability", name, "high", True, evidence)
                )
        else:
            finding = f"{template_id}@{evidence}"
            category = (
                "panel"
                if any(tag in {"panel", "login"} for tag in tags)
                else "exposure"
                if "exposure" in tags
                else "misconfiguration"
                if "misconfig" in tags
                else "technology"
                if "tech" in tags
                else "observation"
            )
            entities.append(
                Entity(
                    "finding",
                    finding,
                    label=title,
                    metadata={
                        "severity": severity,
                        "scanner": name,
                        "evidence": evidence,
                        "template_id": template_id,
                        "finding_type": category,
                        "tags": tags,
                    },
                )
            )
            relations.append(Relation(root, _id("finding", finding), "scanner_finding", name, "high", True, evidence))
    return ProviderResult(name, "ok" if records else "no_data", {"findings": records[:200]}, entities, relations)


def wpscan_scan(target: str, *, api_token: str = "", timeout: int = 90) -> ProviderResult:
    name = "WPScan"
    executable = _find("wpscan")
    if not executable:
        return ProviderResult(name, "skipped", error="WPScan is not installed or is not available in PATH")
    quota_event = None
    if api_token:
        try:
            # WPScan does not expose per-component API usage in stable JSON.
            # One reservation per scan is a conservative, explicitly labelled
            # local estimate; server/CLI exhaustion still wins when reported.
            quota_event = ledger.acquire("wpscan")
        except QuotaExceeded as exc:
            return ProviderResult(name, "rate_limited", error=str(exc))
    args = [
        executable,
        "--url",
        _url(target),
        "--format",
        "json",
        "--no-update",
        "--plugins-detection",
        "passive",
        "--themes-detection",
        "passive",
        "--detection-mode",
        "passive",
        "--request-timeout",
        "10",
        "--connect-timeout",
        "5",
    ]
    if api_token:
        args.extend(("--api-token", api_token))
    result, failure = _run_process(name, args, timeout)
    if failure:
        if api_token:
            failure.error = failure.error.replace(api_token, "***")
        if quota_event is not None:
            ledger.record_response(quota_event, "wpscan", 500, {})
        return failure
    if quota_event is not None:
        ledger.record_response(quota_event, "wpscan", 200, {})
    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return ProviderResult(name, "error", error="WPScan did not return valid JSON")
    entities, relations = [], []
    root = _id("url", _url(target))

    def add_component(component: str, version: str, vulnerabilities: list[dict]):
        value = f"{component} {version}".strip()
        metadata = _technology_metadata(value)
        metadata.update({"source": name, "product": component, "version": version})
        entities.append(Entity("technology", value, metadata=metadata))
        relations.append(Relation(root, _id("technology", value), "uses_technology", name, "high", True))
        for vuln in vulnerabilities or []:
            cves = sorted({match.upper() for match in _CVE_RE.findall(json.dumps(vuln))})
            for cve in cves:
                entities.append(
                    Entity(
                        "cve",
                        cve,
                        metadata={
                            "validation_sources": [name],
                            "matched_component": component,
                            "matched_version": version,
                            "title": vuln.get("title", ""),
                        },
                    )
                )
                relations.append(
                    Relation(root, _id("cve", cve), "version_matched_vulnerability", name, "medium", True, value)
                )

    version = data.get("version") or {}
    add_component("WordPress", str(version.get("number") or ""), version.get("vulnerabilities") or [])
    for family in ("plugins", "themes"):
        for slug, component in (data.get(family) or {}).items():
            component_version = str((component.get("version") or {}).get("number") or "")
            add_component(slug, component_version, component.get("vulnerabilities") or [])
    return ProviderResult(name, "ok", {"scan": data}, entities, relations)
