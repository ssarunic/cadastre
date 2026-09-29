"""F4: MCP LR-unit response shaping (detail levels + owners_limit).

Loads tools.py standalone (no MCP SDK needed) and shapes a real LR unit
(449/21277, redacted owners) via the pure _shape_lr_unit classmethod.
"""

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "api" / "src"))

from cadastral_api.models.entities import LandRegistryUnitDetailed  # noqa: E402

_TOOLS_PATH = REPO / "mcp" / "src" / "cadastral_mcp" / "tools.py"
_spec = importlib.util.spec_from_file_location("cadastral_mcp_tools_shaping", _TOOLS_PATH)
_tools = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tools)
CadastralTools = _tools.CadastralTools

FIXTURE = REPO / "api" / "src" / "cadastral_api" / "tests" / "fixtures" / "lr_unit_lrparcels.json"


@pytest.fixture
def unit() -> LandRegistryUnitDetailed:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return LandRegistryUnitDetailed.model_validate(raw[0] if isinstance(raw, list) else raw)


def test_full_includes_all_sheets(unit) -> None:
    shaped = CadastralTools._shape_lr_unit(unit, "full", None)
    assert "ownership_sheet_b" in shaped
    assert "encumbrance_sheet_c" in shaped
    assert shaped["summary"]["total_parcels"] == 1


def test_summary_is_minimal(unit) -> None:
    shaped = CadastralTools._shape_lr_unit(unit, "summary", None)
    assert "ownership_sheet_b" not in shaped
    assert "owners" not in shaped
    assert shaped["summary"]["num_owners"] == 4


def test_ownership_returns_tagged_owners_with_structured_shares(unit) -> None:
    shaped = CadastralTools._shape_lr_unit(unit, "ownership", None)
    assert "ownership_sheet_b" not in shaped  # raw sheets dropped
    assert "encumbrance_sheet_c" not in shaped
    assert shaped["in_land_registry"] is True
    assert shaped["total_owners"] == 4
    assert shaped["owners_truncated"] is False
    owners = shaped["owners"]
    assert len(owners) == 4
    assert all(o["register"] == "land_registry" for o in owners)
    assert all(o["name_normalized"] for o in owners)
    # Structured share, not a description string.
    assert all(isinstance(o["share"], dict) and "decimal" in o["share"] for o in owners)


def test_owners_limit_truncates_and_reports_total(unit) -> None:
    shaped = CadastralTools._shape_lr_unit(unit, "ownership", 2)
    assert len(shaped["owners"]) == 2
    assert shaped["total_owners"] == 4
    assert shaped["owners_truncated"] is True


def test_invalid_detail_raises(unit) -> None:
    with pytest.raises(ValueError):
        CadastralTools._shape_lr_unit(unit, "bogus", None)


CONDOMINIUM = (
    REPO / "api" / "src" / "cadastral_api" / "tests" / "fixtures" / "lr_unit_condominium.json"
)


@pytest.fixture
def condominium() -> LandRegistryUnitDetailed:
    raw = json.loads(CONDOMINIUM.read_text(encoding="utf-8"))
    return LandRegistryUnitDetailed.model_validate(raw[0] if isinstance(raw, list) else raw)


class _UnitClient:
    """Serves one unit whatever the reference, under the number asked for."""

    def __init__(self, unit: LandRegistryUnitDetailed) -> None:
        self.unit = unit

    def get_lr_unit_detailed(self, unit_number, main_book_id=None, **kwargs):
        if str(unit_number) == str(self.unit.lr_unit_number):
            return self.unit
        return self.unit.model_copy(update={"lr_unit_number": str(unit_number)})


def _read(unit, detail, limit, offset=0, *, budget, **kwargs) -> dict:
    """The entry get_lr_unit returns for the unit under a wire budget of ``budget`` bytes."""
    tools = CadastralTools(_UnitClient(unit), result_budget_bytes=budget)
    ref = {"lr_unit_number": str(unit.lr_unit_number), "main_book_id": unit.main_book_id}
    return asyncio.run(
        tools.get_lr_unit([ref], detail=detail, limit=limit, offset=offset, **kwargs)
    )["results"][0]


