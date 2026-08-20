# Advanced Web Scanner

Multi-source enrichment for an IP, domain, URL, ASN or CVE. Passive analysis is
the default. An explicit per-scan confirmation can enable bounded local active
validation for a target the user owns or is authorized to test. Local scanners
are disabled automatically while proxy protection is active, preventing them
from bypassing the application-wide network route.

## Profiles

- Minimum: DNS-over-HTTPS/system DNS, RDAP, IPinfo Lite, RIPEstat, Shodan
  InternetDB, AlienVault OTX, AbuseIPDB, crt.sh, NVD, CISA KEV, EPSS, OSV and
  public GitHub Security Advisories.
- Maximum: minimum plus Shodan free-account capability/quota information, VirusTotal, urlscan.io, Wayback CDX,
  Common Crawl, HackerTarget, GreyNoise Community, Cert Spotter and local TLS extraction.

## Correlation and evidence lifecycle

DNS address and CNAME answers are compared through independent Cloudflare and
Google DoH resolvers. Transport failures fall through to the next resolver;
NXDOMAIN and NODATA remain valid observations. The DNS posture stage also
collects SPF, DMARC, MTA-STS, TLS-RPT and CAA, detects wildcard DNS and emits
conservative dangling-CNAME candidates. A candidate is never presented as a
confirmed subdomain takeover.

The scope classifier recognizes shared Cloudflare, Akamai, Fastly, Imperva,
CloudFront, Azure Front Door and Google Cloud CDN edges using ASN and CNAME
evidence. Generic AWS, Azure and Google Cloud ASNs are labelled cloud-hosted
but are not suppressed on ASN evidence alone. Shared edges stay visible in the
report while reverse-IP, service and vulnerability expansion is suppressed.

Every relation carries `observed_at`, `checked_at`, `expires_at`, an evidence
state (`historical`, `candidate`, `live`, `confirmed`, `rejected`) and its
supporting sources. Independent sources produce a separate corroborated claim.
Risk scoring gives full weight only to live/confirmed exposure; InternetDB and
other indexed services remain candidates until current validation succeeds.

Technology names are normalized into stable vendor/product identities with a
generic purl. Conflicting observed versions are retained and marked ambiguous
instead of silently selecting one. NVD, OSV, GitHub Advisories and VulnCheck
remain complementary parallel sources, followed by KEV and EPSS context.

Cert Spotter and crt.sh issuances become first-class certificate fingerprint
pivots. A local TLS handshake marks the certificate currently deployed.
Authoritative RDAP fallback is selected through IANA bootstrap registries, and
RIPEstat adds bounded routing history plus RPKI origin validation. Archive URLs
are analyzed locally for APIs, scripts, source maps, administration paths,
cloud storage and parameter names without fetching the discovered resources.

Optional active validation integrates local Naabu, httpx, Nuclei and WPScan.
Missing executables are reported as `skipped`, not as a failed passive scan.
Naabu uses an unprivileged CONNECT scan over a bounded high-value port list;
httpx discovers HTTP/TLS metadata and technologies; the detected stack selects
WPScan, records favicon/JARM correlation fingerprints, while Nuclei adds
validation evidence. Fingerprint matches remain supporting signals and never
prove common ownership. Default limits are 5 HTTP
requests/second, 25 port connections/second, eight HTTP targets and 90 seconds
per local tool. Intrusive, fuzz, brute-force, default-login, DoS and headless
Nuclei templates are excluded.

Version-bearing technologies are matched with a bounded four-product stage:
NVD keyword candidates, GitHub's `affects=package@version`, ecosystem-aware OSV
queries and (when configured) VulnCheck's vulnerable-CPE search. Each provider
can contribute at most 12 candidate CVEs, preventing broad product names from
exploding the graph. These relations remain `probable`; they are not presented
as proof that the deployed instance is exploitable.

IP and CVE pivots are bounded by `ScanOptions`. Hostnames observed by passive
sources are checked against current DNS and labelled either
`current_resolves_to` or `historical_or_observed`. InternetDB CVEs remain
weak signals until product/version applicability is independently confirmed.
Vulnerability confidence is stored as `possible`, `probable`, `confirmed` or
`rejected`. Version matching can produce `probable`; active validation evidence
is required for `confirmed`.

