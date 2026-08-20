"""Local runtime checks for pure domain and serialization boundaries."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image

from laitoxx.core.settings.proxy_config import build_proxies, build_proxy_url
from laitoxx.features.crypto.hash_tools.hash_identifier import identify_hash
from laitoxx.features.crypto.hash_tools.text_hasher import hash_text
from laitoxx.features.osint.advanced_web_scanner.models import normalize_target
from laitoxx.features.osint.advanced_web_scanner.provider.reverse_lookup import domain_candidate, domains_from_payload
from laitoxx.features.osint.email_validator import is_valid_email
from laitoxx.features.osint.image_search import build_search_urls
from laitoxx.features.osint.tongue.domain.gifts import (
    extract_public_profiles,
    extract_ton_address_candidates,
    normalize_gift_slug,
    parse_title_number,
    split_slug,
)
from laitoxx.features.osint.tongue.domain.primitives import (
    extract_comment,
    flatten_text,
    is_numeric_memo,
    jsonable,
    repeated_params,
    safe_int,
    short,
    stable_id,
    ton_amount,
    ts_to_iso,
    tx_succeeded,
)
from laitoxx.features.utilities.ioc_extractor import extract_entities
from laitoxx.features.utilities.steganography.api import create_config, decode_text, encode_text
from laitoxx.features.utilities.steganography.crypto import decrypt, encrypt, pack_payload, unpack_payload
from laitoxx.features.utilities.steganography.models import StegConfig, StegHeader, derive_magic, get_channel_preset
from laitoxx.features.utilities.text_cipher import _transform
from laitoxx.interfaces.gui.plugin_syntax_check import check_lua_syntax
from laitoxx.interfaces.gui.plugin_template import generate_plugin_template
from laitoxx.shared.graph.algorithms import calculate_centralities, get_shortest_path
from laitoxx.shared.graph.mermaid import generate_mermaid
from laitoxx.shared.graph.model import Edge, Graph, Node


def text_and_identifiers() -> None:
    sample = "Hello, мир!"
    for mode in ("binary", "hex", "base64", "url"):
        assert _transform(mode, "decode", _transform(mode, "encode", sample), 7) == sample
    assert _transform("caesar", "decode", _transform("caesar", "encode", sample, 25), 25) == sample
    assert _transform("rot13", "encode", _transform("rot13", "encode", "Hello")) == "Hello"
    assert _transform("reverse", "encode", _transform("reverse", "decode", sample)) == sample
    assert _transform("unknown", "encode", sample).startswith("[unknown mode:")
    assert _transform("hex", "decode", "xx").startswith("[error:")
    assert hash_text("abc", "sha256") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert identify_hash("d41d8cd98f00b204e9800998ecf8427e")


def ioc_and_targets() -> None:
    values = {
        (item.kind, item.value)
        for item in extract_entities(
            "mail a@example.com ip 192.0.2.4 url https://example.com/a user @demo_user "
            "hash d41d8cd98f00b204e9800998ecf8427e"
        )
    }
    assert ("email", "a@example.com") in values
    assert ("ip", "192.0.2.4") in values
    assert is_valid_email("a+b@example.co.uk") and not is_valid_email("bad@")
    normalized_url = normalize_target("HTTPS://Example.COM/path")
    assert normalized_url.kind == "url" and normalized_url.value == "https://example.com/path"
    assert normalize_target("192.0.2.1").kind == "ip"
    assert domain_candidate("Sub.Example.com") == "sub.example.com"
    assert domains_from_payload({"domains": ["example.com", "sub.example.org"]}) == [
        "example.com",
        "sub.example.org",
    ]
    urls = build_search_urls("https://example.invalid/image.png", ["Google Lens", "Bing"])
    assert set(urls) == {"Google Lens", "Bing"}


def proxy_boundaries() -> None:
    assert build_proxy_url({}) == ""
    assert build_proxies({}) is None
    cfg = {"enabled": True, "scheme": "http", "host": "127.0.0.1", "port": 8080}
    assert build_proxy_url(cfg) == "http://127.0.0.1:8080"
    assert build_proxies(cfg) == {"http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080"}


def graph_roundtrip() -> None:
    graph = Graph("demo", "LR")
    first = Node.from_type('A "quoted"', "Person")
    duplicate = Node("A duplicate", description="second", metadata={"source": "two"})
    target = Node("B", metadata={"unicode": "мир"})
    for node in (first, duplicate, target):
        graph.add_node(node)
    assert graph.add_edge(Edge(first.id, target.id, "knows"))
    assert graph.add_edge(Edge(duplicate.id, target.id, "knows", metadata={"source": "edge"}))
    assert not graph.add_edge(Edge("missing", target.id))
    graph.merge_nodes(first.id, [duplicate.id, "missing"])
    assert len(graph.nodes) == 2 and len(graph.edges) == 1
    assert get_shortest_path(graph, first.id, target.id) == [first.id, target.id]
    assert set(calculate_centralities(graph, "degree")) == {first.id, target.id}
    assert generate_mermaid(graph).startswith("graph LR")
    restored = Graph.from_dict(graph.to_dict())
    assert restored.to_dict() == graph.to_dict()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "graph.json"
        graph.save_json(str(path))
        assert Graph.load_json(str(path)).to_dict() == graph.to_dict()
    graph.remove_node(target.id)
    assert not graph.edges


def steganography_roundtrip() -> None:
    for preset in ("R", "RGB", "RGBA", "unknown"):
        assert get_channel_preset(preset)
    config = create_config("RGB", bits=2, compress=True, strategy="interleaved")
    assert StegConfig.from_bytes(config.to_bytes()) == config
    header = StegHeader(config=config, payload_length=17, original_length=20, crc32=123)
    assert StegHeader.from_bytes(header.to_bytes()).payload_length == 17
    assert StegHeader.from_bytes(header.to_bytes("secret"), "secret").config == config
    assert derive_magic("a") != derive_magic("b")
    payload = b"binary\x00payload" * 4
    for method in ("xor", "aes-gcm"):
        packed = encrypt(payload, "secret", method)
        assert decrypt(packed, "secret") == payload
        assert pack_payload(unpack_payload(packed)) == packed
    image = Image.new("RGB", (96, 96), (100, 120, 140))
    encoded = encode_text(image, "Hello, мир 👋", config)
    assert decode_text(encoded, config) == "Hello, мир 👋"


def tongue_primitives() -> None:
    assert safe_int("12") == 12 and safe_int(None, 7) == 7
    assert ton_amount(1_000_000_000) == 1.0
    assert short("12345678901234567890") == "1234567…67890"
    assert stable_id("a", 1) == stable_id("a", 1)
    assert ts_to_iso(1).startswith("1970-01-01") and ts_to_iso(0) is None
    assert jsonable({"x": {1, 2}})
    assert "hello" in flatten_text({"a": ["hello"]})
    assert extract_comment({"message_content": {"decoded": {"comment": "memo"}}}) == "memo"
    assert is_numeric_memo("123456") and not is_numeric_memo("12a")
    assert tx_succeeded({"description": {"aborted": False}})
    assert repeated_params("x", ["a", "b"]) == [("x", "a"), ("x", "b")]
    assert normalize_gift_slug("https://t.me/nft/PlushPepe-123") == "plushpepe-123"
    assert split_slug("plushpepe-123") == ("plushpepe", 123)
    assert parse_title_number("Plush Pepe #123") == ("Plush Pepe", 123)
    assert extract_public_profiles("https://t.me", ["https://t.me/demo", "https://example.com"])
    assert isinstance(extract_ton_address_candidates("", []), list)


def plugin_boundaries() -> None:
    valid = generate_plugin_template("Demo", "utility", "Author", "Description", ["windows"])
    assert "Demo" in valid and not check_lua_syntax(valid)
    assert check_lua_syntax("function broken(")


CASES = (
    text_and_identifiers,
    ioc_and_targets,
    proxy_boundaries,
    graph_roundtrip,
    steganography_roundtrip,
    tongue_primitives,
    plugin_boundaries,
)


def main() -> int:
    for case in CASES:
        case()
        print(f"PASS {case.__name__}")
    print(f"cases={len(CASES)} failed=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
