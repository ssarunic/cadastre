"""compare_registers: possessors against owners, one entry per parcel, units read once."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from cadastral_api.exceptions import CadastralAPIError, ErrorType
from cadastral_api.models.entities import LandRegistryUnitDetailed, ParcelInfo
from cadastral_api.models.provenance import Provenance

from cadastral_mcp.tools import CadastralTools

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "api" / "src" / "cadastral_api" / "tests" / "fixtures"


class _FakeClient:
    def __init__(self) -> None:
        self.parcel = ParcelInfo.model_validate(
            json.loads((FIXTURES / "parcel_info_linked.json").read_text())
        )
        self.parcel.provenance = Provenance("cadastre", "http://mock/cad/parcel-info?p=1", "t")
        raw = json.loads((FIXTURES / "lr_unit_lrparcels.json").read_text())
        self.unit = LandRegistryUnitDetailed.model_validate(
            raw[0] if isinstance(raw, list) else raw
        )
        self.unit.provenance = Provenance("land_registry", "http://mock/lr/lr-unit?x", "t")
        self.unit_calls = 0

    def get_parcel_info(self, parcel_id, **kwargs):
        if str(parcel_id) == "0":
            raise CadastralAPIError(ErrorType.PARCEL_NOT_FOUND, details={"parcel_id": "0"})
        return self.parcel

    def get_lr_unit_detailed(self, unit_number, main_book_id=None, **kwargs):
        self.unit_calls += 1
        if self.unit_calls > 5:
            raise CadastralAPIError(ErrorType.ACCESS_DENIED, details={"status_code": 403})
        return self.unit


def _run(coro):
    return asyncio.run(coro)


def test_one_entry_per_parcel_and_the_unit_read_once() -> None:
    client = _FakeClient()
    res = _run(CadastralTools(client).compare_registers([{"parcel_id": 1}, {"parcel_id": 2}]))
    assert res["total"] == 2 and res["successful"] == 2 and res["failed"] == 0
    assert res["units_fetched"] == 1 and client.unit_calls == 1
    entry = res["results"][0]
    assert entry["status"] == "success"
    assert entry["parcel_number"] == "1122/1" and entry["municipality_code"] == "334979"
    assert entry["lr_unit"] == {"lr_unit_number": "449", "main_book_id": 21277}
    assert entry["provenance"]["cadastre"]["register"] == "cadastre"
    assert entry["provenance"]["land_registry"]["register"] == "land_registry"
    data = entry["data"]
    assert data["relationship"] == "disjoint"
    assert data["area_check"]["land_registry_m2"] == 3291
    assert res["relationships"] == {"disjoint": 2}
    people = res["people"]
    # The same parcel twice: people are counted once.
    assert people["distinct_owners"] == 3
    assert people["distinct_possessors"] == data["distinct_possessors"]
    assert people["distinct_people"] == people["distinct_owners"] + people["distinct_possessors"]


def test_errors_are_per_entry_with_their_kind() -> None:
    tools = CadastralTools(_FakeClient())
    res = _run(tools.compare_registers([{"parcel_id": 0}, {"parcel_number": "x"}]))
    assert res["failed"] == 2
    assert res["results"][0]["error_type"] == "parcel_not_found"
    assert res["results"][1]["error_type"] == "invalid_request"


def test_an_unreadable_unit_keeps_the_possessors() -> None:
    client = _FakeClient()
    client.unit_calls = 5  # the next unit read is refused
    res = _run(CadastralTools(client).compare_registers([{"parcel_id": 1}]))
    entry = res["results"][0]
    assert entry["status"] == "success"
    assert entry["land_registry_error"]["error_type"] == "access_denied"
    assert entry["data"]["relationship"] == "land_registry_unavailable"
    assert entry["data"]["possessors"] and entry["data"]["owners"] == []
    assert entry["provenance"]["land_registry"] is None
