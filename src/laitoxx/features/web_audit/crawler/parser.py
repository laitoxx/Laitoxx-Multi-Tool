"""Bounded HTML extraction for crawler responses."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .models import CrawlForm

_EMAIL_RE = re.compile(r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}\b", re.I)
_SECURITY_HEADERS = (
    "strict-transport-security",
    "content-security-policy",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
    "cross-origin-opener-policy",
)


def detect_technologies(headers: dict[str, str], body: str) -> list[str]:
    """Return conservative technology hints from public response markers."""

    lower = body[:200000].casefold()
    values = " ".join(headers.values()).casefold()
    detected: set[str] = set()
    markers = (
        ("WordPress", ("wp-content/", "wp-includes/")),
        ("Drupal", ("drupal-settings-json", "sites/default/files")),
        ("Joomla", ("/media/system/js/", 'content="joomla')),
        ("React", ("data-reactroot", "__next_data__")),
        ("Vue", ("data-v-", "__nuxt__")),
        ("Cloudflare", ("cf-ray", "cloudflare")),
    )
    for name, needles in markers:
        if any(needle in lower or needle in values for needle in needles):
            detected.add(name)
    server = headers.get("server", "").strip()
    powered = headers.get("x-powered-by", "").strip()
    if server:
        detected.add(server)
    if powered:
        detected.add(powered)
    return sorted(detected)


def parse_html(body: str, page_url: str, headers: dict[str, str]) -> dict:
    """Extract links, metadata, forms and public contact indicators."""

    soup = BeautifulSoup(body, "html.parser")
    title = soup.title.get_text(" ", strip=True)[:300] if soup.title else ""
    description_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    description = str(description_tag.get("content", ""))[:500] if description_tag else ""
    canonical_tag = soup.find("link", attrs={"rel": lambda value: value and "canonical" in value})
    canonical = urljoin(page_url, canonical_tag.get("href", "")) if canonical_tag else ""
    links: set[str] = set()
    assets: set[str] = set()
    phones: set[str] = set()
    for tag in soup.find_all("a", href=True):
        href = str(tag.get("href", "")).strip()
        if href.casefold().startswith("tel:"):
            phones.add(href[4:].strip())
        else:
            links.add(urljoin(page_url, href))
    for tag, attribute in (("script", "src"), ("img", "src"), ("link", "href"), ("source", "src")):
        for item in soup.find_all(tag):
            value = str(item.get(attribute, "")).strip()
            if value:
                assets.add(urljoin(page_url, value))
    forms: list[CrawlForm] = []
    for form in soup.find_all("form"):
        fields = []
        for field in form.find_all(("input", "select", "textarea")):
            fields.append(
                {
                    "name": str(field.get("name", "")),
                    "type": str(field.get("type", field.name)),
                }
            )
        forms.append(
            CrawlForm(
                action=urljoin(page_url, str(form.get("action", "")) or page_url),
                method=str(form.get("method", "GET")).upper(),
                fields=fields,
            )
        )
    normalized_headers = {key.casefold(): value for key, value in headers.items()}
    return {
        "title": title,
        "description": description,
        "canonical_url": canonical,
        "raw_links": sorted(links),
        "assets": sorted(assets),
        "forms": forms,
        "emails": sorted(set(_EMAIL_RE.findall(body))),
        "phones": sorted(phones),
        "technologies": detect_technologies(normalized_headers, body),
        "security_headers": {
            name: normalized_headers[name] for name in _SECURITY_HEADERS if name in normalized_headers
        },
        "missing_security_headers": [name for name in _SECURITY_HEADERS if name not in normalized_headers],
    }
