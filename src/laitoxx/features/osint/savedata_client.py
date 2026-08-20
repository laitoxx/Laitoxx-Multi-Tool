from __future__ import annotations

import csv
import hashlib
import re
from collections.abc import Iterable
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SAVEDATA_BASE_URL = "https://data.intelx.io/saverudata/db2"
DEFAULT_TIMEOUT = (5, 20)
DEFAULT_MAX_RESPONSE_BYTES = 8 * 1024 * 1024
DEFAULT_MAX_MATCHES = 100

ENRICHMENT_KEYS = frozenset(
    {
        "cdek_full_name",
        "cdek_email",
        "lnmatch_last_name",
        "yandex_name",
        "yandex_address_city",
        "yandex_place_name",
        "yandex_address_doorcode",
        "beeline_full_name",
        "beeline_address_city",
        "vk_email",
        "avito_user_name",
        "avito_ad_title",
        "avito_city",
        "rfcont_name",
        "rfcont_email",
        "pikabu_email",
    }
)


class _ResponseTooLarge(Exception):
    pass


@dataclass(frozen=True)
class SaveDataResult:
    rows: tuple[dict[str, str], ...] = ()
    status_code: int | None = None
    error: str | None = None
    truncated: bool = False


def normalize_email(email: str) -> str:
    value = str(email).strip().lower()
    if value.count("@") != 1 or any(character.isspace() for character in value):
        raise ValueError("Invalid email address.")
    local_part, domain = value.split("@", 1)
    if not local_part or not domain:
        raise ValueError("Invalid email address.")
    return value


def normalize_phone(phone: str) -> str:
    value = re.sub(r"\D", "", str(phone))
    if not 7 <= len(value) <= 15:
        raise ValueError("Phone number must contain between 7 and 15 digits.")
    return value


def email_shard_url(email: str) -> str:
    normalized = normalize_email(email)
    digest = hashlib.md5(normalized.encode("utf-8")).hexdigest()  # noqa: S324 - shard identifier, not security
    return f"{SAVEDATA_BASE_URL}/dbe/{digest[0]}/{digest[1]}/{digest[:4]}.csv"


def phone_shard_url(phone: str) -> str:
    normalized = normalize_phone(phone)
    shard_key = normalized[:-3]
    path = "/".join(shard_key[index : index + 2] for index in range(0, len(shard_key), 2))
    return f"{SAVEDATA_BASE_URL}/dbpn/{path}.csv"


