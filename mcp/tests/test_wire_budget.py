"""The wire budget of a tool result (response-cache specification, section 11).

A result is measured as the client receives it, the text block plus the
structured copy, and a paged window that does not fit is cut to the largest
prefix that does; only a single record that does not fit on its own is
refused. ``MCP_STRUCTURED_OUTPUT=off`` registers text-only tools.
"""

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pydantic_core
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "api" / "src"))

from cadastral_api.models.entities import MunicipalitySearchResult  # noqa: E402

_TOOLS_PATH = REPO / "mcp" / "src" / "cadastral_mcp" / "tools.py"
_spec = importlib.util.spec_from_file_location("cadastral_mcp_tools_budget", _TOOLS_PATH)
_tools = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tools)
CadastralTools = _tools.CadastralTools
wire_size = _tools.wire_size
fit_window = _tools.fit_window
DoesNotFitError = _tools.DoesNotFitError


# --- wire_size -----------------------------------------------------------------


def test_wire_size_counts_the_pretty_text_and_the_compact_structured_copy() -> None:
    payload = {"name": "Šibenik", "rows": [1, 2, 3], "when": None}
    pretty = len(pydantic_core.to_json(payload, indent=2))
    compact = len(pydantic_core.to_json(payload))
    assert pretty > compact
    assert wire_size(payload) == pretty + compact
    assert wire_size(payload, structured=False) == pretty


def test_wire_size_serialises_what_the_sdk_would() -> None:
    from datetime import date

    payload = {"day": date(2026, 9, 29), "path": Path("x")}  # fallback=str, as the SDK does
    assert wire_size(payload) > 0


# --- fit_window ----------------------------------------------------------------


def _rows(n: int) -> list[dict]:
    return [{"id": i, "text": "x" * 100} for i in range(n)]


def _build_for(total: int):
    rows = _rows(total)

    def build(limit: int | None) -> dict:
        window = rows[: limit if limit is not None else total]
        return {"rows": window, "page": CadastralTools._page(0, limit, total, len(window))}

    return build


def test_a_window_within_the_budget_is_returned_as_built() -> None:
    build = _build_for(10)
    result = fit_window(build, None, budget=10_000_000)
    assert result["page"]["returned"] == 10
    assert "requested_limit" not in result["page"]


def test_no_limit_means_as_many_as_fit() -> None:
    build = _build_for(1000)
    whole = wire_size(build(None))
    budget = whole // 4
    result = fit_window(build, None, budget=budget)
    page = result["page"]
    assert 0 < page["returned"] < 1000
    assert wire_size(result) <= budget
    assert page["limit"] == page["returned"]
    assert page["requested_limit"] is None
    assert page["truncated"] is True and page["next_offset"] == page["returned"]
    # The cut is proportional, not a quarter of the window: near the budget.
    assert wire_size(result) > budget * 0.7


def test_an_explicit_limit_over_the_budget_is_reduced_and_reported() -> None:
    build = _build_for(1000)
    budget = wire_size(build(100))
    result = fit_window(build, 500, budget=budget)
    assert result["page"]["limit"] < 500
    assert result["page"]["requested_limit"] == 500
    assert wire_size(result) <= budget


def test_a_single_record_that_does_not_fit_is_does_not_fit() -> None:
    build = _build_for(10)
    with pytest.raises(DoesNotFitError) as excinfo:
        fit_window(build, None, budget=50)
    assert excinfo.value.result["page"]["returned"] == 1
    assert excinfo.value.size > 50 and excinfo.value.budget == 50


