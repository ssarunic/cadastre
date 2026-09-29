"""Sale blockers and owner flags through the MCP tools.

- get_lr_unit carries ``sale_blockers`` at every level (the list itself on
  "ownership" and "encumbrances"), ``owner_flags_summary``, and ``flags`` on
  each ownership row; ``condominium_unit`` narrows the blockers; the plomba
  detail names the pending request.
- compare_registers and build_assembly carry the composed blockers and the
  flags without any code of their own.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from cadastral_api.exceptions import CadastralAPIError, ErrorType
from cadastral_api.models.entities import FileStatus, LandRegistryUnitDetailed, ParcelInfo
from cadastral_api.models.provenance import Provenance

from cadastral_mcp.tools import CadastralTools

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "api" / "src" / "cadastral_api" / "tests" / "fixtures"


def _unit(name: str) -> LandRegistryUnitDetailed:
    raw = json.loads((FIXTURES / name).read_text())
    unit = LandRegistryUnitDetailed.model_validate(raw[0] if isinstance(raw, list) else raw)
    unit.provenance = Provenance("land_registry", "http://mock/lr/lr-unit?x", "t")
    return unit


class _FakeClient:
    """Serves the synthetic unit 9001 (or the condominium) for any reference."""

    def __init__(self, name: str = "lr_unit_sale_blockers.json") -> None:
        self.unit = _unit(name)
        self.parcel = ParcelInfo.model_validate(
            json.loads((FIXTURES / "parcel_info_linked.json").read_text())
        )
        self.parcel.provenance = Provenance("cadastre", "http://mock/cad/parcel-info?p=1", "t")
        self.status = FileStatus.model_validate(
            json.loads((FIXTURES / "file_status_pending.json").read_text())
        )
        self.status_calls: list[str] = []

    def get_lr_unit_detailed(self, unit_number, main_book_id=None, **kwargs):
        return self.unit

    def get_lr_unit_from_parcel(
        self, parcel_number, municipality, historical_overview=False, **kwargs
    ):
        return self.unit

    def get_plombe_details(self, lr_unit):
        self.status_calls.append(lr_unit.lr_unit_number)
        return {p.file_number: self.status for p in lr_unit.active_plumbs}

    def get_parcel_info(self, parcel_id, **kwargs):
        if str(parcel_id) == "0":
            raise CadastralAPIError(ErrorType.PARCEL_NOT_FOUND, details={"parcel_id": "0"})
        return self.parcel

    def resolve_municipality_reg_num(self, name_or_code):
        return str(name_or_code)


def _run(coro):
    return asyncio.run(coro)


def _data(client: _FakeClient, **kwargs):
    res = _run(
        CadastralTools(client).get_lr_unit(
            [{"lr_unit_number": "9001", "main_book_id": 21277}], **kwargs
        )
    )
    entry = res["results"][0]
    assert entry["status"] == "success", entry
    return res, entry["data"]


def test_every_level_carries_the_screening_and_two_carry_the_list() -> None:
    client = _FakeClient()
    for detail in ("summary", "shares", "full", "parcels"):
        _, data = _data(client, detail=detail)
        brief = data["sale_blockers"]
        assert brief["verdict"] == "blocked" and brief["blocker_count"] == 11
        assert "likely_estate" in brief["blocker_kinds"]
        assert "blockers" not in brief and "mortgage" in brief["blocker_kinds"]
        assert brief["cancelled_count"] == 1 and "ownership" in brief["detail_note"]
    for detail in ("ownership", "encumbrances"):
        _, data = _data(client, detail=detail)
        blockers = data["sale_blockers"]
        assert blockers["verdict"] == "blocked"
        assert [b["kind"] for b in blockers["blockers"]][:3] == [
            "pending_entry",
            "pending_entry",
            "mortgage",
        ]
        assert len(blockers["blockers_cancelled"]) == 1
        assert "amount_value" not in blockers["blockers"][0]  # nulls are left out
        assert blockers["blockers"][2]["amount_value"] == 50000.0
    _, data = _data(client, detail="ownership")
    assert data["owner_flags_summary"] == {
        "owners": 7,
        "likely_deceased": 3,
        "address_abroad": 2,
        "address_unknown": 1,
        "public_body": 1,
    }
    flags = {row["name"]: row["flags"] for row in data["owners"]}
    assert flags["KOVAČ ANA"]["address_abroad"]["country"] == "Germany"
    assert flags["POKOJNI HORVAT MARKO"]["likely_deceased"]["signals"] == ["name_marker"]
    assert flags["REPUBLIKA HRVATSKA"]["public_body"] is True
    assert flags["REPUBLIKA HRVATSKA"]["likely_deceased"] is None
    assert data["owners"][0]["share_order_number"] == "1"
    _, data = _data(client, detail="parcels")
    assert "owner_flags_summary" not in data


def test_plombe_detail_feeds_the_pending_blockers_once() -> None:
    client = _FakeClient()
    res, data = _data(client, detail="ownership", include_plombe_detail=True)
    assert client.status_calls == ["9001"]  # fetched once, used twice
    assert set(data["plombe_detail"]) == {"Z-100/2026", "Z-101/2026"}
    pending = [b for b in data["sale_blockers"]["blockers"] if b["kind"] == "pending_entry"]
    assert all(b["request_kind"] == client.status.application_content for b in pending)
    assert data["sale_blockers"]["plombe_detail_included"] is True


def test_condominium_unit_narrows_the_blockers_and_is_echoed() -> None:
    client = _FakeClient("lr_unit_condominium.json")
    res = _run(
        CadastralTools(client).get_lr_unit(
            [{"lr_unit_number": "13998", "main_book_id": 30783}],
            detail="encumbrances",
            condominium_unit="E-80",
            limit=2,
        )
    )
    assert res["condominium_unit"] == "E-80"
    data = res["results"][0]["data"]
    blockers = data["sale_blockers"]
    assert blockers["scope_filter"] == {"condominium_unit": "E-80"}
    assert all(
        b["scope"] == "unit" or b.get("condominium_unit") == "E-80" for b in blockers["blockers"]
    )
    assert any("left out" in note for note in blockers["notes"])
    # The owner rows are not filtered by the flat: the summary still counts them all.
    _, summary = (
        None,
        _run(
            CadastralTools(client).get_lr_unit(
                [{"lr_unit_number": "13998", "main_book_id": 30783}],
                detail="summary",
                condominium_unit="80",
            )
        )["results"][0]["data"],
    )
    assert summary["owner_flags_summary"]["owners"] == 103
    assert summary["sale_blockers"]["scope_filter"] == {"condominium_unit": "80"}


def test_a_blank_condominium_unit_is_that_entrys_error() -> None:
    res = _run(
        CadastralTools(_FakeClient()).get_lr_unit(
            [{"lr_unit_number": "9001", "main_book_id": 21277}], condominium_unit="()"
        )
    )
    entry = res["results"][0]
    assert entry["status"] == "error" and entry["error_type"] == "invalid_request"


def test_compare_registers_and_build_assembly_carry_the_composition() -> None:
    client = _FakeClient()
    tools = CadastralTools(client)
    res = _run(tools.compare_registers([{"parcel_id": 1}]))
    data = res["results"][0]["data"]
    kinds = [b["kind"] for b in data["sale_blockers"]["blockers"]]
    assert "owner_not_possessor" in kinds and data["sale_blockers"]["verdict"] == "blocked"
    assert data["owner_flag_counts"]["likely_deceased"] == 3
    assert data["owners"][0]["flags"]["address_abroad"]["abroad"] is False

    res = _run(tools.build_assembly([{"parcel_id": 1}], persons_limit=None))
    parcel = res["parcels"][0]
    assert parcel["sale_verdict"] == "blocked"
    assert parcel["blocker_counts"]["blocking"] == 3
    assert "mortgage" in parcel["blocker_kinds"]
    assert res["totals"]["parcels_by_verdict"] == {"blocked": 1}
    assert res["totals"]["persons_likely_deceased"] == 3
    persons = {p["name"]: p for p in res["persons"]}
    assert persons["KOVAČ ANA"]["address_abroad"] is True
    groups = {g["surname"]: g for g in res["surname_groups"]}
    assert groups["kovac"]["address_abroad_count"] == 2
    assert res["scores"][0]["factors"]["no_pending_plombe"] is False


def test_compare_registers_names_the_pending_requests_on_request() -> None:
    client = _FakeClient()
    tools = CadastralTools(client)
    plain = _run(tools.compare_registers([{"parcel_id": 1}]))
    pending = [
        b for b in plain["results"][0]["data"]["sale_blockers"]["blockers"]
        if b["kind"] == "pending_entry"
    ]
    assert pending and all(b.get("request_kind") is None for b in pending)
    assert client.status_calls == []
    named = _run(
        tools.compare_registers([{"parcel_id": 1}, {"parcel_id": 2}], include_plombe_detail=True)
    )
    assert client.status_calls == ["9001"]  # once per unit, not per parcel
    for entry in named["results"]:
        pending = [
            b for b in entry["data"]["sale_blockers"]["blockers"] if b["kind"] == "pending_entry"
        ]
        assert all(b["request_kind"] == client.status.application_content for b in pending)
    assembled = _run(tools.build_assembly([{"parcel_id": 1}], include_plombe_detail=True))
    assert client.status_calls == ["9001", "9001"]
    assert assembled["parcels"][0]["sale_verdict"] == "blocked"


def test_the_people_block_counts_a_matched_person_once() -> None:
    client = _FakeClient()
    sheet = client.parcel.possession_sheets[0]
    sheet.possessors = sheet.possessors[:2]
    for other in client.parcel.possession_sheets[1:]:
        other.possessors = []
    # The cadastre spells the owner with the father's name after a comma.
    sheet.possessors[0].name = "HORVAT IVAN, MARKO"
    sheet.possessors[1].name = "NOBODY ELSE"
    res = _run(CadastralTools(client).compare_registers([{"parcel_id": 1}, {"parcel_id": 2}]))
    data = res["results"][0]["data"]
    assert data["relationship"] == "overlapping" and data["fuzzy_matches"] == 1
    assert data["matched"][0]["via"] == "name_loose"
    assert data["matched"][0]["by_tax_number"] is False
    people = res["people"]
    assert people["distinct_possessors"] == 2 and people["distinct_owners"] == 7
    # 2 + 7 records, one person in both registers, the same parcel twice.
    assert people["distinct_people"] == 8 == data["distinct_people"]


class _TwoParcelClient(_FakeClient):
    """Two parcels on two units, each with an Augustin: not the same person."""

    def __init__(self) -> None:
        super().__init__()
        self.parcels = {
            1: ParcelInfo.model_validate(
                json.loads((FIXTURES / "parcel_info_linked.json").read_text())
            ),
            2: ParcelInfo.model_validate(
                json.loads((FIXTURES / "parcel_info_direct.json").read_text())
            ),
        }
        self.units = {
            "449": _unit("lr_unit_lrparcels.json"),
            "788": _unit("lr_unit_cadparcels.json"),
        }
        for number, parcel in self.parcels.items():
            sheet = parcel.possession_sheets[0]
            sheet.possessors = sheet.possessors[:1]
            sheet.possessors[0].name = f"POSJEDNIK {number}"
            for other in parcel.possession_sheets[1:]:
                other.possessors = []
        legacy = self.units["449"].ownership_sheet_b.lr_unit_shares[0].owners[0]
        legacy.name, legacy.tax_number, legacy.entry = "ŠARUNIĆ AUGUSTIN POK. BOŽE", None, None
        living = self.units["788"].ownership_sheet_b.lr_unit_shares[0].owners[0]
        living.name, living.tax_number = "ŠARUNIĆ AUGUSTIN", "63061048570"

    def get_parcel_info(self, parcel_id, **kwargs):
        return self.parcels[int(parcel_id)]

    def get_lr_unit_detailed(self, unit_number, main_book_id=None, **kwargs):
        return self.units[str(unit_number)]


def test_namesakes_on_two_parcels_are_two_people_in_the_set_total() -> None:
    tools = CadastralTools(_TwoParcelClient())
    res = _run(tools.compare_registers([{"parcel_id": 1}, {"parcel_id": 2}]))
    per_parcel = [entry["data"]["distinct_people"] for entry in res["results"]]
    assert res["units_fetched"] == 2
    # Nobody appears on both parcels: the set total is the sum of the two.
    assert res["people"]["distinct_people"] == sum(per_parcel)
    owners = [
        o for entry in res["results"] for o in entry["data"]["owners"] if "AUGUSTIN" in o["name"]
    ]
    assert len(owners) == 2
    assert {o["flags"]["likely_deceased"]["likely_deceased"] for o in owners} == {True, False}
