"""The cache policy: which endpoint is cached for how long, keys, and the entry envelope."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from cadastral_api.cache import policy

CLIENT_SOURCE = (
    Path(__file__).resolve().parents[2] / "src" / "cadastral_api" / "client" / "api_client.py"
)

#: Endpoints the client calls that are deliberately not cached.
UNCACHED: set[str] = set()


def test_every_client_endpoint_has_a_data_class_or_is_listed_as_uncached() -> None:
    source = CLIENT_SOURCE.read_text(encoding="utf-8")
    endpoints = set(
        re.findall(r'"(/(?:search-cad-parcels|search-lr-parcels|cad|lr)/[a-z\-]+)"', source)
    )
    assert endpoints, "no endpoint literals found in the client"
    unclassified = {e for e in endpoints if policy.data_class_of(e) is None} - UNCACHED
    assert not unclassified, f"endpoints without a data class: {sorted(unclassified)}"
    stale = set(policy.ENDPOINT_CLASS) - endpoints
    assert not stale, f"policy names endpoints the client does not call: {sorted(stale)}"


def test_personal_data_classes_never_exceed_thirty_minutes() -> None:
    for name, cls in policy.CLASSES.items():
        if cls.personal_data:
            assert cls.lifetime <= policy.MAX_PERSONAL_DATA_LIFETIME, name
    assert {n for n, c in policy.CLASSES.items() if c.personal_data} == {
        "parcel_detail", "possession_sheet", "lr_unit"
    }


def test_endpoints_that_answer_with_people_are_personal_data() -> None:
    """A parcel search returns whole records, possessors and owners included."""
    for endpoint in (
        "/cad/parcel-info",
        "/cad/possession-sheet",
        "/cad/possession-sheet-by-number",
        "/cad/search-parcels",
        "/lr/lr-unit",
    ):
        cls = policy.data_class_of(endpoint)
        assert cls is not None and cls.personal_data, endpoint
        assert cls.lifetime <= policy.MAX_PERSONAL_DATA_LIFETIME, endpoint


def test_lifetimes_follow_the_specification_table() -> None:
    assert policy.CLASSES["reference"].lifetime == 24 * 3600
    assert policy.CLASSES["search"].lifetime == 6 * 3600
    assert policy.CLASSES["lr_unit"].lifetime == 30 * 60
    assert policy.CLASSES["file_status"].lifetime == 5 * 60


class TestKey:
    def test_is_versioned_and_hex(self) -> None:
        key = policy.cache_key("http://a", "GET", "/lr/lr-unit", {"x": "1"})
        assert key.startswith(policy.KEY_PREFIX)
        assert re.fullmatch(r"[0-9a-f]{64}", key[len(policy.KEY_PREFIX):])

    def test_differs_when_only_the_base_url_differs(self) -> None:
        a = policy.cache_key("http://localhost:8000", "GET", "/lr/lr-unit", {"x": "1"})
        b = policy.cache_key("https://other.example", "GET", "/lr/lr-unit", {"x": "1"})
        assert a != b

    def test_a_trailing_slash_on_the_base_url_does_not_matter(self) -> None:
        a = policy.cache_key("http://localhost:8000", "GET", "/e", {"x": "1"})
        b = policy.cache_key("http://localhost:8000/", "GET", "/e", {"x": "1"})
        assert a == b

    def test_parameter_order_does_not_matter(self) -> None:
        a = policy.cache_key("http://a", "GET", "/e", {"x": "1", "y": "2"})
        b = policy.cache_key("http://a", "GET", "/e", {"y": "2", "x": "1"})
        assert a == b
        assert a != policy.cache_key("http://a", "GET", "/e", {"x": "1", "y": "3"})

    def test_the_body_is_part_of_the_key_for_post(self) -> None:
        a = policy.cache_key("http://a", "POST", "/lr/file-status", None, {"k": 1, "j": 2})
        b = policy.cache_key("http://a", "POST", "/lr/file-status", None, {"j": 2, "k": 1})
        c = policy.cache_key("http://a", "POST", "/lr/file-status", None, {"k": 1, "j": 3})
        assert a == b and a != c
        assert a != policy.cache_key("http://a", "GET", "/lr/file-status")


class TestEnvelope:
    def test_round_trip(self) -> None:
        raw = policy.encode(
            {"a": [1, "č"]}, fetched_at="2026-09-16T12:00:00+00:00",
            endpoint="/cad/parcel-info", data_class="parcel_detail",
        )
        header, body = raw.split(b"\n", 1)
        assert header.startswith(b'{"v":1,')
        assert body == '{"a":[1,"č"]}'.encode()
        envelope = policy.decode(raw)
        assert envelope is not None
        assert envelope.body == {"a": [1, "č"]}
        assert envelope.fetched_at == "2026-09-16T12:00:00+00:00"
        assert (envelope.endpoint, envelope.data_class) == ("/cad/parcel-info", "parcel_detail")

    @pytest.mark.parametrize(
        "raw",
        [
            b"",
            b"garbage",
            b"{}\n{}",
            b'{"v":2,"fetched_at":"x","endpoint":"/e","class":"c"}\n{}',
            b'{"v":1,"fetched_at":"x"}\n{}',
            b'{"v":1,"fetched_at":"x","endpoint":"/e","class":"c"}\nnot json',
            b"\xff\xfe",
        ],
    )
    def test_unreadable_or_other_version_is_none(self, raw: bytes) -> None:
        assert policy.decode(raw) is None

    def test_remaining_lifetime_follows_the_class(self) -> None:
        from datetime import datetime, timezone

        envelope = policy.Envelope(
            {}, "2026-09-16T12:00:00+00:00", "/lr/lr-unit", "lr_unit"
        )
        now = datetime(2026, 9, 16, 12, 10, tzinfo=timezone.utc)
        assert envelope.age_seconds(now) == 600
        assert envelope.remaining_lifetime(now) == 20 * 60
        assert envelope.remaining_lifetime(datetime(2026, 9, 17, tzinfo=timezone.utc)) == 0
        assert policy.Envelope({}, "2026-09-16T12:00:00Z", "/e", "unknown").remaining_lifetime(
            now
        ) == 0
