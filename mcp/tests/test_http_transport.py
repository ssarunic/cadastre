"""The HTTP transport serves the MCP protocol, and slow calls do not block each other.

The app from ``create_http_app`` runs on a free port in a background thread;
the SDK's streamable HTTP client talks to it. The API client behind the
server answers from fixtures through a ``MockTransport`` that sleeps, so
two tool calls issued together finish in one sleep when the handlers run
in worker threads and in two when they block the event loop.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "api" / "src"))
sys.path.insert(0, str(REPO / "mcp" / "src"))

from cadastral_api import CadastralAPIClient  # noqa: E402
from mcp.client.session import ClientSession  # noqa: E402
from mcp.client.streamable_http import streamable_http_client  # noqa: E402

from cadastral_mcp import http_server, server  # noqa: E402

FIXTURES = REPO / "api" / "src" / "cadastral_api" / "tests" / "fixtures"
FIXTURE_FOR_PATH = {
    "/search-cad-parcels/offices": "offices.json",
    "/search-cad-parcels/municipalities": "municipalities_savar.json",
}
UPSTREAM_DELAY = 0.4


@pytest.fixture
def slow_upstream(monkeypatch, tmp_path) -> None:
    """The server's API client answers from fixtures after a sleep."""

    def serve(request: httpx.Request) -> httpx.Response:
        time.sleep(UPSTREAM_DELAY)
        body = json.loads((FIXTURES / FIXTURE_FOR_PATH[request.url.path]).read_text("utf-8"))
        return httpx.Response(200, json=body)

    def make_client(**kwargs):
        kwargs.update(rate_limit=0, cache="off", cache_dir=tmp_path)
        client = CadastralAPIClient(**kwargs)
        client.client = httpx.Client(base_url="http://mock", transport=httpx.MockTransport(serve))
        return client

    monkeypatch.setattr(server, "CadastralAPIClient", make_client)


@pytest.fixture
def base_url(slow_upstream, run_server) -> str:
    return run_server(
        lambda _url: http_server.create_http_app(server.create_mcp_server(), "127.0.0.1")
    )


async def _session_call(url: str, calls: list[tuple[str, dict]]) -> tuple[list, list, float]:
    async with streamable_http_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            start = time.monotonic()
            results = await asyncio.gather(
                *(session.call_tool(name, args) for name, args in calls)
            )
            return tools.tools, list(results), time.monotonic() - start


def test_health(base_url) -> None:
    body = httpx.get(f"{base_url}/health").json()
    assert body["status"] == "ok"
    assert body["mcp_path"] == "/mcp"


def test_tools_are_served_over_http(base_url) -> None:
    tools, results, _ = asyncio.run(
        _session_call(f"{base_url}/mcp", [("resolve_municipality", {"name_or_code": "SAVAR"})])
    )
    assert "get_lr_unit" in {tool.name for tool in tools}
    (result,) = results
    assert not result.is_error, result.content
    assert result.structured_content["code"] == "334979"


def test_concurrent_calls_overlap(base_url) -> None:
    calls = [("list_cadastral_offices", {}), ("resolve_municipality", {"name_or_code": "SAVAR"})]
    _, results, elapsed = asyncio.run(_session_call(f"{base_url}/mcp", calls))
    assert all(not result.is_error for result in results)
    # Two upstream sleeps in sequence would take 2 x UPSTREAM_DELAY.
    assert elapsed < 1.6 * UPSTREAM_DELAY, elapsed
