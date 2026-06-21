"""Unit tests for text_transformer encoding/decoding functions."""
from __future__ import annotations

import pytest

# Import private helpers directly — they are pure functions with no side effects.
from laitoxx.features.utilities.text_transformer import (
    _caesar,
    _decode_morse,
    _encode_morse,
    _transform,
    _transform_base64,
    _transform_binary,
    _transform_hex,
    _transform_leet,
    _transform_rot13,
    _transform_url,
)


# ── Morse ─────────────────────────────────────────────────────────────────────

class TestMorse:
    def test_encode_simple(self):
        assert _encode_morse("SOS") == "... --- ..."

    def test_encode_word_boundary(self):
        assert _encode_morse("HI BYE") == ".... .. / -... -.-- ."

    def test_decode_simple(self):
        assert _decode_morse("... --- ...") == "SOS"

    def test_decode_word_boundary(self):
        assert _decode_morse(".... .. / -... -.-- .") == "HI BYE"

    def test_roundtrip(self):
        for word in ("HELLO", "WORLD", "LAITOXX"):
            assert _decode_morse(_encode_morse(word)) == word

    def test_unknown_character(self):
        # Tilde is not in the Morse alphabet — should produce '?'
        result = _encode_morse("~")
        assert "?" in result


# ── Caesar cipher ─────────────────────────────────────────────────────────────

class TestCaesar:
    def test_encode_shift3(self):
        assert _caesar("ABC", 3) == "DEF"

    def test_wraps_around_z(self):
        assert _caesar("XYZ", 3) == "ABC"

    def test_preserves_lowercase(self):
        assert _caesar("abc", 3) == "def"

    def test_preserves_non_alpha(self):
        assert _caesar("Hello, World!", 0) == "Hello, World!"

    def test_decode_is_inverse(self):
        original = "The quick brown fox"
        encoded = _caesar(original, 13)
        assert _caesar(encoded, -13) == original

    def test_shift_26_is_identity(self):
        assert _caesar("ABCXYZ", 26) == "ABCXYZ"


# ── Base64 ────────────────────────────────────────────────────────────────────

class TestBase64:
    def test_encode(self):
        assert _transform_base64("encode", "hello", 0) == "aGVsbG8="

    def test_decode(self):
        assert _transform_base64("decode", "aGVsbG8=", 0) == "hello"

    def test_decode_without_padding(self):
        assert _transform_base64("decode", "aGVsbG8", 0) == "hello"

    def test_roundtrip_unicode(self):
        text = "Привет мир"
        encoded = _transform_base64("encode", text, 0)
        assert _transform_base64("decode", encoded, 0) == text

    def test_invalid_returns_error(self):
        result = _transform_base64("decode", "!!!not_base64!!!", 0)
        assert result.startswith("[error:")


# ── Hex ───────────────────────────────────────────────────────────────────────

class TestHex:
    def test_encode(self):
        assert _transform_hex("encode", "hi", 0) == "6869"

    def test_decode(self):
        assert _transform_hex("decode", "6869", 0) == "hi"

    def test_decode_with_spaces(self):
        assert _transform_hex("decode", "68 69", 0) == "hi"

    def test_roundtrip(self):
        text = "Laitoxx 2025"
        assert _transform_hex("decode", _transform_hex("encode", text, 0), 0) == text

    def test_invalid_hex_returns_error(self):
        result = _transform_hex("decode", "ZZ", 0)
        assert result.startswith("[error:")


# ── Binary ────────────────────────────────────────────────────────────────────

class TestBinary:
    def test_encode(self):
        assert _transform_binary("encode", "A", 0) == "01000001"

    def test_decode(self):
        assert _transform_binary("decode", "01000001", 0) == "A"

    def test_roundtrip(self):
        text = "Hello"
        assert _transform_binary("decode", _transform_binary("encode", text, 0), 0) == text

    def test_invalid_binary_returns_error(self):
        result = _transform_binary("decode", "99999", 0)
        assert result.startswith("[error:")


# ── ROT13 ─────────────────────────────────────────────────────────────────────

class TestRot13:
    def test_encode(self):
        assert _transform_rot13("encode", "Hello", 0) == "Uryyb"

    def test_self_inverse(self):
        text = "The quick brown fox"
        assert _transform_rot13("decode", _transform_rot13("encode", text, 0), 0) == text

    def test_numbers_unchanged(self):
        assert _transform_rot13("encode", "abc123", 0) == "nop123"


# ── Leet ──────────────────────────────────────────────────────────────────────

class TestLeet:
    def test_encode_a(self):
        assert "4" in _transform_leet("encode", "a", 0) or "@" in _transform_leet("encode", "a", 0)

    def test_encode_e(self):
        assert "3" in _transform_leet("encode", "e", 0)

    def test_encode_i(self):
        result = _transform_leet("encode", "i", 0)
        assert "1" in result or "!" in result


# ── URL encoding ──────────────────────────────────────────────────────────────

class TestUrl:
    def test_encode_space(self):
        assert _transform_url("encode", "hello world", 0) == "hello%20world"

    def test_encode_special(self):
        result = _transform_url("encode", "a=1&b=2", 0)
        assert "%" in result

    def test_decode(self):
        assert _transform_url("decode", "hello%20world", 0) == "hello world"

    def test_roundtrip(self):
        text = "https://example.com/path?q=hello world"
        encoded = _transform_url("encode", text, 0)
        assert _transform_url("decode", encoded, 0) == text


# ── _transform dispatcher ────────────────────────────────────────────────────

class TestDispatcher:
    def test_unknown_mode(self):
        result = _transform("nonexistent_mode", "encode", "hello")
        assert "[unknown mode:" in result

    def test_caesar_via_dispatcher(self):
        assert _transform("caesar", "encode", "ABC", 3) == "DEF"

    def test_reverse(self):
        assert _transform("reverse", "encode", "hello") == "olleh"

    def test_upper(self):
        assert _transform("upper", "encode", "hello") == "HELLO"

    def test_lower(self):
        assert _transform("lower", "encode", "HELLO") == "hello"
