# Third-party licenses

Laitoxx is not affiliated with the projects below. Components retain their original licenses.

## Scanner and fingerprint assets

| Component | Usage | License | Full text |
|---|---|---|---|
| Masscan 1.3.2 | Downloaded from the official source release and built locally | AGPL-3.0 | `licenses/external/masscan-AGPL-3.0.txt` |
| FingerprintHub rules | Packaged fingerprint subset | MIT | `licenses/external/fingerprinthub-MIT.txt` |
| Nuclei Templates rules | Packaged fingerprint subset | MIT | `licenses/external/nuclei-templates-MIT.txt` |
| Rapid7 Recog rules | Packaged fingerprint subset | BSD-2-Clause | `licenses/external/recog-BSD-2-Clause.txt` |
| Nerva rules | Packaged fingerprint subset | Apache-2.0 | `licenses/external/nerva-Apache-2.0.txt` |
| JA3 lists | Packaged fingerprint subset | BSD-3-Clause | `licenses/external/ja3-BSD-3-Clause.txt` |
| HASSH metadata | Packaged fingerprint subset | BSD-3-Clause | `licenses/external/hassh-BSD-3-Clause.txt` |

The packaged database intentionally excludes Nmap service probes, WhatWeb, Leetha, p0f and Wappalyzer-derived rows. Those sources have copyleft or NPSL terms which cannot be applied to the whole project without an explicit project-license decision.

## Declared Python dependencies

| Package | Installed version | License metadata | Upstream |
|---|---:|---|---|
| aiohttp | 3.10.11 | Apache 2 | https://matrix.to/#/#aio-libs:matrix.org |
| aiohttp-socks | 0.9.1 | Apache-2.0 | https://github.com/romis2012/aiohttp-socks |
| beautifulsoup4 | 4.12.3 | MIT License | https://www.crummy.com/software/BeautifulSoup/bs4/download/ |
| binwalk | 2.1.0 | See bundled upstream license text | https://github.com/devttys0/binwalk |
| colorama | 0.4.6 | BSD License | https://github.com/tartley/colorama |
| dnspython | 2.8.0 | ISC | https://www.dnspython.org |
| duckdb | 1.5.4 | MIT License | https://duckdb.org/docs/stable/clients/python/overview |
| hachoir | 3.3.0 | GNU GPL v2 | https://github.com/vstinner/hachoir |
| hashid | 3.1.4 | GNU GPL | https://github.com/psypanda/hashID |
| kreuzberg | 4.9.9 | Elastic-2.0 | https://kreuzberg.dev/CHANGELOG/ |
| lupa | 2.6 | MIT style | https://github.com/scoder/lupa |
| mutagen | 1.47.0 | GPL-2.0-or-later | https://github.com/quodlibet/mutagen |
| networkx | 3.4.2 | BSD License | https://networkx.org/ |
| olefile | 0.47 | BSD | https://www.decalage.info/python/olefileio |
| oletools | 0.60.2 | BSD | https://github.com/decalage2/oletools |
| paketlib | 0.1.16 | MIT License |  |
| pefile | 2023.2.7 | MIT | https://github.com/erocarrera/pefile |
| pillow | 12.1.1 | MIT-CMU | https://github.com/python-pillow/Pillow/releases |
| pdfid | 1.1.3 | MIT License | https://github.com/mlodic/pdfid |
| pyexiv2 | 2.15.5 | GPLv3 | https://github.com/LeoHsiao1/pyexiv2 |
| pymongo | 4.13.2 | Apache Software License | https://www.mongodb.org |
| PyQt6 | 6.10.0 | GPL-3.0-only | https://www.riverbankcomputing.com/software/pyqt/ |
| PyQt6-WebEngine | 6.10.0 | GPL-3.0-only | https://www.riverbankcomputing.com/software/pyqtwebengine/ |
| PySocks | 1.7.1 | BSD | https://github.com/Anorov/PySocks |
| python-magic | 0.4.27 | MIT | http://github.com/ahupp/python-magic |
| requests | 2.32.5 | Apache-2.0 | https://requests.readthedocs.io |
| truststore | 0.10.4 | MIT | https://truststore.readthedocs.io |
| tinytag | 2.2.1 | MIT License | https://github.com/tinytag/tinytag |
| xattr | not installed | inspect on installation | |
| osmnx | 2.1.0 | MIT | https://osmnx.readthedocs.io |
| protobuf | 7.34.0 | 3-Clause BSD License | https://developers.google.com/protocol-buffers/ |
| httpx | 0.28.1 | BSD-3-Clause | https://github.com/encode/httpx/blob/master/CHANGELOG.md |
| numpy | 2.3.5 | BSD License | https://numpy.org |
| opencv-python-headless | not installed | inspect on installation | |
| cryptography | 49.0.0 | Apache-2.0 OR BSD-3-Clause | https://cryptography.io/en/latest/changelog/ |
| pycryptodomex | 3.23.0 | BSD, Public Domain | https://github.com/Legrandin/pycryptodome/ |

This inventory reports the environment used to build this repository snapshot. Wheel and system-package distributions may add their own notices; retain those notices when redistributing them.
