"""Paging through a record costs one upstream fetch, and every page says when that was.

``CadastralTools`` over a real ``CadastralAPIClient`` on a recording
``MockTransport`` (the mock server keeps no request log): five ``get_lr_unit``
calls with different windows make one ``/lr/lr-unit`` request, ``refresh``
makes another, and the ``page`` block carries ``fetched_at``.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import httpx
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "api" / "src"))

from cadastral_api import CadastralAPIClient  # noqa: E402

_TOOLS_PATH = REPO / "mcp" / "src" / "cadastral_mcp" / "tools.py"
_spec = importlib.util.spec_from_file_location("cadastral_mcp_tools_cache", _TOOLS_PATH)
_tools = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tools)
CadastralTools = _tools.CadastralTools

FIXTURES = REPO / "api" / "src" / "cadastral_api" / "tests" / "fixtures"
_FIXTURE_FOR_PATH = {
    "/lr/lr-unit": "lr_unit_lrparcels.json",
    "/cad/parcel-info": "parcel_info_direct.json",
}


@pytest.fixture
def tools(tmp_path) -> tuple[CadastralTools, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def serve(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        body = json.loads((FIXTURES / _FIXTURE_FOR_PATH[request.url.path]).read_text("utf-8"))
        return httpx.Response(200, json=body)

    client = CadastralAPIClient(base_url="http://mock", rate_limit=0, cache_dir=tmp_path)
    client.client = httpx.Client(base_url="http://mock", transport=httpx.MockTransport(serve))
    return CadastralTools(client), seen


def _run(coro):
    return asyncio.run(coro)


def test_five_pages_of_one_unit_make_one_request(tools) -> None:
    handler, seen = tools
    ref = {"lr_unit_number": "449", "main_book_id": 21277}
    pages = [
        _run(handler.get_lr_unit([ref], detail="ownership", offset=offset, limit=1))
        for offset in range(4)
    ]
    pages.append(_run(handler.get_lr_unit([ref], detail="parcels")))
    assert [r.url.path for r in seen] == ["/lr/lr-unit"]
    windows = [p["results"][0]["data"]["page"] for p in pages[:4]]
    assert [w["offset"] for w in windows] == [0, 1, 2, 3]
    assert all(w["returned"] == 1 and w["total"] == 4 for w in windows)
    fetched = {p["results"][0]["data"]["page"]["fetched_at"] for p in pages}
    retrieved_at = pages[0]["results"][0]["data"]["provenance"]["retrieved_at"]
    assert fetched == {retrieved_at}


def test_refresh_reads_the_unit_again(tools) -> None:
    handler, seen = tools
    ref = {"lr_unit_number": "449", "main_book_id": 21277}
    _run(handler.get_lr_unit([ref]))
    _run(handler.get_lr_unit([ref]))
    assert len(seen) == 1
    _run(handler.get_lr_unit([ref], refresh=True))
    assert len(seen) == 2


def test_parcel_pages_carry_fetched_at_and_share_one_request(tools) -> None:
    handler, seen = tools
    ref = {"parcel_id": "6566217"}
    first = _run(handler.get_parcel([ref], limit=1))
    second = _run(handler.get_parcel([ref], offset=1, limit=1))
    assert [r.url.path for r in seen] == ["/cad/parcel-info"]
    entries = [first["results"][0], second["results"][0]]
    assert all(e["status"] == "success" for e in entries)
    assert entries[0]["page"]["fetched_at"] == entries[0]["provenance"]["retrieved_at"]
    assert entries[0]["page"]["fetched_at"] == entries[1]["page"]["fetched_at"]
    _run(handler.get_parcel([ref], refresh=True))
    assert len(seen) == 2
