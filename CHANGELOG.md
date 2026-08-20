# Changelog

This file records user-visible changes to Laitoxx Multi-Tool. The
`3.0.0-rc.1` notes compare the local release candidate with the public GitHub
`main` baseline at commit `b9fa44993dd67da8194cf532016cbf68409c4819`
(2026-07-14), whose README identifies the published line as 2.3.2.

## [Unreleased]

No changes recorded yet.

## [3.0.0-rc.1] - 2026-08-20

This is the first release candidate for the 3.0 series. It is a major internal
and user-facing revision; treat it as a pre-release and back up important 2.x
runtime data before upgrading.

### Added

- Added **Advanced Web Scanner**, a multi-source investigation workflow for IP
  addresses, domains, URLs, ASNs, and CVEs. It correlates DNS, RDAP,
  certificates, routing, exposure, reputation, archives, technologies, and
  vulnerabilities into evidence-aware reports, timelines, and graphs.
- Added passive integrations for sources including Cloudflare/Google DoH,
  IPinfo, RIPEstat, Shodan InternetDB, AlienVault OTX, AbuseIPDB, crt.sh, NVD,
  CISA KEV, EPSS, OSV, GitHub Advisories, Wayback, Common Crawl, LeakIX,
  HackerTarget, GreyNoise, Cert Spotter, VirusTotal, urlscan.io, and optional
  VulnCheck data. Availability depends on target type, provider state, and
  configured credentials.
- Added explicitly authorized, bounded local validation through Naabu, httpx,
  Nuclei, and an existing WPScan installation. Intrusive, fuzzing,
  brute-force, default-login, DoS, and headless Nuclei templates are excluded.
- Added **TONgue** investigations that connect Telegram identities, TON
  addresses, collectible Gifts, NFTs, ownership history, and public movements,
  with evidence persistence and graph/report exports.
- Added a dedicated **Masscan Scanner** workspace using Masscan 1.3.2, local
  banner probing, structured observations, and redistributable service
  fingerprints.
- Added **CogniPass** as a locally built targeted password generator, including
  a dedicated GUI and pinned Zig toolchain/source workflow.
- Added a structured **Web Crawler** with bounded scope, forms and endpoint
  discovery, report export, cancellation, and graph projection.
- Added **Domain Intelligence** for DNS, RDAP registration, HTTP, TLS,
  certificate, and integrated subdomain evidence.
- Added **IOC Extractor** for IP addresses, domains, URLs, email addresses,
  phone numbers, hashes, JWTs, and usernames.
- Added a full **Steganography** workspace with encode/extract/inspect flows,
  capacity checks, multiple image strategies, checksummed payload containers,
  and authenticated/encrypted payload support.
- Added **Text Cipher**, providing 86 local encodings, ciphers, text
  transformations, number/date/color conversions, hashes, and symbol codecs.
- Added reusable execution controls, structured report export, graph schemas,
  relationship suggestions, and additional native graph layouts.
- Added a command palette, modular task/input controllers, dedicated windows
  for new investigation workflows, and runtime audits for core, GUI, workers,
  providers, Web OSINT, TONgue, text transforms, and steganography.
- Added bundled immutable resources, a generated third-party notices index, and
  provenance-preserving fingerprint datasets.

### Changed

- Reorganized the application around a feature-oriented `src` architecture:
  `app` assembles the program, `core` owns shared infrastructure, `features`
  owns domain logic, `interfaces.gui` owns presentation, and `shared` owns
  reusable execution/report/graph primitives.
- Converted the tool registry to declarative import paths with lazy handler
  resolution. Optional feature imports no longer need to succeed during GUI
  startup.
- Split large GUI classes into focused views, controllers, contexts, widgets,
  and feature services. Long-running business logic now returns structured
  reports instead of being owned by Qt threads.
- Reworked Username OSINT with a 500+ site catalog, quick/standard/full modes,
  provider validation and health history, inference, nickname generation,
  avatar handling, digital-portrait output, and graph integration.
- Reworked Image Search and forensic image analysis into modular services and
  UI components.
- Reworked the graph editor with native node/edge rendering, layout tools,
  styling, selection, imports, properties, analysis actions, and undoable
  commands.
- Reworked Lua plugins around discovery, typed plugin metadata, restricted
  execution, configuration dialogs, syntax tooling, and explicit host APIs for
  graph, username, and application services.
- Moved writable settings, cache, reports, graphs, logs, themes, and tool data
  out of the repository into the platform application-data directory. Added
  `LAITOXX_DATA_DIR` as an override.
- Moved translations to JSON resource catalogs and expanded translation
  coverage for the modular GUI.
- Centralized HTTP, TLS trust, proxy, DNS, and socket policy. SOCKS-protected
  sessions now block accidental direct DNS/TCP access from compatible Python
  paths.
