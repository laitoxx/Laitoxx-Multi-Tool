import re
import requests
from bs4 import BeautifulSoup

from ..shared_utils import Color


USER_AGENT = "Mozilla/5.0 (OSINT TechDetector)"
REQUEST_TIMEOUT = 15

CDN_SIGNATURES = {
    "Cloudflare":     ["CF-Ray", "CF-Cache-Status", "cf-request-id"],
    "Akamai":         ["X-Check-Cacheable", "X-Akamai-Transformed", "Akamai-Cache-Status"],
    "Fastly":         ["X-Served-By", "Fastly-Debug-Digest"],
    "AWS CloudFront": ["X-Amz-Cf-Id", "X-Amz-Cf-Pop"],
    "Azure CDN":      ["X-Azure-Ref"],
    "BunnyCDN":       ["CDN-PullZone", "CDN-RequestId"],
    "Sucuri CDN":     ["X-Sucuri-Cache"],
}

WAF_SIGNATURES = {
    "Cloudflare WAF": lambda h, b: "cf-ray" in h,
    "Sucuri":         lambda h, b: "x-sucuri-id" in h,
    "ModSecurity":    lambda h, b: "mod_security" in b or "modsecurity" in b,
    "Incapsula":      lambda h, b: "x-iinfo" in h,
    "Imperva":        lambda h, b: "x-cdn" in h and "imperva" in b,
    "F5 BIG-IP":      lambda h, b: "bigipserver" in h,
    "Wordfence":      lambda h, b: "wordfence" in b,
}

CMS_PATTERNS = {
    "WordPress":  r"/wp-content/|/wp-includes/|wp-json",
    "Joomla":     r"/components/com_|/modules/mod_|Joomla!",
    "Drupal":     r"Drupal\.settings|/sites/default/files/",
    "Magento":    r"Mage\.Cookies|/skin/frontend/|/js/mage/",
    "PrestaShop": r"prestashop|/modules/blockcart/",
    "OpenCart":   r"opencart|/catalog/view/theme/",
    "TYPO3":      r"typo3|/typo3temp/",
    "Shopify":    r"Shopify\.theme|cdn\.shopify\.com",
    "Wix":        r"wixstatic\.com|wix\.com/lpviral",
    "Squarespace": r"squarespace\.com|static\.squarespace",
}

COOKIE_CMS = {
    "WordPress":  lambda c: any(n.startswith("wordpress_") or n == "wp-settings-time" for n in c),
    "Joomla":     lambda c: any("joomla" in n for n in c),
    "Drupal":     lambda c: any("drupal" in n for n in c),
    "Magento":    lambda c: "frontend" in c,
}

FW_PATTERNS = {
    "React":     r"react(?:\.min)?\.js|react-dom|data-reactroot|__REACT",
    "Vue.js":    r"vue(?:\.min)?\.js|vue\.runtime|__vue_",
    "Angular":   r"angular(?:\.min)?\.js|ng-version=|ng-app",
    "jQuery":    r"jquery(?:\.min)?\.js|jQuery\.fn\.jquery",
    "Bootstrap": r"bootstrap(?:\.min)?\.(?:js|css)",
    "Next.js":   r"_next/static|__NEXT_DATA__",
    "Nuxt.js":   r"_nuxt/|__nuxt",
    "Ember.js":  r"ember(?:\.min)?\.js|Ember\.Application",
    "Svelte":    r"__svelte|svelte-",
}

SEC_HEADERS = [
    ("Content-Security-Policy",   "CSP"),
    ("Strict-Transport-Security", "HSTS"),
    ("X-Frame-Options",           "X-Frame-Options"),
    ("X-Content-Type-Options",    "X-Content-Type-Options"),
    ("Referrer-Policy",           "Referrer-Policy"),
    ("Permissions-Policy",        "Permissions-Policy"),
    ("Cross-Origin-Opener-Policy","COOP"),
]


def _get_input_url(data) -> str:
    if data:
        return data.get("url", "").strip()
    return input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}"
        f" Enter URL to fingerprint: {Color.RESET}"
    ).strip()


def _normalize_url(url: str) -> str:
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url


def _fetch_response(url: str):
    try:
        return requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ), None
    except requests.exceptions.RequestException as exc:
        return None, exc


