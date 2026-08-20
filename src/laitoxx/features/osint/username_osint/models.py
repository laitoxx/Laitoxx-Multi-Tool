"""Data models for the Username OSINT engine."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TokenActivation:
    """Dynamic token activation configuration."""

    method: str = ""  # Service identifier such as spotify or twitter.
    marks: list[str] = field(default_factory=list)  # Strings that indicate token expiration.
    url: str = ""  # Endpoint used to fetch a fresh token.
    src: str = ""  # Field name in the token response.
    dst: str = ""  # Header field that receives the token.

    @classmethod
    def from_dict(cls, d: dict) -> TokenActivation:
        if not d:
            return cls()
        return cls(
            method=d.get("method", ""),
            marks=d.get("marks", []),
            url=d.get("url", ""),
            src=d.get("src", ""),
            dst=d.get("dst", ""),
        )


@dataclass
class SiteEntry:
    """A single site definition from sites_db.json."""

    name: str
    url_template: str
    category: str
    check_type: str = "status_code"  # Supported values: status_code, message, redirect and json_api.
    valid_status: list[int] = field(default_factory=lambda: [200])
    invalid_indicators: list[str] = field(default_factory=list)
    avatar_url: str | None = None
    tags: list[str] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    request_method: str = "GET"
    timeout: int = 10
    follow_redirects: bool = True
    redirect_detection: bool = False
    # Provider specific account detection fields.
    presense_strs: list[str] = field(default_factory=list)  # Strings that prove account presence.
    absence_strs: list[str] = field(default_factory=list)  # Strings that prove account absence.
    url_probe: str | None = None  # Optional API or probe endpoint.
    regex_check: str | None = None  # Optional username format expression.
    engine: str | None = None  # Optional CMS or provider engine identifier.
    url_main: str | None = None  # Main site URL used for display.
    disabled: bool = False  # Disabled entries are not requested.
    activation: TokenActivation | None = None  # Dynamic token refresh configuration.
    errors: dict[str, str] = field(default_factory=dict)  # Provider error explanations.
    confidence_threshold: float = 0.0  # Minimum confidence accepted for a positive verdict.

    @classmethod
    def from_dict(cls, name: str, d: dict) -> SiteEntry:
        activation_data = d.get("activation")
        return cls(
            name=name,
            url_template=d.get("url", ""),
            category=d.get("category", "other"),
            check_type=d.get("check_type", d.get("checkType", "status_code")),
            valid_status=d.get("valid_status", [200]),
            invalid_indicators=d.get("invalid_indicators", []),
            avatar_url=d.get("avatar_url"),
            tags=d.get("tags", []),
            headers=d.get("headers", {}),
            request_method=d.get("request_method", "GET"),
            timeout=d.get("timeout", 10),
            follow_redirects=d.get("follow_redirects", True),
            redirect_detection=d.get("redirect_detection", False),
            presense_strs=d.get("presense_strs", d.get("presenseStrs", [])),
            absence_strs=d.get("absence_strs", d.get("absenceStrs", [])),
            url_probe=d.get("url_probe", d.get("urlProbe")),
            regex_check=d.get("regex_check", d.get("regexCheck")),
            engine=d.get("engine"),
            url_main=d.get("url_main", d.get("urlMain")),
            disabled=d.get("disabled", False),
            activation=TokenActivation.from_dict(activation_data) if activation_data else None,
            errors=d.get("errors", {}),
            confidence_threshold=d.get("confidence_threshold", 0.0),
        )


@dataclass
class CheckResult:
    """Result of checking a single site for a username."""

    site_name: str
    url: str
    status: str = "not_found"
    http_code: int | None = None
    response_time_ms: float = 0.0
    avatar_url: str | None = None
    category: str = "other"
    error_message: str | None = None
    confidence: float = 0.0
    retry_count: int = 0
    waf_detected: bool = False
    profile_url: str | None = None
    engine: str | None = None
    evidence: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    @property
    def is_found(self) -> bool:
        return self.status in {"confirmed", "probable"}

    @property
    def confidence_pct(self) -> int:
        return int(self.confidence * 100)


# Canonical site categories.
SITE_CATEGORIES = [
    "social",
    "development",
    "gaming",
    "dating",
    "professional",
    "music",
    "video",
    "forums",
    "blogging",
    "crypto",
    "shopping",
    "adult",
    "media",
    "art",
    "education",
    "finance",
    "government",
    "messaging",
    "other",
]

CATEGORY_ICONS = {
    "social": "\U0001f465",
    "development": "\U0001f4bb",
    "gaming": "\U0001f3ae",
    "dating": "\u2764\ufe0f",
    "professional": "\U0001f454",
    "music": "\U0001f3b5",
    "video": "\U0001f3ac",
    "forums": "\U0001f4ac",
    "blogging": "\u270d\ufe0f",
    "crypto": "\U0001fa99",
    "shopping": "\U0001f6d2",
    "adult": "\U0001f51e",
    "media": "\U0001f4f0",
    "art": "\U0001f3a8",
    "education": "\U0001f393",
    "finance": "\U0001f4b0",
    "government": "\U0001f3db\ufe0f",
    "messaging": "\U0001f4e8",
    "other": "\U0001f310",
}