def _dumped_owners(shaped: dict) -> int:
    """Owner records left in a full dump, sub-shares included."""
    def walk(shares) -> int:
        count = 0
        for share in shares:
            count += len(share.get("owners") or [])
            nested = share.get("sub_shares_and_entries") or []
            count += walk([item for item in nested if isinstance(item, dict) and "owners" in item])
        return count

    return walk(shaped["ownership_sheet_b"]["lr_unit_shares"])


def test_full_reports_owner_count_when_nothing_is_capped(unit) -> None:
    shaped = CadastralTools._shape_lr_unit(unit, "full", None)
    assert shaped["total_owners"] == 4
    assert shaped["owners_truncated"] is False
    assert _dumped_owners(shaped) == 4


def test_owners_limit_applies_to_full_not_only_ownership(unit) -> None:
    shaped = CadastralTools._shape_lr_unit(unit, "full", 2)
    assert _dumped_owners(shaped) == 2
    assert shaped["total_owners"] == 4
    assert shaped["owners_truncated"] is True
    # The other sheets are still there; only sheet B was cut off.
    assert "encumbrance_sheet_c" in shaped
    assert "possessory_sheet_a1" in shaped


def test_full_is_paged_by_share_and_drops_the_shares_outside_the_window(condominium) -> None:
    # Emptying the owners is not enough: each share carries its own description
    # and registration entry, so this unit's 85 emptied shares still serialise
    # to 135,000 characters. Sheet B is cut to the window of shares instead.
    dump = condominium.model_dump(mode="json")
    before = dump["ownership_sheet_b"]["lr_unit_shares"]
    total, _, returned, omitted = CadastralTools._window_shares(dump, 0, 5)
    shares = dump["ownership_sheet_b"]["lr_unit_shares"]
    assert (total, returned) == (85, 5)
    assert len(shares) == 5 < len(before)
    assert omitted == CadastralTools._count_shares(before) - CadastralTools._count_shares(shares)



def test_a_full_dump_whose_bulk_is_another_sheet_is_refused_naming_it(condominium) -> None:
    # This unit's encumbrances alone overrun the budget, so cutting the shares
    # window cannot rescue the full dump; the refusal names the sheet at fault
    # and the per-sheet levels, and does not suggest a share cap.
    entry = _read(condominium, "full", 5, budget=100_000)
    assert entry["status"] == "error"
    assert entry["error_type"] == "response_too_large"
    message = entry["error"]
    assert condominium.lr_unit_number in message
    assert "encumbrance_sheet_c" in message
    assert "owners_limit" not in message
    assert 'detail="ownership"' in message
    assert 'detail="encumbrances"' in message and 'detail="shares"' in message
    # The smaller views still work for the same unit under the same budget.
    assert _read(condominium, "ownership", 3, budget=100_000)["data"]["owners_truncated"]
    assert _read(condominium, "summary", None, budget=100_000)["data"]["summary"]



def test_a_full_dump_within_the_budget_comes_back_whole(condominium) -> None:
    # Under the default budget the condominium's full dump (about 600 kB on
    # the wire) is returned whole; the old 50,000-character ceiling is gone.
    entry = _read(condominium, "full", None, budget=_tools.DEFAULT_RESULT_BUDGET_BYTES)
    assert entry["status"] == "success"
    assert entry["data"]["page"]["returned"] == 85
    assert "requested_limit" not in entry["data"]["page"]


def test_every_level_names_the_unit_and_its_office(unit) -> None:
    for detail in CadastralTools.VALID_DETAIL:
        shaped = CadastralTools._shape_lr_unit(unit, detail, 3)
        assert shaped["lr_unit_number"] == unit.lr_unit_number
        assert shaped["institution_id"] == unit.institution_id
        if detail != "summary":
            assert shaped["page"]["total"] >= shaped["page"]["returned"]