- Updated startup to require the project virtual environment, preserve the
  `src` import path, tolerate ZIP snapshots without Git metadata, and apply Git
  updates only through fast-forward pulls.
- Replaced the previous Text Transformer entry with the broader Text Cipher
  workspace.
- Replaced standalone legacy subdomain discovery with verified subdomain
  evidence inside Domain Intelligence.

### Installer and dependency changes

- Constrained supported Python versions to 3.10-3.13. Python 3.14 is rejected
  with an explicit compatibility explanation.
- Updated Linux/macOS and Windows installers to create `venv`, install all
  declared Python requirements, and fail with a non-zero status when a required
  component group cannot be installed.
- Added pinned, SHA-256-verified standalone installers for Nuclei 3.11.0,
  httpx 1.10.0, and Naabu 2.6.1. Go, winget, and a system package manager are
  not required for these binaries.
- Added a pinned CogniPass build from commit
  `1062c39102a8868e2a48a7496047eb24497d67bd` using `ziglang==0.13.0.post1`,
  including archive verification and a Git fallback.
- Added a verified Masscan 1.3.2 source build with explicit checks for `make`
  and a C compiler, safe extraction, bounded build parallelism, and actionable
  platform-specific error messages.
- Kept WPScan optional because its official CLI has no standalone binary and
  requires Ruby/native dependencies. Existing installations are detected from
  `PATH`.
- Removed unused or replaced dependencies from the mandatory set, including
  the Python Nmap wrapper, Selenium, Scapy, Torpy, Faker, fake-useragent,
  python-whois, and several legacy UI/data packages. Added cryptography,
  PyCryptodome, NumPy, OpenCV headless, and system trust-store integration for
  the new local analysis paths.
- Added dependency/license verification scripts and bundled third-party license
  texts for declared distributions and external fingerprint sources.

### Security, privacy, and evidence handling

- Active scanning is opt-in per scan and remains bounded by target, port,
  request, concurrency, and timeout controls.
- Local scanners are disabled while proxy protection is active rather than
  risking a route bypass.
- Added safe archive extraction, published checksum validation, pinned source
  revisions, atomic executable replacement, and post-install version probes.
- Added evidence timestamps, expiry, source attribution, confidence states, and
  partial-provider outcomes. Historical or indexed observations are not
  promoted to confirmed live exposure without current validation.
- Added shared-edge/CDN classification and bounded pivot expansion to reduce
  false ownership correlations and graph explosions.
- Redacted raw leaked credential values and raw service banners from persisted
  Advanced Web Scanner reports.
- Restricted Lua plugin globals; direct `io`, `os`, `debug`, `loadfile`, and
  `dofile` access is not exposed by the 3.0 sandbox.

### Fixed

- Installers no longer continue to a misleading “Installation complete” result
  after failed Python packages, CogniPass builds, scanner downloads, or Masscan
  builds.
- Masscan installation no longer imports GUI/settings modules as a side effect,
  so compiler checks can run before application data directories are writable.
- Missing build tools, compilers, unsupported platforms, failed checksums,
  permissions/security blocks, and failed version probes now retain distinct,
  actionable error messages.
- Long-running GUI work now uses shared cancellation, pause, progress, stream,
  and error contracts, reducing thread-lifecycle and stale-result failures.
- Provider failures and rate limits preserve valid partial evidence instead of
  discarding the whole investigation.

### Removed or replaced

- Removed the legacy Nmap-based scanner and simple port-scanner entries in favor
  of the Masscan workspace and structured service observations.
- Removed the standalone subdomain-finder entry in favor of Domain Intelligence
  discovery and verification.
- Removed repository-owned mutable settings and acceptance-marker files; these
  now live in the platform application-data directory.
- Removed unrestricted legacy Lua execution paths in favor of the restricted
  plugin host environment.

### Known release-candidate limitations

- Python 3.14 is not supported.
- Masscan requires a local build toolchain and normally needs elevated/raw-packet
  privileges at runtime. Windows additionally needs an Npcap-compatible driver.
- WPScan must be installed separately when WordPress-specific local validation
  is required.
- Online enrichment remains subject to provider credentials, quotas, target
  coverage, and availability. Reports deliberately preserve `no_data`,
  `rate_limited`, `unavailable`, and partial states.

## Previous releases

The public 2.x release notes remain available in the repository history. Git
tags include `2.3.2`, `2.3.1`, and earlier releases.

[Unreleased]: https://github.com/laitoxx/Laitoxx-Multi-Tool/compare/3.0.0-rc.1...HEAD
[3.0.0-rc.1]: https://github.com/laitoxx/Laitoxx-Multi-Tool/compare/2.3.2...3.0.0-rc.1