def test_fit_window_builds_at_most_three_times() -> None:
    calls: list[int | None] = []
    rows = _rows(1000)

    def build(limit: int | None) -> dict:
        calls.append(limit)
        window = rows[: limit if limit is not None else 1000]
        return {"rows": window, "page": CadastralTools._page(0, limit, 1000, len(window))}

    fit_window(build, None, budget=wire_size(build(None)) // 3)
    assert 2 <= len(calls) - 1 <= 3  # the first build plus one cut and at most one retry


def test_a_result_without_a_page_block_is_refused_when_over_budget() -> None:
    def build(limit: int | None) -> dict:
        return {"blob": "x" * 1000}

    with pytest.raises(DoesNotFitError):
        fit_window(build, None, budget=100)


# --- a list tool under the budget ----------------------------------------------


class _FakeMunicipalities:
    def __init__(self, n: int) -> None:
        self.all = [
            MunicipalitySearchResult.model_validate({
                "key1": str(2000 + i),
                "value1": f"{300000 + i} K.O. MJESTO {i:04d}",
                "key2": str(300000 + i),
                "value2": "114",
                "value3": "116",
                "displayValue1": f"{300000 + i} K.O. MJESTO {i:04d}, ZADAR, PUK ZADAR",
            })
            for i in range(n)
        ]

    def find_municipality(self, search_term=None, office_id=None, department_id=None):
        return self.all


def test_list_municipalities_with_no_limit_returns_as_many_as_fit() -> None:
    client = _FakeMunicipalities(3000)
    # Under the default budget the whole list (about 1 MB on the wire, like
    # the real 3,300 municipalities) is already cut; an unbounded budget
    # measures it whole.
    cut = asyncio.run(CadastralTools(client).list_municipalities(limit=None))
    assert 0 < cut["page"]["returned"] < 3000 and cut["page"]["truncated"] is True
    unbounded = CadastralTools(client, result_budget_bytes=10**9)
    everything = asyncio.run(unbounded.list_municipalities(limit=None))
    assert everything["page"]["returned"] == 3000
    budget = wire_size(everything) // 10
    tools = CadastralTools(client, result_budget_bytes=budget)
    res = asyncio.run(tools.list_municipalities(limit=None))
    page = res["page"]
    assert 0 < page["returned"] < 3000 and page["total"] == 3000
    assert page["requested_limit"] is None and page["limit"] == page["returned"]
    assert page["truncated"] is True and page["next_offset"] == page["returned"]
    assert wire_size(res) <= budget
    # With the structured copy off the same budget holds more records.
    text_only = CadastralTools(client, result_budget_bytes=budget, structured_output=False)
    assert asyncio.run(text_only.list_municipalities(limit=None))["page"]["returned"] > (
        page["returned"]
    )


# --- configuration and registration -------------------------------------------


def test_result_budget_is_read_from_the_environment(monkeypatch) -> None:
    from cadastral_mcp import config as config_module

    monkeypatch.setenv("MCP_RESULT_BUDGET_BYTES", "123456")
    monkeypatch.setenv("MCP_STRUCTURED_OUTPUT", "off")
    cfg = config_module.MCPConfig(
        result_budget_bytes=config_module._result_budget_from_env(),
        structured_output=False,
    )
    assert cfg.result_budget_bytes == 123456 and cfg.structured_output is False
    monkeypatch.setenv("MCP_RESULT_BUDGET_BYTES", "not a number")
    assert config_module._result_budget_from_env() == config_module.DEFAULT_RESULT_BUDGET_BYTES
    monkeypatch.setenv("MCP_RESULT_BUDGET_BYTES", "0")
    assert config_module._result_budget_from_env() == config_module.DEFAULT_RESULT_BUDGET_BYTES
    monkeypatch.delenv("MCP_RESULT_BUDGET_BYTES")
    assert config_module._result_budget_from_env() == 800_000
    assert config_module.DEFAULT_RESULT_BUDGET_BYTES == _tools.DEFAULT_RESULT_BUDGET_BYTES


def _tools_of(structured: bool):
    from cadastral_mcp import config as config_module
    from cadastral_mcp.server import create_mcp_server

    original = config_module.config.structured_output
    config_module.config.structured_output = structured
    try:
        mcp = create_mcp_server()
    finally:
        config_module.config.structured_output = original
    return {t.name: t for t in asyncio.run(mcp.list_tools())}


def test_structured_output_off_registers_text_only_tools() -> None:
    on = _tools_of(True)
    assert on["get_parcel"].output_schema is not None
    off = _tools_of(False)
    assert set(off) == set(on)
    assert all(t.output_schema is None for t in off.values())
    assert json.dumps(off["get_parcel"].input_schema) == json.dumps(on["get_parcel"].input_schema)