def test_ownership_pages_with_offset(unit) -> None:
    first = CadastralTools._shape_lr_unit(unit, "ownership", 3, 0)
    assert first["page"] == {
        "offset": 0, "limit": 3, "total": 4, "returned": 3, "truncated": True, "next_offset": 3
    }
    rest = CadastralTools._shape_lr_unit(unit, "ownership", 3, first["page"]["next_offset"])
    assert len(rest["owners"]) == 1
    assert rest["owners_truncated"] is False
    assert rest["page"]["truncated"] is False
    names = [o["name"] for o in first["owners"]] + [o["name"] for o in rest["owners"]]
    assert names == [o["name"] for o in unit.ownership_sheet_b.owner_rows()]


def test_full_pages_shares_with_offset_and_loses_none(condominium) -> None:
    pages, owners, offset = [], 0, 0
    while True:
        dump = condominium.model_dump(mode="json")
        total, _, returned, omitted = CadastralTools._window_shares(dump, offset, 40)
        pages.append(returned)
        owners += _dumped_owners(dump)
        assert omitted > 0
        offset += returned
        if offset >= total:
            break
    assert pages == [40, 40, 5]
    assert owners == 103  # every owner record of every share, once


def test_paging_reaches_a_trailing_share_without_owners() -> None:
    # A share that holds only annotations is a page item like any other: with
    # limit=1 the first page says there is more, and the second page is it.
    def dump() -> dict:
        return {"ownership_sheet_b": {"lr_unit_shares": [
            {"order_number": "1", "owners": [{"name": "A"}], "sub_shares_and_entries": []},
            {"order_number": "2", "owners": [], "sub_shares_and_entries": [{"entry": "x"}]},
        ]}}

    first = dump()
    assert CadastralTools._window_shares(first, 0, 1) == (2, 2, 1, 1)
    page = CadastralTools._page(0, 1, 2, 1)
    assert page["truncated"] is True and page["next_offset"] == 1
    second = dump()
    assert CadastralTools._window_shares(second, page["next_offset"], 1) == (2, 2, 1, 1)
    assert second["ownership_sheet_b"]["lr_unit_shares"][0]["order_number"] == "2"



def test_shares_level_is_raw_sheet_b_paged(condominium) -> None:
    first = CadastralTools._shape_lr_unit(condominium, "shares", 10, 0)
    sheet = first["ownership_sheet_b"]
    assert len(sheet["lr_unit_shares"]) == 10
    assert sheet["lr_entries"]  # the sheet-level B entries come along
    share = sheet["lr_unit_shares"][0]
    assert {"status", "sub_shares_and_entries", "owners"} <= set(share)  # raw, not flattened
    assert first["total_shares"] == 85
    assert first["total_owners"] == 103
    assert first["owners_truncated"] is True
    assert first["page"]["next_offset"] == 10
    assert "encumbrance_sheet_c" not in first and "possessory_sheet_a1" not in first
    # The pages cover the whole sheet exactly once.
    seen, offset = [], 0
    while True:
        page = CadastralTools._shape_lr_unit(condominium, "shares", 10, offset)
        seen += [s["order_number"] for s in page["ownership_sheet_b"]["lr_unit_shares"]]
        if not page["page"]["truncated"]:
            break
        offset = page["page"]["next_offset"]
    assert seen == [s.order_number for s in condominium.ownership_sheet_b.lr_unit_shares]


def test_full_window_past_the_end_is_empty_not_an_error(unit) -> None:
    shaped = CadastralTools._shape_lr_unit(unit, "full", 2, 10)
    assert _dumped_owners(shaped) == 0
    assert shaped["page"]["returned"] == 0
    assert shaped["page"]["truncated"] is False


