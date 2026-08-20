"""Unified email validation, mail-domain posture and public enrichment."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from laitoxx.core.dns import query_dns

from .data_search_identity import _email_search_flow
from .email_validator import is_valid_email


def _resolve(domain: str, record_type: str) -> list[str]:
    return query_dns(domain, record_type)


def inspect_mail_domain(domain: str) -> dict:
    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="email-dns") as executor:
        mx_job = executor.submit(_resolve, domain, "MX")
        txt_job = executor.submit(_resolve, domain, "TXT")
        dmarc_job = executor.submit(_resolve, f"_dmarc.{domain}", "TXT")
        mx, txt, dmarc = mx_job.result(), txt_job.result(), dmarc_job.result()
    spf = [value for value in txt if "v=spf1" in value.casefold()]
    dmarc_policies = []
    for value in dmarc:
        tags = {}
        for item in value.strip('"').split(";"):
            key, separator, raw = item.strip().partition("=")
            if separator:
                tags[key.casefold()] = raw.strip().casefold()
        dmarc_policies.append(tags)
    provider = ""
    joined = " ".join(mx).casefold()
    for marker, name in (
        ("google.com", "Google Workspace"),
        ("outlook.com", "Microsoft 365"),
        ("protection.outlook.com", "Microsoft 365"),
        ("yandex.net", "Yandex"),
        ("zoho.", "Zoho Mail"),
        ("protonmail.", "Proton Mail"),
    ):
        if marker in joined:
            provider = name
            break
    return {
        "domain": domain,
        "mx": mx,
        "accepts_mail": bool(mx),
        "provider": provider,
        "spf": spf,
        "dmarc": dmarc,
        "posture": {
            "spf_published": bool(spf),
            "dmarc_published": bool(dmarc),
            "dmarc_enforcing": any(tags.get("p") in {"quarantine", "reject"} for tags in dmarc_policies),
        },
    }


def normalize_email(value: str) -> str:
    email = (value or "").strip()
    if email and "@" not in email:
        email = f"{email}@gmail.com"
    if not is_valid_email(email):
        raise ValueError(f"Invalid email address: {email or '<empty>'}")
    local, domain = email.rsplit("@", 1)
    try:
        domain = domain.encode("idna").decode("ascii").casefold()
    except UnicodeError as error:
        raise ValueError("Invalid international email domain") from error
    return f"{local}@{domain}"


def email_osint(value: str | None = None) -> dict:
    email = normalize_email(value if value is not None else input())
    domain = email.rsplit("@", 1)[1]
    domain_profile = inspect_mail_domain(domain)
    print(f"Email OSINT: {email}")
    print("Syntax: valid")
    print("Mail domain profile:")
    print(json.dumps(domain_profile, ensure_ascii=False, indent=2))
    if not domain_profile["accepts_mail"]:
        print("Warning: the domain publishes no MX records; account existence was not inferred.")
    _email_search_flow(email, log=print)
    return {"email": email, "syntax_valid": True, "mail_domain": domain_profile}