def tech_detector(data=None):
    """
    Passive technology fingerprinting: server, CDN, WAF, CMS,
    JS frameworks, security headers. No injection -- GET only.

    GUI  -> tech_detector({"url": "https://example.com"})
    CLI  -> tech_detector()
    """
    url = _get_input_url(data)
    if not url:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No URL provided.")
        return

    url = _normalize_url(url)

    print()
    print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Fingerprinting: {Color.WHITE}{url}")
    print()

    response, error = _fetch_response(url)
    if error:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Connection error: {error}")
        return

    headers = response.headers
    html = response.text
    headers_lower = {k.lower() for k in headers}
    html_lower = html.lower()

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        soup = None

    print(f"{Color.DARK_RED}┌─[ {Color.LIGHT_RED}Server & Framework {Color.DARK_RED}]" + "─" * 20)
    _hdr("Server",       headers.get("Server"))
    _hdr("X-Powered-By", headers.get("X-Powered-By"))
    _hdr("X-Generator",  headers.get("X-Generator"))
    _hdr("X-AspNet-Ver", headers.get("X-AspNet-Version"))

    print()
    print(f"{Color.DARK_RED}├─[ {Color.LIGHT_RED}CDN {Color.DARK_RED}]" + "─" * 35)
    detected_cdns = []
    for name, sigs in CDN_SIGNATURES.items():
        if any(s.lower() in headers_lower for s in sigs):
            detected_cdns.append(name)
            print(f"{Color.DARK_GRAY}  [{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} {name}")
    if not detected_cdns:
        print(f"{Color.DARK_GRAY}  - {Color.WHITE}No known CDN detected")

    print()
    print(f"{Color.DARK_RED}├─[ {Color.LIGHT_RED}WAF {Color.DARK_RED}]" + "─" * 35)
    detected_wafs = []
    for name, checker in WAF_SIGNATURES.items():
        try:
            if checker(headers_lower, html_lower):
                detected_wafs.append(name)
                print(f"{Color.DARK_GRAY}  [{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} {name}")
        except Exception:
            pass
    if not detected_wafs:
        print(f"{Color.DARK_GRAY}  - {Color.WHITE}No known WAF detected")

    print()
    print(f"{Color.DARK_RED}├─[ {Color.LIGHT_RED}CMS {Color.DARK_RED}]" + "─" * 35)
    cms_found = []

    if soup:
        meta_gen = soup.find("meta", attrs={"name": re.compile("generator", re.I)})
        if meta_gen and meta_gen.get("content"):
            val = meta_gen["content"]
            print(f"{Color.DARK_GRAY}  - {Color.LIGHT_RED}Meta generator: {Color.WHITE}{val}")
            cms_found.append(val)

    for cms_name, pattern in CMS_PATTERNS.items():
        if re.search(pattern, html, re.IGNORECASE) and cms_name not in cms_found:
            cms_found.append(cms_name)
            print(f"{Color.DARK_GRAY}  [{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} {cms_name} (HTML markers)")

    cookie_names = [c.name.lower() for c in response.cookies]
    for cms_name, checker in COOKIE_CMS.items():
        if checker(cookie_names) and cms_name not in cms_found:
            cms_found.append(cms_name)
            print(f"{Color.DARK_GRAY}  [{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} {cms_name} (cookie evidence)")

    if not cms_found:
        print(f"{Color.DARK_GRAY}  - {Color.WHITE}No CMS fingerprint detected")

    print()
    print(f"{Color.DARK_RED}├─[ {Color.LIGHT_RED}Frontend Frameworks {Color.DARK_RED}]" + "─" * 19)
    found_fws = []
    for fw_name, pattern in FW_PATTERNS.items():
        if re.search(pattern, html, re.IGNORECASE):
            found_fws.append(fw_name)
            print(f"{Color.DARK_GRAY}  [{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} {fw_name}")
    if not found_fws:
        print(f"{Color.DARK_GRAY}  - {Color.WHITE}No common JS frameworks detected")

    print()
    print(f"{Color.DARK_RED}├─[ {Color.LIGHT_RED}Security Headers {Color.DARK_RED}]" + "─" * 22)
    for header_name, label in SEC_HEADERS:
        val = headers.get(header_name)
        if val:
            display = val if len(val) < 70 else val[:67] + "..."
            print(f"{Color.DARK_GRAY}  [{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} {label:<28}{Color.WHITE}{display}")
        else:
            print(f"{Color.DARK_GRAY}  [{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} {label:<28}{Color.DARK_GRAY}missing")

    print()
    print(f"{Color.DARK_RED}└" + "─" * 45)
    print(f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Fingerprinting complete.")

def _hdr(label: str, value):
    if value:
        print(f"{Color.DARK_GRAY}  - {Color.LIGHT_RED}{label:<16}{Color.WHITE}{value}")
    else:
        print(f"{Color.DARK_GRAY}  - {Color.DARK_GRAY}{label:<16}not present")
