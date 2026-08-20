"""
_patterns.py - Compiled pattern constants for UsernameChecker.

Extracted from checker.py to keep the main module focused on logic only.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# False-Positive Indicators - strings that indicate a profile does NOT exist
# ---------------------------------------------------------------------------
from ._negative_phrases_extended import EXTENDED_NEGATIVE_PHRASES
from ._negative_phrases_primary import PRIMARY_NEGATIVE_PHRASES

FALSE_POSITIVE_PHRASES: list[str] = [
    *PRIMARY_NEGATIVE_PHRASES,
    *EXTENDED_NEGATIVE_PHRASES,
]

# ---------------------------------------------------------------------------
# Title keywords - indicate a 404/error page
# ---------------------------------------------------------------------------
HARD_TITLE_404: tuple[str, ...] = (
    "404",
    "not found",
    "page not found",
    "не найден",
    "nicht gefunden",
    "introuvable",
    "bulunamadı",
    "不存在",
    "ошибка 404",
)

SOFT_TITLE_BAD: tuple[str, ...] = (
    "error",
    "login",
    "signin",
    "signup",
    "search",
    "ошибка",
    "войти",
    "авторизация",
    "регистрация",
)

# ---------------------------------------------------------------------------
# WAF / bot-protection markers - separate status: waf_blocked
# ---------------------------------------------------------------------------
WAF_MARKERS: tuple[str, ...] = (
    # Cloudflare
    "cloudflare",
    "cf-ray",
    "attention required",
    "enable javascript and cookies",
    "checking your browser",
    "just a moment",
    "ddos protection by cloudflare",
    # hCaptcha / reCAPTCHA
    "hcaptcha",
    "recaptcha",
    "please verify you are a human",
    "verify you are human",
    "i'm not a robot",
    "i am not a robot",
    # Imperva / Incapsula
    "incapsula",
    "imperva",
    "request unsuccessful",
    # Generic bot checks
    "security check",
    "bot check",
    "please complete the security check",
    "access denied",
    "403 forbidden",
    "you have been blocked",
    "your ip has been blocked",
    "suspicious activity",
)

# ---------------------------------------------------------------------------
# Login-wall markers - status: login_required
# ---------------------------------------------------------------------------
LOGIN_WALL_MARKERS: tuple[str, ...] = (
    # English
    "sign in to view",
    "log in to view",
    "login to view",
    "sign in to see",
    "log in to see",
    "you must be logged in",
    "please log in",
    "please sign in",
    "create an account to view",
    "register to view",
    "members only",
    "sign up to see",
    "join to view",
    "login required",
    "authentication required",
    # Russian
    "войдите чтобы просмотреть",
    "войдите, чтобы посмотреть",
    "войти для просмотра",
    "необходима авторизация",
    "зарегистрируйтесь чтобы просмотреть",
    "только для участников",
    "авторизуйтесь для просмотра",
    "требуется вход",
)

# ---------------------------------------------------------------------------
# JS / Meta redirect patterns
# ---------------------------------------------------------------------------
JS_REDIRECT_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r'<meta[^>]+http-equiv=["\']refresh["\']', re.IGNORECASE),
    re.compile(r'window\.location\s*(?:\.href\s*)?=\s*["\']', re.IGNORECASE),
    re.compile(r"window\.location\.replace\s*\(", re.IGNORECASE),
    re.compile(r"window\.location\.assign\s*\(", re.IGNORECASE),
    re.compile(r'document\.location\s*(?:\.href\s*)?=\s*["\']', re.IGNORECASE),
)

# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

MIN_PROFILE_BODY_SIZE = 3_000
