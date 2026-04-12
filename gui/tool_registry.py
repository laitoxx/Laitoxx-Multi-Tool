from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from script.tools.user_search_by_phone import search_by_number
from script.tools.ip_info import get_ip
from script.tools.email_validator import check_email_address
from script.tools.website_info import get_website_info
from script.tools.port_scanner import port_scanner_tool
from script.tools.gmail_osint import gmail_osint
from script.tools.db_searcher import search_database
from script.tools.mac_lookup import search_mac_address
from script.tools.subdomain_finder import find_subdomains
from script.tools.google_osint import google_osint
from script.tools.telegram_search import telegram_search
from script.tools.user_checker import check_username
from script.tools.username_osint import username_osint_tool
from script.tools.web_crawler import web_crawler
from script.tools.http_inspector import http_inspector
from script.tools.tech_detector import tech_detector
from script.tools.cms_audit import cms_audit
from script.tools.hash_tools.text_hasher import text_hasher_tool
from script.tools.hash_tools.hash_identifier import hash_identifier_tool
from script.tools.hash_tools.rainbow_table_generator import rainbow_table_tool
from script.tools.nmap_scanner.nmap_scanner import nmap_scanner_tool
from script.tools.jwt_analyzer import jwt_analyzer_tool
from script.tools.web_security_tools import web_security_tools
from script.tools.text_transformer import text_transformer_tool
from script.tools.password_generator import password_generator_tool
from script.tools.regex_tester import regex_tester_tool
from script.tools.cidr_calculator import cidr_calculator_tool
from script.tools.image_search import image_search_tool


@dataclass(frozen=True)
class ToolSpec:
    func: Callable
    input_type: Optional[str]
    prompt: Optional[str]
    desc: str
    threaded: bool
    disabled: bool = False


