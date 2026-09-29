"""The response cache in the client: hits, misses, refresh, locks, and the schema-change rules.

Every test runs a real ``CadastralAPIClient`` on a ``MockTransport`` that
records the requests it receives, so "served from the cache" means "the
transport saw nothing".
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path

import httpx
import pytest

from cadastral_api import CadastralAPIClient
from cadastral_api.cache import Fetched, MemoryCache, NullCache, from_config, policy
from cadastral_api.exceptions import CadastralAPIError, ErrorType

FIXTURES = Path(__file__).resolve().parents[2] / "src" / "cadastral_api" / "tests" / "fixtures"

_FIXTURE_FOR_PATH = {
    "/lr/lr-unit": "lr_unit_lrparcels.json",
    "/cad/parcel-info": "parcel_info_direct.json",
    "/search-cad-parcels/offices": "offices.json",
}


def _fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _serve_fixtures(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=_fixture(_FIXTURE_FOR_PATH[request.url.path]))


def _client(handler, **kwargs) -> tuple[CadastralAPIClient, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def recording(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    kwargs.setdefault("rate_limit", 0)
    client = CadastralAPIClient(base_url="http://mock", **kwargs)
    client.client = httpx.Client(base_url="http://mock", transport=httpx.MockTransport(recording))
    return client, seen


def _unit_key(client: CadastralAPIClient, number: str = "449", book: int = 21277) -> str:
    return policy.cache_key(
        client.base_url,
        "GET",
        "/lr/lr-unit",
        {"lrUnitNumber": number, "mainBookId": str(book), "historicalOverview": "false"},
    )


class TestHitsAndMisses:
    def test_the_second_identical_call_makes_no_request(self) -> None:
        client, seen = _client(_serve_fixtures)
        first = client.get_lr_unit_detailed("449", 21277)
        second = client.get_lr_unit_detailed("449", 21277)
        assert len(seen) == 1
        assert second.lr_unit_number == first.lr_unit_number
        assert second is not first  # parsed afresh from the stored bytes
        stats = client.cache.stats()
        assert (stats.entries, stats.hits, stats.misses) == (1, 1, 1)

    def test_a_different_request_is_a_different_entry(self) -> None:
        client, seen = _client(_serve_fixtures)
        client.get_lr_unit_detailed("449", 21277)
        client.get_lr_unit_detailed("449", 21277, historical_overview=True)
        client.get_parcel_info("6564741")
        client.list_cadastral_offices()
        client.list_cadastral_offices()
        assert [r.url.path for r in seen] == [
            "/lr/lr-unit", "/lr/lr-unit", "/cad/parcel-info", "/search-cad-parcels/offices"
        ]

    def test_cache_off_fetches_every_time(self) -> None:
        client, seen = _client(_serve_fixtures, cache="off")
        client.get_lr_unit_detailed("449", 21277)
        client.get_lr_unit_detailed("449", 21277)
        assert len(seen) == 2
        assert client.cache.stats().backend == "off"

    def test_a_ready_backend_is_used_as_is(self) -> None:
        backend = MemoryCache(max_bytes=1 << 20)
        client, seen = _client(_serve_fixtures, cache=backend)
        assert client.cache is backend
        client.get_parcel_info("6564741")
        assert backend.stats().entries == 1

    def test_an_error_response_is_not_stored(self) -> None:
        calls = {"n": 0}

        def flaky(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            if calls["n"] == 1:
                return httpx.Response(404, text="no")
            return _serve_fixtures(request)

        client, seen = _client(flaky)
        with pytest.raises(CadastralAPIError):
            client.get_parcel_info("6564741")
        client.get_parcel_info("6564741")
        assert len(seen) == 2
        client.get_parcel_info("6564741")
        assert len(seen) == 2

    def test_an_empty_answer_is_not_stored(self) -> None:
        client, seen = _client(lambda request: httpx.Response(200, json=[]))
        for _ in range(2):
            with pytest.raises(CadastralAPIError) as e:
                client.get_lr_unit_detailed("1", 1)
            assert e.value.error_type is ErrorType.LR_UNIT_NOT_FOUND
        assert len(seen) == 2
        assert client.cache.stats().entries == 0

    def test_a_hit_does_not_wait_for_the_rate_limiter(self) -> None:
        client, seen = _client(_serve_fixtures, rate_limit=5.0)
        client.get_parcel_info("6564741")
        started = time.monotonic()
        client.get_parcel_info("6564741")
        assert time.monotonic() - started < 1.0
        assert len(seen) == 1

    def test_two_threads_asking_for_one_record_make_one_request(self) -> None:
        gate = threading.Event()

        def slow(request: httpx.Request) -> httpx.Response:
            gate.wait(timeout=5)
            return _serve_fixtures(request)

        client, seen = _client(slow)
        results: list = []

        def read() -> None:
            results.append(client.get_lr_unit_detailed("449", 21277))

        threads = [threading.Thread(target=read) for _ in range(3)]
        for t in threads:
            t.start()
        time.sleep(0.2)  # everyone is waiting on the same key
        gate.set()
        for t in threads:
            t.join(timeout=10)
        assert len(results) == 3 and len(seen) == 1
        assert len(client._inflight) == 0  # locks are dropped afterwards


class TestProvenance:
    def test_retrieved_at_is_the_original_fetch_time_on_a_hit(self) -> None:
        client, _ = _client(_serve_fixtures)
        first = client.get_parcel_info("6564741")
        key = policy.cache_key(client.base_url, "GET", "/cad/parcel-info", {"parcelId": "6564741"})
        stored = policy.decode(client.cache.get(key))
        assert stored is not None
        # Pretend the entry was written earlier and check the hit reports it.
        older = stored.fetched_at.replace("2026", "2025", 1) if "2026" in stored.fetched_at else (
            "2025-01-01T00:00:00+00:00"
        )
        client.cache.set(
            key,
            policy.encode(stored.body, fetched_at=older, endpoint=stored.endpoint,
                          data_class=stored.data_class),
            ttl=60,
        )
        second = client.get_parcel_info("6564741")
        assert first.provenance is not None and second.provenance is not None
        assert second.provenance.retrieved_at == older
        assert first.provenance.source_url == second.provenance.source_url


class TestRefresh:
    def test_refresh_fetches_and_overwrites(self) -> None:
        client, seen = _client(_serve_fixtures)
        client.get_lr_unit_detailed("449", 21277)
        client.get_lr_unit_detailed("449", 21277, refresh=True)
        assert len(seen) == 2
        client.get_lr_unit_detailed("449", 21277)
        assert len(seen) == 2

    def test_refresh_from_parcel_reaches_the_personal_data_hops_only(self) -> None:
        parcel = _fixture("parcel_info_direct.json")

        def serve(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if path == "/search-cad-parcels/municipalities":
                return httpx.Response(200, json=_fixture("municipalities_savar.json"))
            if path == "/search-cad-parcels/parcel-numbers":
                record = dict(_fixture("parcel_search_prefix.json")[0])
                record.update(key1=str(parcel["parcelId"]), value1=parcel["parcelNumber"])
                return httpx.Response(200, json=[record])
            return _serve_fixtures(request)

        client, seen = _client(serve)
        client.get_lr_unit_from_parcel(parcel["parcelNumber"], "SAVAR")
        before = [r.url.path for r in seen]
        assert before.count("/cad/parcel-info") == 1 and before.count("/lr/lr-unit") == 1
        client.get_lr_unit_from_parcel(parcel["parcelNumber"], "SAVAR")
        assert len(seen) == len(before)  # every hop served from the cache
        client.get_lr_unit_from_parcel(parcel["parcelNumber"], "SAVAR", refresh=True)
        after = [r.url.path for r in seen[len(before):]]
        assert sorted(after) == ["/cad/parcel-info", "/lr/lr-unit"]


class TestSchemaChanges:
    def test_an_entry_of_another_format_version_is_a_miss(self) -> None:
        client, seen = _client(_serve_fixtures)
        key = _unit_key(client)
        other_version = b'{"v":99,"fetched_at":"x","endpoint":"/lr/lr-unit","class":"lr_unit"}\n{}'
        client.cache.set(key, other_version, 60)
        client.get_lr_unit_detailed("449", 21277)
        assert len(seen) == 1
        assert policy.decode(client.cache.get(key)) is not None  # replaced by the fresh entry

    def test_a_corrupt_entry_is_a_miss_and_is_replaced(self) -> None:
        client, seen = _client(_serve_fixtures)
        key = _unit_key(client)
        client.cache.set(key, b"\xff not an envelope", 60)
        client.get_lr_unit_detailed("449", 21277)
        assert len(seen) == 1
        assert policy.decode(client.cache.get(key)) is not None

    def test_a_cached_body_the_model_rejects_is_refetched(self, caplog) -> None:
        client, seen = _client(_serve_fixtures)
        key = _unit_key(client)
        client.cache.set(
            key,
            policy.encode([{"lrUnitNumber": 12345}], fetched_at="2026-01-01T00:00:00+00:00",
                          endpoint="/lr/lr-unit", data_class="lr_unit"),
            60,
        )
        with caplog.at_level(logging.WARNING, logger="cadastral_api.client.api_client"):
            unit = client.get_lr_unit_detailed("449", 21277)
        assert unit.lr_unit_number == "449"
        assert len(seen) == 1
        assert "no longer parses" in caplog.text
        client.get_lr_unit_detailed("449", 21277)
        assert len(seen) == 1  # the fresh entry replaced the rejected one

    def test_only_the_fresh_failure_is_raised(self) -> None:
        client, seen = _client(lambda request: httpx.Response(200, json=[{"lrUnitNumber": 1}]))
        key = _unit_key(client)
        client.cache.set(
            key,
            policy.encode([{"other": "junk"}], fetched_at="2026-01-01T00:00:00+00:00",
                          endpoint="/lr/lr-unit", data_class="lr_unit"),
            60,
        )
        with pytest.raises(CadastralAPIError) as e:
            client.get_lr_unit_detailed("449", 21277)
        assert e.value.error_type is ErrorType.INVALID_RESPONSE
        assert len(seen) == 1
        assert client.cache.get(key) is None  # the rejected entry is gone, the failure not stored

    def test_a_failing_backend_degrades_to_a_miss_without_raising(self, caplog) -> None:
        class Broken(NullCache):
            backend = "broken"

            def get(self, key: str):
                raise RuntimeError("cache service down")

            def set(self, key: str, value: bytes, ttl: float) -> None:
                raise RuntimeError("cache service down")

        client, seen = _client(_serve_fixtures, cache=Broken())
        with caplog.at_level(logging.WARNING, logger="cadastral_api.client.api_client"):
            client.get_parcel_info("6564741")
            client.get_parcel_info("6564741")
        assert len(seen) == 2
        assert caplog.text.count("Response cache get failed") == 1  # logged once
        assert caplog.text.count("Response cache set failed") == 1


class TestConfiguration:
    def test_from_config_reads_the_environment(self, monkeypatch) -> None:
        monkeypatch.setenv("CADASTRAL_CACHE", "off")
        assert isinstance(from_config(), NullCache)
        monkeypatch.setenv("CADASTRAL_CACHE", "memory")
        monkeypatch.setenv("CADASTRAL_CACHE_MEMORY_MB", "2")
        cache = from_config()
        assert isinstance(cache, MemoryCache) and cache.max_bytes == 2 * 1024 * 1024
        monkeypatch.delenv("CADASTRAL_CACHE")
        assert isinstance(from_config(), MemoryCache)

    def test_explicit_values_win_over_the_environment(self, monkeypatch) -> None:
        monkeypatch.setenv("CADASTRAL_CACHE", "off")
        assert isinstance(from_config("memory", memory_mb=1), MemoryCache)
        client = CadastralAPIClient(base_url="http://mock", cache="memory")
        assert isinstance(client.cache, MemoryCache)

    def test_backends_of_later_phases_fall_back_to_memory_with_a_warning(self, caplog) -> None:
        with caplog.at_level(logging.WARNING, logger="cadastral_api.cache"):
            assert isinstance(from_config("disk"), MemoryCache)
            assert isinstance(from_config("redis://localhost:6379/0"), MemoryCache)
        assert "not available in this version" in caplog.text

    def test_unknown_values_are_rejected(self, monkeypatch) -> None:
        with pytest.raises(ValueError):
            from_config("memroy")
        monkeypatch.setenv("CADASTRAL_CACHE_MEMORY_MB", "lots")
        with pytest.raises(ValueError):
            from_config("memory")


def test_fetched_is_a_plain_value() -> None:
    fetched = Fetched({"a": 1}, "2026-09-16T12:00:00+00:00", from_cache=True)
    assert fetched.body == {"a": 1} and fetched.from_cache