The relationship view uses a layered investigation layout. Vulnerability nodes
are always retained when the display is capped and merge NVD descriptions,
CVSS, CISA KEV status, EPSS probability and OSV context into one explanation.
Selecting a node opens its evidence panel. The same descriptions and relation
evidence are preserved when the report is opened in Graph Editor.

Graph canvas, node, confidence-edge, panel, field and button colours use the
normal application theme contract. They can be changed in Theme Editor under
the Relationship graph group.

Repeated port/service nodes are collapsed per IP by default so large CDN and
reverse-proxy results remain readable. The UI toggle restores every service
node without changing the underlying report or JSON export.

## API setup and quotas

The first scan opens a mandatory setup audit. The minimum chain cannot be
disabled and requires free IPinfo Lite and AbuseIPDB credentials. Optional
providers can be enabled separately. OTX, NVD and urlscan.io support automatic
anonymous/key mode selection. Credentials are persisted in application
settings and can still be overridden through environment variables:

`IPINFO_TOKEN`, `OTX_API_KEY`, `ABUSEIPDB_API_KEY`, `NVD_API_KEY`,
`SHODAN_API_KEY`, `VIRUSTOTAL_API_KEY`, `URLSCAN_API_KEY`,
`GREYNOISE_API_KEY`, `GITHUB_TOKEN`, `VULNCHECK_API_TOKEN` and
`WPSCAN_API_TOKEN`, `CERTSPOTTER_API_TOKEN`. Local executable locations can be overridden with
`LAITOXX_<TOOL>_PATH`. Using only the selected Python interpreter and its
standard library, the project installers download pinned standalone Naabu,
httpx and Nuclei archives for the current OS/architecture, validate the
release-published SHA-256 and place the binaries in the virtual environment.
Go, Ruby, winget and system package managers are not used for these scanners.
WPScan has no official standalone binary and is therefore only detected when
the user has installed it separately; its absence does not disable the other
active or passive stages.

GitHub Advisories supports anonymous access (60 requests/hour) and authenticated
access (normally 5000 requests/hour). VulnCheck Community requires a token and
uses its public `nist-nvd2` and `vulncheck-kev` indexes; the scanner never
silently switches to the paid `vulncheck-nvd2` index. WPScan works locally
without a token, but vulnerability database results require one; the free API
tier is catalogued as 25 requests/day. Local httpx and Nuclei have no SaaS
request quota.

All HTTP traffic uses the application-wide network manager. Responses are kept
in the local TTL OSINT cache to reduce quotas and tolerate repeated analysis.
Only cache misses consume the local quota ledger. Request timestamps, response
status, cooldowns, server-reported remaining quota and reset times are stored in
the application cache directory. HTTP 429/Retry-After and
rate-limit headers override the catalog defaults. Shodan host enrichment keeps
the keyless InternetDB endpoint as its baseline. With an optional account key,
the scanner also runs exact target filters through `/shodan/host/count` and
collects available port, product, network and vulnerability facets without
spending query credits. If `/api-info` reports query credits, one compact first
page from `/shodan/host/search` is added and debited locally. Membership-only
`/shodan/host/{ip}` lookups and on-demand scans are never scheduled.

The account key's `/shodan/host/search/filters` response is cached and treated
as the capability contract. Automatic queries are selected from the current
evidence: `net`/`hostname` for exact assets, `domain` and
`ssl.cert.subject.cn` for domain identity, `has_vuln` for scoped vulnerability
records, and exact certificate, CPE, favicon, HTTP hash, JARM/JA3S, HASSH,
analytics or cloud fingerprints when those values were actually observed.
Restricted `tag`/`vuln` filters are not assumed to work on a free key. Broad
geographic/product fields remain facets of a scoped query instead of becoming
global pivots. Collision-prone hashes are labelled as correlation evidence and
never promoted to proof of shared ownership.

LeakIX enrichment queries `/search` independently with `scope=service` and
`scope=leak`. Both scopes have separate cache entries, share the documented
one-request-per-second pacer, and can return a partial result if one scope is
temporarily unavailable. Service banners become historical service and
technology evidence; leak events become findings and CVE signals. Raw banners
and leaked credential values are not written to reports.

Provider outcomes distinguish hard API errors from expected operational
states: `rate_limited`, `no_data` and `unavailable`. IPv6 RDAP paths preserve
literal colons, InternetDB IPv6 misses are reported as no-data, and OTX pivot
lookups are serialized to avoid a burst after the first 429 response.
