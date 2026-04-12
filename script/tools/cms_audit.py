import re
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

from ..shared_utils import Color


_SENSITIVE_PATHS = [
    ".git/HEAD",
    ".git/config",
    ".env",
    ".htaccess",
    "phpinfo.php",
    "info.php",
    "wp-config.php.bak",
    "wp-config.php~",
    "config.php.bak",
    "database.yml",
    "Gemfile",
    "composer.json",
    "package.json",
    ".DS_Store",
    "backup.sql",
    "dump.sql",
    "db.sql",
    "admin/config.php",
    "config/database.php",
    "config/secrets.yml",
]


def cms_audit(data=None):
    """
    Passive CMS and security audit — GET requests only, no payloads.
    Detects CMS versions, reads robots.txt / security.txt / sitemap.xml,
    checks for exposed sensitive files.

    GUI  → cms_audit({"url": "https://example.com"})
    CLI  → cms_audit()
    """
    if data:
        url = data.get("url", "").strip()
    else:
        url = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
            f" Enter target URL for CMS audit: {Color.RESET}"
        ).strip()

    if not url:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No URL provided.")
        return

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE}"
          f" CMS Audit: {Color.WHITE}{base_url}\n")

    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (OSINT CMS Auditor)"

    print(f"{Color.DARK_RED}┌─[ {Color.LIGHT_RED}CMS Version Detection"
          f" {Color.DARK_RED}]" + "─" * 17)

    any_cms = False
    any_cms |= _detect_wordpress(session, base_url)
    any_cms |= _detect_joomla(session, base_url)
    any_cms |= _detect_drupal(session, base_url)

    if not any_cms:
        print(f"{Color.DARK_GRAY}  - {Color.WHITE}No common CMS detected via version probes")

    print(f"\n{Color.DARK_RED}├─[ {Color.LIGHT_RED}robots.txt"
          f" {Color.DARK_RED}]" + "─" * 28)
    _fetch_text(session, urljoin(base_url, "/robots.txt"), max_lines=40)

    print(f"\n{Color.DARK_RED}├─[ {Color.LIGHT_RED}security.txt"
          f" {Color.DARK_RED}]" + "─" * 26)
    found = _fetch_text(session, urljoin(base_url, "/.well-known/security.txt"), max_lines=30)
    if not found:
        _fetch_text(session, urljoin(base_url, "/security.txt"), max_lines=30)

    print(f"\n{Color.DARK_RED}├─[ {Color.LIGHT_RED}sitemap.xml"
          f" {Color.DARK_RED}]" + "─" * 27)
    _fetch_sitemap(session, base_url)

    print(f"\n{Color.DARK_RED}├─[ {Color.LIGHT_RED}Exposed Sensitive Files"
          f" {Color.DARK_RED}]" + "─" * 15)
    exposed = []
    total = len(_SENSITIVE_PATHS)
    for i, path in enumerate(_SENSITIVE_PATHS):
        print(f"\r{Color.DARK_GRAY}  Checking {i + 1}/{total}...", end="", flush=True)
        target = base_url.rstrip("/") + "/" + path
        try:
            r = session.get(target, timeout=8, allow_redirects=False)
            if r.status_code == 200 and r.text.strip():
                exposed.append((path, len(r.text)))
        except requests.exceptions.RequestException:
            pass
    print()

    if exposed:
        for path, size in exposed:
            target = base_url.rstrip("/") + "/" + path
            print(f"{Color.DARK_GRAY}  [{Color.RED}!{Color.DARK_GRAY}]"
                  f"{Color.RED} EXPOSED: {Color.WHITE}{target}"
                  f" {Color.DARK_GRAY}({size} bytes)")
        print(f"\n{Color.DARK_GRAY}[{Color.RED}!{Color.DARK_GRAY}]{Color.RED}"
              f" {len(exposed)} exposed file(s) found.")
    else:
        print(f"{Color.DARK_GRAY}  [{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN}"
              f" No sensitive files exposed from the common list.")

    print(f"\n{Color.DARK_RED}└" + "─" * 45)
    print(f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN}"
          f" CMS audit complete.")


def _get(session, url: str, timeout: int = 10):
    """Return response if status 200, else None."""
    try:
        r = session.get(url, timeout=timeout, allow_redirects=True)
        return r if r.status_code == 200 and r.text.strip() else None
    except requests.exceptions.RequestException:
        return None