def test_parcels_level_is_sheet_a_paged(encumbered) -> None:
    shaped = CadastralTools._shape_lr_unit(encumbered, "parcels", 3, 0)
    assert "ownership_sheet_b" not in shaped and "owners" not in shaped
    assert shaped["total_parcels"] == 7
    assert len(shaped["parcels"]) == 3
    assert shaped["page"]["next_offset"] == 3
    assert shaped["sheet_a1_source_key"] in ("lrParcels", "cadParcels")
    assert "sheet_a2_entries" in shaped
    numbers = [p["parcel_number"] for p in shaped["parcels"]]
    assert numbers == encumbered.possessory_sheet_a1.parcel_numbers()[:3]


def test_encumbrances_level_is_sheet_c_paged(condominium) -> None:
    # The condominium's sheet C alone overruns the full-dump ceiling; paged
    # by entry group it comes back a window at a time.
    groups = condominium.encumbrance_sheet_c.lr_entry_groups
    first = CadastralTools._shape_lr_unit(condominium, "encumbrances", 5, 0)
    assert first["total_entry_groups"] == len(groups) == 30
    assert len(first["entry_groups"]) == 5
    assert first["page"]["truncated"] is True
    assert "ownership_sheet_b" not in first and "owners" not in first
    last = CadastralTools._shape_lr_unit(condominium, "encumbrances", 5, 25)
    assert len(last["entry_groups"]) == 5
    assert last["page"]["truncated"] is False



def test_a_window_over_the_budget_is_cut_to_what_fits(condominium) -> None:
    # No limit means as many as fit: the shares window (about 460 kB on the
    # wire whole) is cut to a prefix within budget, and the page block says
    # where to continue and what was asked for.
    budget = 100_000
    data = _read(condominium, "shares", None, budget=budget)["data"]
    page = data["page"]
    assert 0 < page["returned"] < 85
    assert page["limit"] == page["returned"] and page["requested_limit"] is None
    assert page["truncated"] is True and page["next_offset"] == page["returned"]
    assert _tools.wire_size(data) <= budget
    # An explicit limit that does not fit is reduced the same way and reported.
    page = _read(condominium, "shares", 50, budget=budget)["data"]["page"]
    assert page["returned"] < 50 and page["limit"] < 50 and page["requested_limit"] == 50
    # A limit that fits is applied as given.
    page = _read(condominium, "shares", 5, budget=budget)["data"]["page"]
    assert page["limit"] == 5 and page["returned"] == 5 and "requested_limit" not in page
    # The cut pages still cover the whole sheet exactly once.
    seen, offset = [], 0
    while True:
        data = _read(condominium, "shares", None, offset, budget=budget)["data"]
        seen += [s["order_number"] for s in data["ownership_sheet_b"]["lr_unit_shares"]]
        if not data["page"]["truncated"]:
            break
        offset = data["page"]["next_offset"]
    assert seen == [s.order_number for s in condominium.ownership_sheet_b.lr_unit_shares]


def test_a_paged_level_whose_single_record_does_not_fit_is_refused(condominium) -> None:
    # One entry group of list C is about 60 kB on the wire; under a smaller
    # budget nothing can be cut further and the level is refused.
    entry = _read(condominium, "encumbrances", None, budget=50_000)
    assert entry["status"] == "error"
    assert entry["error_type"] == "response_too_large"
    assert "encumbrances" in entry["error"] and 'detail="summary"' in entry["error"]
    # The same level under a budget that holds a few groups is cut, not refused.
    data = _read(condominium, "encumbrances", None, budget=150_000)["data"]
    assert data["page"]["truncated"] is True and 0 < data["page"]["returned"] < 30



def test_several_units_share_the_budget(condominium) -> None:
    # Two units in one call each get half the budget, so the response as a
    # whole stays within it.
    tools = CadastralTools(_UnitClient(condominium), result_budget_bytes=200_000)
    ref = {"lr_unit_number": str(condominium.lr_unit_number), "main_book_id": 1}
    other = {"lr_unit_number": "2", "main_book_id": 1}  # served as a second unit
    res = asyncio.run(tools.get_lr_unit([ref, other], detail="shares", limit=None))
    assert [r["status"] for r in res["results"]] == ["success", "success"]
    assert all(_tools.wire_size(r["data"]) <= 100_000 for r in res["results"])
    # The envelope indents every nested line, which the per-entry measure does
    # not count; the default budget's margin under 1 MB covers that.
    assert _tools.wire_size(res) <= 200_000 * 1.15


