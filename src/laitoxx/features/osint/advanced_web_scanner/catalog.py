from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QuotaWindow:
    limit: int
    seconds: int
    label: str
    fixed_utc: bool = False
    indicative: bool = False


@dataclass(frozen=True)
class ProviderSpec:
    id: str
    name: str
    mandatory: bool = True
    key_name: str = ""
    key_required: bool = False
    supports_anonymous: bool = True
    quotas: dict[str, tuple[QuotaWindow, ...]] | None = None


def _q(limit: int, seconds: int, label: str, *, fixed=False, indicative=False):
    return QuotaWindow(limit, seconds, label, fixed, indicative)


PROVIDERS: tuple[ProviderSpec, ...] = (
    ProviderSpec("dns", "Cloudflare DNS-over-HTTPS"),
    ProviderSpec("rdap", "RDAP.org", quotas={"anonymous": (_q(10, 10, "10 / 10 sec"),)}),
    ProviderSpec("ipinfo", "IPinfo Lite", key_name="IPINFO_TOKEN", key_required=True, supports_anonymous=False),
    ProviderSpec("ripestat", "RIPEstat"),
    ProviderSpec("internetdb", "Shodan InternetDB"),
    ProviderSpec(
        "otx",
        "AlienVault OTX",
        key_name="OTX_API_KEY",
        quotas={
            "anonymous": (_q(1000, 3600, "~1000 / hour", indicative=True),),
            "key": (_q(10000, 3600, "~10000 / hour", indicative=True),),
        },
    ),
    ProviderSpec("crtsh", "crt.sh"),
    ProviderSpec(
        "abuseipdb",
        "AbuseIPDB",
        key_name="ABUSEIPDB_API_KEY",
        key_required=True,
        supports_anonymous=False,
        quotas={"key": (_q(1000, 86400, "1000 / day", fixed=True),)},
    ),
    ProviderSpec(
        "nvd",
        "NVD",
        key_name="NVD_API_KEY",
        quotas={
            "anonymous": (_q(5, 30, "5 / 30 sec"),),
            "key": (_q(50, 30, "50 / 30 sec"),),
        },
    ),
    ProviderSpec("osv", "OSV.dev"),
    ProviderSpec(
        "github_advisories",
        "GitHub Security Advisories",
        key_name="GITHUB_TOKEN",
        quotas={
            "anonymous": (_q(60, 3600, "60 / hour"),),
            "key": (_q(5000, 3600, "5000 / hour"),),
        },
    ),
    ProviderSpec("kev", "CISA KEV"),
    ProviderSpec("epss", "EPSS", quotas={"anonymous": (_q(1000, 60, "1000 / min"),)}),
    ProviderSpec(
        "vulncheck",
        "VulnCheck Community",
        mandatory=False,
        key_name="VULNCHECK_API_TOKEN",
        key_required=True,
        supports_anonymous=False,
        quotas={"key": (_q(1000, 60, "1000 / min"),)},
    ),
    ProviderSpec(
        "shodan_account",
        "Shodan Search & Facets",
        mandatory=False,
        key_name="SHODAN_API_KEY",
        key_required=True,
        supports_anonymous=False,
    ),
    ProviderSpec(
        "virustotal",
        "VirusTotal Public API",
        mandatory=False,
        key_name="VIRUSTOTAL_API_KEY",
        key_required=True,
        supports_anonymous=False,
        quotas={"key": (_q(4, 60, "4 / min"), _q(500, 86400, "500 / day", fixed=True))},
    ),
    ProviderSpec(
        "urlscan",
        "urlscan.io",
        mandatory=False,
        key_name="URLSCAN_API_KEY",
        quotas={
            "anonymous": (_q(30, 60, "30 / min"), _q(100, 3600, "100 / hour"), _q(500, 86400, "500 / day", fixed=True)),
            "key": (_q(30, 60, "30 / min"), _q(100, 3600, "100 / hour"), _q(1000, 86400, "1000 / day", fixed=True)),
        },
    ),
    ProviderSpec("wayback", "Wayback Machine CDX", mandatory=False),
    ProviderSpec("commoncrawl", "Common Crawl Index", mandatory=False),
    ProviderSpec(
        "hackertarget",
        "HackerTarget Reverse IP",
        mandatory=False,
        key_name="HACKERTARGET_API_KEY",
        quotas={
            # The dedicated Reverse IP endpoint has a stricter free allowance
            # than HackerTarget's general API page: 20 calls/day, 50 results.
            "anonymous": (_q(2, 1, "2 / sec"), _q(20, 86400, "20 / day", fixed=True)),
            # Member allowance depends on the subscription and is learned from
            # x-api-* response headers; only the global rate is local.
            "key": (_q(2, 1, "2 / sec"),),
        },
    ),
    ProviderSpec(
        "greynoise",
        "GreyNoise Community",
        mandatory=False,
        key_name="GREYNOISE_API_KEY",
        quotas={"key": (_q(50, 604800, "50 / week"),)},
    ),
    ProviderSpec("tls", "Local TLS certificate", mandatory=False),
    ProviderSpec("naabu", "Naabu targeted port discovery (local)", mandatory=False),
    ProviderSpec("httpx", "httpx fingerprinting (local)", mandatory=False),
    ProviderSpec("nuclei", "Nuclei validation (local)", mandatory=False),
    ProviderSpec(
        "wpscan",
        "WPScan (local + vulnerability API)",
        mandatory=False,
        key_name="WPSCAN_API_TOKEN",
        quotas={"key": (_q(25, 86400, "25 / day", fixed=True, indicative=True),)},
    ),
    # New providers stay at the end of the settings list.  Their execution
    # priority is defined separately by the engine's fallback chain.
    ProviderSpec(
        "whoisjson",
        "WhoisJSON Reverse WHOIS",
        mandatory=False,
        key_name="WHOISJSON_API_KEY",
        key_required=True,
        supports_anonymous=False,
        # The monthly balance is supplied by Remaining-Requests.  WhoisJSON
        # does not publish its reset timestamp, so only the exact minute limit
        # is enforced locally.
        quotas={"key": (_q(20, 60, "20 / min"),)},
    ),
    ProviderSpec(
        "botoi",
        "Botoi Reverse DNS (PTR)",
        mandatory=False,
        key_name="BOTOI_API_KEY",
        quotas={
            "anonymous": (
                _q(5, 60, "5 / min"),
                _q(100, 86400, "100 / day", fixed=True, indicative=True),
            ),
            "key": (_q(10, 60, "10 / min"), _q(1000, 86400, "1000 / day", fixed=True)),
        },
    ),
    ProviderSpec(
        "leakix",
        "LeakIX exposure intelligence",
        mandatory=False,
        key_name="LEAKIX_API_KEY",
        key_required=True,
        supports_anonymous=False,
        quotas={
            "key": (
                _q(1, 1, "~1 / sec"),
                # Community quota supplied by the plan/settings page. Public API
                # docs do not expose a balance or exact billing reset timestamp.
                _q(3000, 30 * 86400, "3000 / 30 days", indicative=True),
            )
        },
    ),
    ProviderSpec(
        "certspotter",
        "Cert Spotter CT Search",
        mandatory=False,
        key_name="CERTSPOTTER_API_TOKEN",
        quotas={
            "key": (
                _q(5, 1, "5 / sec"),
                _q(75, 60, "75 / min"),
                _q(100, 3600, "100 hostname queries / hour"),
            ),
        },
    ),
)

BY_ID = {provider.id: provider for provider in PROVIDERS}