def _detect_wordpress(session, base_url: str) -> bool:
    version = None

    r = _get(session, base_url.rstrip("/") + "/readme.html")
    if r:
        m = re.search(r"Version\s+([\d.]+)", r.text, re.IGNORECASE)
        if m:
            version = m.group(1)

    if not version:
        r = _get(session, base_url)
        if r:
            m = re.search(
                r'<meta[^>]+name=["\']generator["\'][^>]*content=["\']WordPress\s*([\d.]*)',
                r.text, re.IGNORECASE
            )
            if m:
                version = m.group(1) or "unknown"

    if not version:
        r = _get(session, base_url)
        if r:
            m = re.search(r'wp-emoji-release\.min\.js\?ver=([\d.]+)', r.text)
            if m:
                version = m.group(1)

    if version:
        print(f"{Color.DARK_GRAY}  [{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]"
              f"{Color.LIGHT_GREEN} WordPress {Color.WHITE}v{version}")
        return True

    r = _get(session, base_url)
    if r and re.search(r"/wp-content/|/wp-includes/|wp-json", r.text, re.IGNORECASE):
        print(f"{Color.DARK_GRAY}  [{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]"
              f"{Color.LIGHT_GREEN} WordPress detected {Color.DARK_GRAY}(version unknown)")
        return True
    return False


def _detect_joomla(session, base_url: str) -> bool:
    r = _get(session, base_url.rstrip("/") + "/administrator/manifests/files/joomla.xml")
    if r:
        m = re.search(r"<version>([\d.]+)</version>", r.text)
        version = m.group(1) if m else "unknown"
        print(f"{Color.DARK_GRAY}  [{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]"
              f"{Color.LIGHT_GREEN} Joomla {Color.WHITE}v{version}")
        return True
    return False


def _detect_drupal(session, base_url: str) -> bool:
    version = None

    r = _get(session, base_url.rstrip("/") + "/CHANGELOG.txt")
    if r:
        m = re.search(r"Drupal\s+([\d.]+)", r.text)
        if m:
            version = m.group(1)

    if not version:
        r = _get(session, base_url)
        if r:
            m = re.search(
                r'<meta[^>]+name=["\']Generator["\'][^>]*content=["\']Drupal\s*([\d.]*)',
                r.text, re.IGNORECASE
            )
            if m:
                version = m.group(1) or "unknown"


    if version:
        print(f"{Color.DARK_GRAY}  [{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]"
              f"{Color.LIGHT_GREEN} Drupal {Color.WHITE}v{version}")
        return True
    return False


def _fetch_text(session, url: str, max_lines: int = 30) -> bool:
    r = _get(session, url)
    if not r:
        print(f"{Color.DARK_GRAY}  - {Color.DARK_GRAY}Not found: {url}")
        return False
    lines = [ln for ln in r.text.strip().splitlines() if ln.strip()]
    print(f"{Color.DARK_GRAY}  [{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]"
          f"{Color.LIGHT_GREEN} Found: {Color.WHITE}{url}")
    for line in lines[:max_lines]:
        print(f"{Color.DARK_GRAY}    {Color.WHITE}{line}")
    if len(lines) > max_lines:
        print(f"{Color.DARK_GRAY}    {Color.DARK_GRAY}... ({len(lines) - max_lines} more lines)")
    return True


def _fetch_sitemap(session, base_url: str):
    r = _get(session, base_url.rstrip("/") + "/sitemap.xml")
    if not r:
        print(f"{Color.DARK_GRAY}  - {Color.DARK_GRAY}sitemap.xml not found.")
        return
    try:
        soup = BeautifulSoup(r.text, "html.parser")
        locs = [tag.get_text(strip=True) for tag in soup.find_all("loc")]
    except Exception:
        print(f"{Color.DARK_GRAY}  [{Color.RED}✖{Color.DARK_GRAY}]{Color.RED}"
              f" Could not parse sitemap.xml")
        return
    if not locs:
        print(f"{Color.DARK_GRAY}  - {Color.DARK_GRAY}sitemap.xml is empty or unsupported format.")
        return
    print(f"{Color.DARK_GRAY}  [{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN}"
          f" {len(locs)} URL(s) found. Showing first 20:")
    for loc in locs[:20]:
        print(f"{Color.DARK_GRAY}    {Color.WHITE}{loc}")
    if len(locs) > 20:
        print(f"{Color.DARK_GRAY}    {Color.DARK_GRAY}... ({len(locs) - 20} more)")
