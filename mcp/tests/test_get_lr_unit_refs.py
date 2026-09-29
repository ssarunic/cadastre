"""get_lr_unit takes a list of references of three kinds and returns one entry each.

Loads tools.py standalone (no MCP SDK needed) and drives it with a fake client
that serves the redacted 449/21277 unit for any reference.
"""

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "api" / "src"))

from cadastral_api.exceptions import CadastralAPIError, ErrorType  # noqa: E402
from cadastral_api.models.entities import LandRegistryUnitDetailed  # noqa: E402

_TOOLS_PATH = REPO / "mcp" / "src" / "cadastral_mcp" / "tools.py"
_spec = importlib.util.spec_from_file_location("cadastral_mcp_tools_refs", _TOOLS_PATH)
_tools = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tools)
CadastralTools = _tools.CadastralTools
LRUnitRef = _tools.LRUnitRef

FIXTURE = REPO / "api" / "src" / "cadastral_api" / "tests" / "fixtures" / "lr_unit_lrparcels.json"


class _FakeClient:
    """Serves the fixture unit (449 in main book 21277) and records the calls."""

    def __init__(self) -> None:
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.unit = LandRegistryUnitDetailed.model_validate(
            raw[0] if isinstance(raw, list) else raw
        )
        self.calls: list[tuple] = []

    def get_lr_unit_detailed(
        self,
        unit_number,
        main_book_id=None,
        main_book_name=None,
        historical_overview=False,
        **kwargs,
    ):
        self.calls.append(("unit", unit_number, main_book_id, main_book_name))
        if unit_number == "999999":
            raise CadastralAPIError(
                ErrorType.LR_UNIT_NOT_FOUND, details={"lr_unit_number": unit_number}
            )
        return self.unit

    def get_lr_unit_from_parcel(
        self, parcel_number, municipality, historical_overview=False, **kwargs
    ):
        self.calls.append(("parcel", parcel_number, municipality))
        return self.unit

    def resolve_municipality_reg_num(self, name_or_code):
        if not str(name_or_code).isdigit():
            raise AssertionError("codes must not be resolved through the API")
        return str(name_or_code)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def client() -> _FakeClient:
    return _FakeClient()


@pytest.fixture
def tools(client) -> "CadastralTools":
    return CadastralTools(client)


def test_reference_validation() -> None:
    LRUnitRef(lr_unit_number="449", main_book_id=21277)
    # Numbers typed as numbers are accepted and normalised to strings.
    assert LRUnitRef(lr_unit_number=449, main_book_id=21277).lr_unit_number == "449"
    assert _tools.ParcelRef(parcel_id="6564741").parcel_id == 6564741
    LRUnitRef(lr_unit_number="449", main_book_name="SAVAR")
    LRUnitRef(parcel_number="1122/1", municipality="334979")
    for bad in (
        {},
        {"lr_unit_number": "449"},
        {"parcel_number": "1122/1"},
        {"lr_unit_number": "449", "main_book_id": 21277, "parcel_number": "1", "municipality": "x"},
    ):
        with pytest.raises(ValueError):
            LRUnitRef.model_validate(bad)


def test_single_direct_reference(tools, client) -> None:
    res = _run(tools.get_lr_unit([{"lr_unit_number": "449", "main_book_id": 21277}]))
    assert res["total"] == 1 and res["unique"] == 1 and res["successful"] == 1
    entry = res["results"][0]
    assert entry["status"] == "success"
    assert (entry["lr_unit_number"], entry["main_book_id"]) == ("449", 21277)
    assert entry["ref"] == {"lr_unit_number": "449", "main_book_id": 21277}
    assert entry["data"]["total_owners"] == 4  # default detail is "ownership"
    assert client.calls == [("unit", "449", 21277, None)]


def test_parcel_reference_resolves_through_the_parcel(tools, client) -> None:
    res = _run(
        tools.get_lr_unit([{"parcel_number": "1122/1", "municipality": "334979"}], "summary")
    )
    entry = res["results"][0]
    assert entry["status"] == "success"
    assert entry["lr_unit_derived_from_links"] is False
    assert "owners" not in entry["data"] and entry["data"]["summary"]["num_owners"] == 4
    assert client.calls == [("parcel", "1122/1", "334979")]


def test_main_book_name_reference_is_passed_to_the_client(tools, client) -> None:
    res = _run(tools.get_lr_unit([{"lr_unit_number": "449", "main_book_name": "SAVAR"}]))
    assert res["results"][0]["status"] == "success"
    assert client.calls == [("unit", "449", None, "SAVAR")]