ENCUMBERED = (
    REPO / "api" / "src" / "cadastral_api" / "tests" / "fixtures" / "lr_unit_encumbrances.json"
)


@pytest.fixture
def encumbered() -> LandRegistryUnitDetailed:
    raw = json.loads(ENCUMBERED.read_text(encoding="utf-8"))
    return LandRegistryUnitDetailed.model_validate(raw[0] if isinstance(raw, list) else raw)


# --- Finding one owner by name ------------------------------------------------


def _shape_ownership(unit, **kwargs) -> dict:
    return CadastralTools._shape_lr_unit(unit, "ownership", None, 0, **kwargs)


def test_owner_name_keeps_only_that_persons_rows(condominium) -> None:
    # Vlasnik 335 co-owns E-22 through two sub-shares: two rows, one name.
    shaped = _shape_ownership(condominium, owner_name="vlasnik 335")
    assert [row["name"] for row in shaped["owners"]] == ["Vlasnik 335", "Vlasnik 335"]
    assert all(row["condominium_number"] == "E-22" for row in shaped["owners"])
    assert shaped["owner_name"] == "vlasnik 335"
    assert shaped["matching_owners"] == 2
    assert shaped["total_owners"] == 103  # the whole sheet, still visible
    assert shaped["owners_truncated"] is False
    assert shaped["page"] == {
        "offset": 0, "limit": None, "total": 2, "returned": 2, "truncated": False,
    }


def test_owner_name_ignores_case_diacritics_and_word_order(unit) -> None:
    unit.ownership_sheet_b.lr_unit_shares[0].owners[0].name = "ŠARUNIĆ SAŠA"
    for spelling in ("Saša Šarunić", "sarunic sasa", "ŠARUNIĆ", "sarunic"):
        shaped = _shape_ownership(unit, owner_name=spelling)
        assert [row["name"] for row in shaped["owners"]] == ["ŠARUNIĆ SAŠA"], spelling
    # Every word must occur: a stranger with the same surname is not enough.
    assert _shape_ownership(unit, owner_name="Šarunić Ivan")["owners"] == []


def test_owner_name_with_no_match_is_an_empty_answer_not_an_error(condominium) -> None:
    shaped = _shape_ownership(condominium, owner_name="nobody here")
    assert shaped["owners"] == []
    assert shaped["matching_owners"] == 0
    assert shaped["total_owners"] == 103
    assert shaped["page"]["total"] == 0 and shaped["page"]["truncated"] is False


def test_owner_name_pages_through_the_matches(condominium) -> None:
    first = CadastralTools._shape_lr_unit(condominium, "ownership", 1, 0, owner_name="335")
    assert len(first["owners"]) == 1
    assert first["owners_truncated"] is True
    assert first["page"] == {
        "offset": 0, "limit": 1, "total": 2, "returned": 1, "truncated": True, "next_offset": 1,
    }
    second = CadastralTools._shape_lr_unit(condominium, "ownership", 1, 1, owner_name="335")
    assert len(second["owners"]) == 1 and second["owners_truncated"] is False


