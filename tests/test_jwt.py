"""Unit tests for JWT parsing and signature verification."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json

import pytest

from laitoxx.features.crypto.jwt_analyzer import (
    _b64_decode,
    _parse_jwt,
    _verify_signature,
)


def _make_jwt(header: dict, payload: dict, secret: str, algo: str = "HS256") -> str:
    """Helper: create a real signed JWT."""
    digest_map = {"HS256": hashlib.sha256, "HS384": hashlib.sha384, "HS512": hashlib.sha512}
    h = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
    p = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    content = f"{h}.{p}"
    sig = hmac.new(secret.encode(), content.encode(), digest_map[algo]).digest()
    s = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
    return f"{content}.{s}"


# ── _b64_decode ───────────────────────────────────────────────────────────────

class TestB64Decode:
    def test_standard(self):
        assert _b64_decode("aGVsbG8=") == b"hello"

    def test_without_padding(self):
        assert _b64_decode("aGVsbG8") == b"hello"

    def test_url_safe(self):
        # URL-safe variant uses - and _ instead of + and /
        data = b"\xfb\xff"
        encoded = base64.urlsafe_b64encode(data).rstrip(b"=").decode()
        assert _b64_decode(encoded) == data


# ── _parse_jwt ────────────────────────────────────────────────────────────────

class TestParseJwt:
    def test_valid_jwt(self):
        token = _make_jwt({"alg": "HS256", "typ": "JWT"}, {"sub": "user1"}, "secret")
        result = _parse_jwt(token)
        assert result is not None
        header, payload, sig, raw_h, raw_p = result
        assert header["alg"] == "HS256"
        assert payload["sub"] == "user1"
        assert isinstance(sig, bytes)

    def test_invalid_too_few_parts(self):
        assert _parse_jwt("only.twoparts") is None

    def test_invalid_too_many_parts(self):
        assert _parse_jwt("a.b.c.d") is None

    def test_invalid_base64(self):
        assert _parse_jwt("!!!.!!!.!!!") is None

    def test_none_alg_jwt(self):
        token = _make_jwt({"alg": "none", "typ": "JWT"}, {"admin": True}, "")
        result = _parse_jwt(token)
        assert result is not None
        header, payload, *_ = result
        assert header["alg"] == "none"
        assert payload["admin"] is True

    def test_exp_claim_preserved(self):
        import time
        exp = int(time.time()) + 3600
        token = _make_jwt({"alg": "HS256"}, {"exp": exp, "iss": "test"}, "key")
        result = _parse_jwt(token)
        assert result is not None
        _, payload, *_ = result
        assert payload["exp"] == exp
        assert payload["iss"] == "test"


# ── _verify_signature ─────────────────────────────────────────────────────────

class TestVerifySignature:
    def _raw_sig(self, content: str, secret: str, algo: str) -> str:
        digest_map = {"HS256": hashlib.sha256, "HS384": hashlib.sha384, "HS512": hashlib.sha512}
        sig = hmac.new(secret.encode(), content.encode(), digest_map[algo]).digest()
        return base64.urlsafe_b64encode(sig).rstrip(b"=").decode()

    def test_hs256_valid(self):
        content = "header.payload"
        secret = "mysecret"
        raw_sig = self._raw_sig(content, secret, "HS256")
        assert _verify_signature(secret, content, raw_sig, "HS256") is True

    def test_hs256_wrong_secret(self):
        content = "header.payload"
        raw_sig = self._raw_sig(content, "correct", "HS256")
        assert _verify_signature("wrong", content, raw_sig, "HS256") is False

    def test_hs384_valid(self):
        content = "h.p"
        secret = "s3cr3t"
        raw_sig = self._raw_sig(content, secret, "HS384")
        assert _verify_signature(secret, content, raw_sig, "HS384") is True

    def test_hs512_valid(self):
        content = "h.p"
        secret = "supersecret"
        raw_sig = self._raw_sig(content, secret, "HS512")
        assert _verify_signature(secret, content, raw_sig, "HS512") is True

    def test_tampered_payload(self):
        content_signed = "header.original_payload"
        content_tampered = "header.tampered_payload"
        secret = "key"
        raw_sig = self._raw_sig(content_signed, secret, "HS256")
        assert _verify_signature(secret, content_tampered, raw_sig, "HS256") is False


# ── Full token roundtrip ──────────────────────────────────────────────────────

class TestFullRoundtrip:
    def test_parse_and_verify(self):
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {"sub": "42", "name": "Alice"}
        secret = "top_secret"
        token = _make_jwt(header, payload, secret)

        parsed = _parse_jwt(token)
        assert parsed is not None
        hdr, pld, sig, raw_h, raw_p = parsed

        content = f"{raw_h}.{raw_p}"
        raw_sig = token.split(".")[2]
        assert _verify_signature(secret, content, raw_sig, "HS256") is True

    def test_parse_and_verify_wrong_secret(self):
        token = _make_jwt({"alg": "HS256"}, {"sub": "1"}, "real_secret")
        parsed = _parse_jwt(token)
        assert parsed is not None
        _, _, _, raw_h, raw_p = parsed
        content = f"{raw_h}.{raw_p}"
        raw_sig = token.split(".")[2]
        assert _verify_signature("wrong_secret", content, raw_sig, "HS256") is False
