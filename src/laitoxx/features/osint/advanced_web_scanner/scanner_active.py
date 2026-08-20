from __future__ import annotations

from urllib.parse import urlparse

from laitoxx.core.settings.network_manager import NetworkManager

from . import (
    local_scanners,
)
from .configuration import credential
from .models import ProviderResult, ScanReport, Target


class ActiveValidationMixin:
    def _run_active_validation(self, report: ScanReport, target: Target):
        """Run explicitly enabled local scanners with conservative budgets."""
        local_names = {
            "naabu": "Naabu Port Discovery",
            "httpx": "httpx Fingerprinting",
            "nuclei": "Nuclei",
            "wpscan": "WPScan",
        }
        enabled = [provider_id for provider_id in local_names if self._enabled(provider_id)]
        if not enabled:
            return
        if NetworkManager.is_active():
            reason = "Local active scanners are disabled while proxy protection is active to prevent a direct-network IP leak"
            for provider_id in enabled:
                self._merge_local(report, ProviderResult(local_names[provider_id], "skipped", error=reason))
            return

        hosts = self._active_hosts(report, target)
        if "naabu" in enabled:
            for host in hosts:
                self._merge_local(
                    report,
                    local_scanners.naabu_scan(
                        host,
                        rate_limit=self.options.active_port_rate,
                        timeout=self.options.active_timeout,
                    ),
                )

        candidates = self._active_targets(report, target)
        if not candidates:
            self._merge_local(
                report,
                ProviderResult(
                    "Local Active Scanners",
                    "skipped",
                    error="Active web scanners require an IP, domain or URL target",
                ),
            )
            return
        fingerprints: dict[str, ProviderResult] = {}
        wordpress_detected = False
        if "httpx" in enabled:
            for candidate in candidates:
                result = local_scanners.httpx_fingerprint(
                    candidate,
                    rate_limit=self.options.active_rate_limit,
                    timeout=self.options.active_timeout,
                )
                fingerprints[candidate] = result
                self._merge_local(report, result)

        for candidate in candidates:
            if "nuclei" in enabled:
                self._merge_local(
                    report,
                    local_scanners.nuclei_scan(
                        candidate,
                        rate_limit=self.options.active_rate_limit,
                        timeout=self.options.active_timeout,
                    ),
                )
            if "wpscan" in enabled and self._is_wordpress(fingerprints.get(candidate)):
                wordpress_detected = True
                self._merge_local(
                    report,
                    local_scanners.wpscan_scan(
                        candidate,
                        api_token=credential("wpscan", self.options.provider_config),
                        timeout=self.options.active_timeout,
                    ),
                )

        if "wpscan" in enabled and not wordpress_detected:
            self._merge_local(
                report,
                ProviderResult(
                    "WPScan",
                    "skipped",
                    error="WordPress was not identified by httpx technology fingerprinting",
                ),
            )

    def _merge_local(self, report: ScanReport, result: ProviderResult):
        self._merge(report, result)
        if self.progress:
            self.progress(result.name, result)

    def _active_targets(self, report: ScanReport, target: Target) -> list[str]:
        if target.kind == "url":
            root = target.value
            root_domain = urlparse(target.value).hostname or ""
        elif target.kind == "domain":
            root = f"https://{target.value}"
            root_domain = target.value
        elif target.kind == "ip":
            root = f"https://{target.value}"
            root_domain = ""
        else:
            return []
        domains = sorted(
            {
                entity.value
                for entity in report.entities
                if entity.kind == "domain"
                and root_domain
                and (
                    entity.value.casefold() == root_domain.casefold()
                    or entity.value.casefold().endswith("." + root_domain.casefold())
                )
            }
        )
        candidates = [root]
        endpoints = set()
        for entity in report.entities:
            if entity.kind != "service" or entity.metadata.get("category") not in {
                "web",
                "admin_panel",
                "monitoring",
                "devops",
            }:
                continue
            if not str(entity.metadata.get("port", "")).isdigit():
                continue
            port = int(entity.metadata["port"])
            endpoint_host = str(entity.metadata.get("host") or entity.metadata.get("ip") or "").strip()
            if not endpoint_host:
                endpoint_host = entity.value.rsplit(":", 1)[0].strip("[]")
            if endpoint_host:
                endpoints.add((endpoint_host, port))
        high_interest = {"admin_panel": 0, "monitoring": 1, "devops": 2, "web": 3}
        endpoint_categories = {
            (
                str(
                    entity.metadata.get("host")
                    or entity.metadata.get("ip")
                    or entity.value.rsplit(":", 1)[0].strip("[]")
                ),
                int(entity.metadata["port"]),
            ): high_interest.get(str(entity.metadata.get("category")), 9)
            for entity in report.entities
            if entity.kind == "service" and str(entity.metadata.get("port", "")).isdigit()
        }
        for endpoint_host, port in sorted(
            endpoints, key=lambda item: (endpoint_categories.get(item, 9), item[0], item[1])
        ):
            scheme = "https" if port in {443, 8443, 9443} else "http"
            suffix = "" if port in {80, 443} else f":{port}"
            display_host = (
                f"[{endpoint_host}]" if ":" in endpoint_host and not endpoint_host.startswith("[") else endpoint_host
            )
            candidates.append(f"{scheme}://{display_host}{suffix}")
        if root_domain and target.kind != "url":
            candidates.append(f"http://{root_domain}")
        candidates.extend(f"https://{domain}" for domain in domains if domain.casefold() != root_domain.casefold())
        return list(dict.fromkeys(candidates))[: max(1, self.options.active_max_targets)]

    def _active_hosts(self, report: ScanReport, target: Target) -> list[str]:
        """Return a small, in-scope host set for authorized port discovery."""
        if target.kind == "url":
            root = urlparse(target.value).hostname or ""
        elif target.kind in {"domain", "ip"}:
            root = target.value
        else:
            return []
        hosts = [root] if root else []
        if target.kind != "ip" and root:
            hosts.extend(
                sorted(
                    entity.value
                    for entity in report.entities
                    if entity.kind == "domain" and entity.value.casefold().endswith("." + root.casefold())
                )
            )
        return list(dict.fromkeys(hosts))[: min(4, max(1, self.options.active_max_targets))]

    @staticmethod
    def _is_wordpress(result: ProviderResult | None) -> bool:
        if not result:
            return False
        return any(
            "wordpress" in str(technology).casefold()
            for record in result.data.get("records", [])
            for technology in record.get("tech", []) or []
        )