def test_owner_name_on_shares_keeps_the_matching_shares_whole(condominium) -> None:
    # E-27 is held by three co-owners through sub-shares; asking for one of
    # them returns the share with all three, so the co-ownership is visible.
    shaped = CadastralTools._shape_lr_unit(condominium, "shares", None, 0, owner_name="Vlasnik 341")
    shares = shaped["ownership_sheet_b"]["lr_unit_shares"]
    assert [share["condominium_number"] for share in shares] == ["E-27"]
    co_owners = [
        owner["name"]
        for sub in CadastralTools._sub_shares(shares[0])
        for owner in sub["owners"]
    ]
    assert co_owners == ["Vlasnik 340", "Vlasnik 341", "Vlasnik 342"]
    assert shaped["owner_name"] == "Vlasnik 341"
    assert shaped["matching_shares"] == 1
    assert shaped["total_shares"] == 85
    assert shaped["page"]["total"] == 1 and shaped["page"]["truncated"] is False
    # The shares not returned are counted as omitted, filtered-out ones included.
    assert shaped["shares_omitted"] == CadastralTools._count_shares(
        condominium.ownership_sheet_b.model_dump(mode="json")["lr_unit_shares"]
    ) - CadastralTools._count_shares(shares)
    assert _tools.wire_size(shaped) <= _tools.DEFAULT_RESULT_BUDGET_BYTES


def test_owner_name_on_full_filters_sheet_b_only(unit) -> None:
    name = unit.ownership_sheet_b.lr_unit_shares[0].owners[0].name
    shaped = CadastralTools._shape_lr_unit(unit, "full", None, 0, owner_name=name)
    assert shaped["matching_shares"] >= 1 and shaped["total_shares"] > 0
    assert "encumbrance_sheet_c" in shaped and "possessory_sheet_a1" in shaped
    assert all(
        CadastralTools._share_matches(share, name)
        for share in shaped["ownership_sheet_b"]["lr_unit_shares"]
    )


def test_owner_name_is_refused_where_there_are_no_owners(unit) -> None:
    for detail in ("summary", "parcels", "encumbrances"):
        with pytest.raises(ValueError, match="owner_name"):
            CadastralTools._shape_lr_unit(unit, detail, None, 0, owner_name="x")
    with pytest.raises(ValueError, match="blank"):
        _shape_ownership(unit, owner_name="   ")


def test_without_owner_name_nothing_about_the_answer_changes(unit) -> None:
    shaped = _shape_ownership(unit)
    assert "owner_name" not in shaped and "matching_owners" not in shaped
    full = CadastralTools._shape_lr_unit(unit, "full", None, 0)
    assert "owner_name" not in full and "matching_shares" not in full


def test_every_level_names_the_unit_with_its_provenance(unit) -> None:
    for detail in ("summary", "ownership", "shares", "parcels", "encumbrances", "full"):
        shaped = CadastralTools._shape_lr_unit(unit, detail, None)
        # A fixture unit was never fetched: the key is there, the value null.
        assert "provenance" in shaped and shaped["provenance"] is None


def test_owner_levels_count_distinct_owners(unit) -> None:
    names = {row["name"] for row in unit.ownership_sheet_b.owner_rows()}
    for detail in ("summary", "ownership", "shares", "full"):
        shaped = CadastralTools._shape_lr_unit(unit, detail, None)
        assert shaped["distinct_owners"] == len(names) == 3  # 4 records, one person on two shares
    # The count describes the whole sheet, whatever the window.
    paged = CadastralTools._shape_lr_unit(unit, "ownership", 1)
    assert paged["distinct_owners"] == 3 and len(paged["owners"]) == 1
    assert "distinct_owners" not in CadastralTools._shape_lr_unit(unit, "parcels", None)


def test_distinct_owners_merges_spellings_and_splits_tax_numbers(unit) -> None:
    from cadastral_api.models.entities import Party

    share = unit.ownership_sheet_b.lr_unit_shares[0]
    first = share.owners[0]
    share.owners.append(Party.model_validate({"name": first.name.lower() + "  "}))
    share.owners.append(Party.model_validate({"name": first.name, "taxNumber": "1"}))
    share.owners.append(Party.model_validate({"name": first.name, "taxNumber": "2"}))
    shaped = CadastralTools._shape_lr_unit(unit, "ownership", None)
    # Three more records: a respelling (same person, no tax number: joins the
    # name) and two new tax numbers on a name that already has one, which makes
    # that name three people; the other two names are unchanged.
    assert shaped["total_owners"] == 7
    assert shaped["distinct_owners"] == 5