TOOL_REGISTRY: Dict[str, ToolSpec] = {
    "Check Phone Number": ToolSpec(
        func=search_by_number,
        input_type="text",
        prompt="Enter phone number (+ or without):",
        desc="Get information about a phone number.",
        threaded=True,
    ),
    "Check IP": ToolSpec(
        func=get_ip,
        input_type="text",
        prompt="Enter IP address:",
        desc="Get geolocation data for an IP address.",
        threaded=True,
    ),
    "Validate Email": ToolSpec(
        func=check_email_address,
        input_type="text",
        prompt="Enter email address:",
        desc="Validate email format (syntax only).",
        threaded=True,
    ),
    "Info Website": ToolSpec(
        func=get_website_info,
        input_type="text",
        prompt="Enter website URL:",
        desc="Gather information about a website (Whois, etc.).",
        threaded=True,
    ),
    "Gmail Osint": ToolSpec(
        func=gmail_osint,
        input_type="text",
        prompt="Enter Gmail address or prefix:",
        desc="Find information associated with a Gmail account.",
        threaded=True,
    ),
    "Database search": ToolSpec(
        func=search_database,
        input_type="text",
        prompt="Enter search query (e.g., email, name):",
        desc="Search for leaks in local databases.",
        threaded=True,
    ),
    "Check MAC-address": ToolSpec(
        func=search_mac_address,
        input_type="text",
        prompt="Enter MAC address:",
        desc="Lookup the vendor of a MAC address.",
        threaded=True,
    ),
    "Subdomain finder": ToolSpec(
        func=find_subdomains,
        input_type="text",
        prompt="Enter domain (e.g., example.com):",
        desc="Find subdomains for a given domain.",
        threaded=True,
    ),
    "Google Osint": ToolSpec(
        func=google_osint,
        input_type="google_osint",
        prompt=None,
        desc="Build advanced Google dorks with multiple operators.",
        threaded=False,
    ),
    "Search Nick": ToolSpec(
        func=username_osint_tool,
        input_type="username_osint_dialog",
        prompt=None,
        desc="Advanced Username OSINT: 500+ sites, nickname generation, graph integration.",
        threaded=False,
    ),
    "Web-crawler": ToolSpec(
        func=web_crawler,
        input_type="text",
        prompt="Enter starting URL:",
        desc="Crawl a website to discover links and pages.",
        threaded=True,
    ),
    "Port Scanner": ToolSpec(
        func=port_scanner_tool,
        input_type="text",
        prompt="Enter target IP or domain:",
        desc="Scan a target for open ports.",
        threaded=True,
    ),
    "HTTP Inspector": ToolSpec(
        func=http_inspector,
        input_type="text",
        prompt="Enter URL to inspect:",
        desc="Status, all headers, redirect chain, TLS cert, cookies.",
        threaded=True,
    ),
    "Tech Detector": ToolSpec(
        func=tech_detector,
        input_type="text",
        prompt="Enter URL to fingerprint:",
        desc="Fingerprint server, CDN, CMS, JS frameworks, WAF, security headers.",
        threaded=True,
    ),
    "CMS Audit": ToolSpec(
        func=cms_audit,
        input_type="text",
        prompt="Enter target URL for CMS audit:",
        desc="Passive CMS audit: version, robots.txt, security.txt, sitemap, exposed files.",
        threaded=True,
    ),
    "Telegram (paketlib)": ToolSpec(
        func=telegram_search,
        input_type="telegram",
        prompt=None,
        desc="Search for users, channels, chats, or Telegram ID on Telegram.",
        threaded=True,
    ),
    "Text Hasher": ToolSpec(
        func=text_hasher_tool,
        input_type="hash",
        prompt=None,
        desc="Hash text using various algorithms (MD5, SHA256, etc.).",
        threaded=True,
    ),
    "Hash Identifier": ToolSpec(
        func=hash_identifier_tool,
        input_type="hash",
        prompt=None,
        desc="Identify the type of a given hash.",
        threaded=True,
    ),
    "Rainbow Table Gen": ToolSpec(
        func=rainbow_table_tool,
        input_type="hash",
        prompt=None,
        desc="Generate a rainbow table for a given charset and hash.",
        threaded=True,
    ),
    "Nmap": ToolSpec(
        func=nmap_scanner_tool,
        input_type=None,
        prompt=None,
        desc="Perform an Nmap scan with progress updates.",
        threaded=True,
    ),
    "JWT Analyzer": ToolSpec(
        func=jwt_analyzer_tool,
        input_type="jwt",
        prompt=None,
        desc="Decode & inspect JWT tokens, or brute-force HMAC secret (HS256/384/512).",
        threaded=True,
    ),
    "Web Security Tools": ToolSpec(
        func=web_security_tools,
        input_type="web_security",
        prompt=None,
        desc="SSL/TLS, CORS, Open Redirect, and Security Headers checks.",
        threaded=True,
    ),
    "Text Transformer": ToolSpec(
        func=text_transformer_tool,
        input_type="text_transformer",
        prompt=None,
        desc="Encode/decode text: Leet, Morse, Binary, Hex, ROT-13, Caesar, Base64, URL...",
        threaded=False,
    ),
    "Password Generator": ToolSpec(
        func=password_generator_tool,
        input_type="password_gen",
        prompt=None,
        desc="Generate secure passwords with custom charset, include/exclude rules.",
        threaded=False,
    ),
    "Regex Tester": ToolSpec(
        func=regex_tester_tool,
        input_type="regex",
        prompt=None,
        desc="Test a regex pattern against text - shows all matches, groups, line:col.",
        threaded=False,
    ),
    "CIDR Calculator": ToolSpec(
        func=cidr_calculator_tool,
        input_type="cidr",
        prompt=None,
        desc="IPv4/IPv6 network info, IP membership check, subnet splitting.",
        threaded=False,
    ),
    "Image Search": ToolSpec(
        func=image_search_tool,
        input_type="image_search",
        prompt=None,
        desc="Обратный поиск изображений + криминалистический анализ: ELA, EXIF, хэши, редактор.",
        threaded=False,
    ),
}

CATEGORIES: Dict[str, List[str]] = {
    "information_gathering": [
        "Check Phone Number",
        "Check IP",
        "Validate Email",
        "Info Website",
        "Gmail Osint",
        "Database search",
        "Check MAC-address",
        "Subdomain finder",
        "Google Osint",
        "Telegram (paketlib)",
        "Search Nick",
        "Web-crawler",
        "Image Search",
    ],
    "web_security": [
        "Port Scanner",
        "Nmap",
        "HTTP Inspector",
        "Tech Detector",
        "CMS Audit",
        "JWT Analyzer",
        "Web Security Tools",
    ],
    "utils": [
        "Text Hasher",
        "Hash Identifier",
        "Rainbow Table Gen",
        "Text Transformer",
        "Password Generator",
        "Regex Tester",
        "CIDR Calculator",
    ],
}