def test_same_unit_is_fetched_once_and_later_entries_point_back(tools, client) -> None:
    res = _run(
        tools.get_lr_unit(
            [
                {"lr_unit_number": "449", "main_book_id": 21277},
                {"lr_unit_number": "449", "main_book_id": 21277},  # direct repeat: no request
                {"parcel_number": "1122/1", "municipality": "334979"},  # resolves to the same
                {"lr_unit_number": "449", "main_book_name": "savar"},  # resolves to the same
            ]
        )
    )
    statuses = [r["status"] for r in res["results"]]
    assert statuses == ["success", "duplicate", "duplicate", "duplicate"]
    assert all(r["same_unit_as"] == 0 for r in res["results"][1:])
    assert all("data" not in r for r in res["results"][1:])
    assert res["total"] == 4 and res["unique"] == 1 and res["successful"] == 1
    assert res["duplicates"] == 3 and res["failed"] == 0
    assert res["successful"] + res["failed"] + res["duplicates"] == res["total"]
    # The direct repeat cost nothing; the other two had to be resolved first.
    assert client.calls == [
        ("unit", "449", 21277, None),
        ("parcel", "1122/1", "334979"),
        ("unit", "449", None, "savar"),
    ]


def test_failures_are_per_reference(tools) -> None:
    res = _run(
        tools.get_lr_unit(
            [
                {"lr_unit_number": "999999", "main_book_id": 21277},
                {"lr_unit_number": "449"},  # incomplete reference
                {"lr_unit_number": "449", "main_book_id": 21277},
            ]
        )
    )
    statuses = [r["status"] for r in res["results"]]
    assert statuses == ["error", "error", "success"]
    assert "999999" in res["results"][0]["error"]
    assert "main_book_id or main_book_name" in res["results"][1]["error"]
    assert res["failed"] == 2 and res["successful"] == 1 and res["duplicates"] == 0


def test_invalid_detail_and_empty_list_are_refused(tools) -> None:
    with pytest.raises(ValueError):
        _run(tools.get_lr_unit([{"lr_unit_number": "449", "main_book_id": 21277}], "bogus"))
    with pytest.raises(ValueError):
        _run(tools.get_lr_unit([]))


def test_historical_overview_and_paging_reach_the_client(tools, client) -> None:
    result = _run(
        tools.get_lr_unit(
            [{"lr_unit_number": "449", "main_book_id": 21277}],
            historical_overview=True,
            offset=1,
            limit=2,
        )
    )
    assert client.calls == [("unit", "449", 21277, None)]
    entry = result["results"][0]
    assert entry["status"] == "success"
    assert entry["data"]["page"] == {
        "offset": 1, "limit": 2, "total": 4, "returned": 2, "truncated": True, "next_offset": 3
    }


def test_historical_overview_is_passed_to_the_client() -> None:
    class _Recording(_FakeClient):
        def get_lr_unit_detailed(self, unit_number, main_book_id=None, **kwargs):
            self.calls.append(kwargs)
            return self.unit

    client = _Recording()
    _run(
        CadastralTools(client).get_lr_unit(
            [{"lr_unit_number": "449", "main_book_id": 21277}], historical_overview=True
        )
    )
    assert client.calls == [
        {"main_book_name": None, "historical_overview": True, "refresh": False}
    ]


def test_owners_limit_is_a_synonym_of_limit(tools) -> None:
    ref = {"lr_unit_number": "449", "main_book_id": 21277}
    by_old = _run(tools.get_lr_unit([ref], owners_limit=2))
    by_new = _run(tools.get_lr_unit([ref], limit=2))
    assert by_old["results"][0]["data"]["owners"] == by_new["results"][0]["data"]["owners"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"limit": 0},
        {"offset": -1},
        {"detail": "sheets"},
        {"owner_name": " "},
        {"owner_name": "x", "detail": "parcels"},
    ],
)
def test_bad_paging_or_detail_is_rejected(tools, kwargs) -> None:
    with pytest.raises(ValueError):
        _run(tools.get_lr_unit([{"lr_unit_number": "449", "main_book_id": 21277}], **kwargs))


def test_owner_name_finds_one_person_in_a_unit(tools) -> None:
    ref = {"lr_unit_number": "449", "main_book_id": 21277}
    res = _run(tools.get_lr_unit([ref], owner_name="vlasnik 114"))
    assert res["owner_name"] == "vlasnik 114"
    data = res["results"][0]["data"]
    assert [row["name"] for row in data["owners"]] == ["Vlasnik 114"]
    assert data["matching_owners"] == 1 and data["total_owners"] == 4
    missing = _run(tools.get_lr_unit([ref], owner_name="nobody"))["results"][0]
    assert missing["status"] == "success" and missing["data"]["matching_owners"] == 0