class SaveDataClient:
    """Bounded client for the undocumented SaveRuData CSV shards hosted by IntelX."""

    def __init__(
        self,
        *,
        timeout: tuple[float, float] = DEFAULT_TIMEOUT,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        max_matches: int = DEFAULT_MAX_MATCHES,
    ) -> None:
        if max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be greater than zero")
        if max_matches <= 0:
            raise ValueError("max_matches must be greater than zero")
        self.timeout = timeout
        self.max_response_bytes = max_response_bytes
        self.max_matches = max_matches

    def lookup_email(self, email: str) -> SaveDataResult:
        try:
            normalized = normalize_email(email)
        except ValueError as exc:
            return SaveDataResult(error=str(exc))
        return self._lookup(email_shard_url(normalized), normalized, _normalize_text)

    def lookup_phone(self, phone: str) -> SaveDataResult:
        try:
            normalized = normalize_phone(phone)
        except ValueError as exc:
            return SaveDataResult(error=str(exc))
        return self._lookup(phone_shard_url(normalized), normalized, _normalize_digits)

    def _lookup(self, url: str, needle: str, normalizer) -> SaveDataResult:
        session = self._create_session()
        try:
            with session.get(url, timeout=self.timeout, stream=True) as response:
                status_error = self._status_error(response.status_code)
                if status_error:
                    return SaveDataResult(status_code=response.status_code, error=status_error)
                if response.status_code in {204, 404}:
                    return SaveDataResult(status_code=response.status_code)

                content_length = response.headers.get("Content-Length")
                if content_length and content_length.isdigit() and int(content_length) > self.max_response_bytes:
                    return SaveDataResult(
                        status_code=response.status_code,
                        error=f"SaveRuData response exceeds {self.max_response_bytes // (1024 * 1024)} MiB limit.",
                    )

                content_type = response.headers.get("Content-Type", "").lower()
                if content_type and not self._is_csv_content_type(content_type):
                    return SaveDataResult(
                        status_code=response.status_code,
                        error=f"SaveRuData returned unexpected content type: {content_type.split(';', 1)[0]}.",
                    )

                return self._parse_response(response, needle, normalizer)
        except requests.RequestException as exc:
            return SaveDataResult(error=f"SaveRuData request failed: {exc}")
        finally:
            session.close()

    def _parse_response(self, response: requests.Response, needle: str, normalizer) -> SaveDataResult:
        rows: list[dict[str, str]] = []
        truncated = False
        normalized_needle = normalizer(needle)
        try:
            reader = csv.DictReader(self._decoded_lines(response))
            for row in reader:
                if not any(normalized_needle in normalizer(value) for value in row.values() if value is not None):
                    continue
                rows.append(_clean_row(row))
                if len(rows) >= self.max_matches:
                    truncated = True
                    break
        except (_ResponseTooLarge, csv.Error, LookupError, UnicodeError) as exc:
            return SaveDataResult(status_code=response.status_code, error=f"Invalid SaveRuData CSV response: {exc}")
        except requests.RequestException as exc:
            return SaveDataResult(status_code=response.status_code, error=f"SaveRuData stream failed: {exc}")
        return SaveDataResult(tuple(rows), status_code=response.status_code, truncated=truncated)

    def _decoded_lines(self, response: requests.Response) -> Iterable[str]:
        total_bytes = 0
        encoding = _response_encoding(response)
        for raw_line in response.iter_lines(decode_unicode=False):
            if not isinstance(raw_line, bytes):
                raw_line = str(raw_line).encode(encoding, errors="replace")
            total_bytes += len(raw_line) + 1
            if total_bytes > self.max_response_bytes:
                raise _ResponseTooLarge(f"response exceeds {self.max_response_bytes // (1024 * 1024)} MiB limit")
            yield raw_line.decode(encoding, errors="replace")

    @staticmethod
    def _create_session() -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=2,
            connect=2,
            read=2,
            status=2,
            backoff_factor=0.4,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.headers.update(
            {
                "Accept": "text/csv,text/plain;q=0.9,application/octet-stream;q=0.8",
                "User-Agent": "Laitoxx-Multi-Tool/SaveRuDataClient",
            }
        )
        return session

    @staticmethod
    def _is_csv_content_type(content_type: str) -> bool:
        return any(
            accepted in content_type
            for accepted in ("text/csv", "application/csv", "text/plain", "application/octet-stream")
        )

    @staticmethod
    def _status_error(status_code: int) -> str | None:
        if status_code in {200, 204, 404}:
            return None
        if status_code in {401, 403}:
            return f"SaveRuData access denied (HTTP {status_code})."
        if status_code == 429:
            return "SaveRuData rate limit exceeded (HTTP 429)."
        if status_code >= 500:
            return f"SaveRuData service is unavailable (HTTP {status_code})."
        return f"Unexpected SaveRuData response (HTTP {status_code})."


def _normalize_text(value: object) -> str:
    return str(value).strip().lower()


def _normalize_digits(value: object) -> str:
    return re.sub(r"\D", "", str(value))


def _clean_row(row: dict[str | None, object]) -> dict[str, str]:
    clean: dict[str, str] = {}
    for key, value in row.items():
        if key is None or value is None:
            continue
        if isinstance(value, list):
            rendered = ",".join(str(item) for item in value)
        else:
            rendered = str(value)
        clean[str(key).lstrip("\ufeff")] = rendered
    return clean


def _response_encoding(response: requests.Response) -> str:
    content_type = response.headers.get("Content-Type", "")
    charset_match = re.search(r"charset=([^;\s]+)", content_type, flags=re.IGNORECASE)
    if charset_match:
        return charset_match.group(1).strip("\"'")
    return "utf-8-sig"
