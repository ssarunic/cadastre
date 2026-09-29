"""build_assembly: gathers records per parcel, units once, exports on request."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from cadastral_api.exceptions import CadastralAPIError, ErrorType
from cadastral_api.models.entities import LandRegistryUnitDetailed, ParcelInfo

from cadastral_mcp.tools import CadastralTools

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "api" / "src" / "cadastral_api" / "tests" / "fixtures"


class _FakeClient:
    def __init__(self) -> None:
        self.parcel = ParcelInfo.model_validate(
            json.loads((FIXTURES / "parcel_info_linked.json").read_text())
        )
        raw = json.loads((FIXTURES / "lr_unit_lrparcels.json").read_text())
        self.unit = LandRegistryUnitDetailed.model_validate(
            raw[0] if isinstance(raw, list) else raw
        )
        self.unit_calls = 0
        self.zoning_calls = 0

    def get_parcel_info(self, parcel_id, **kwargs):
        if str(parcel_id) == "0":
            raise CadastralAPIError(ErrorType.PARCEL_NOT_FOUND, details={"parcel_id": "0"})
        return self.parcel

    def get_lr_unit_detailed(self, unit_number, main_book_id=None, **kwargs):
        self.unit_calls += 1
        return self.unit

    def get_parcel_zoning(self, parcel_number, municipality_reg_num, min_overlap=0.02):
        self.zoning_calls += 1
        raise CadastralAPIError(ErrorType.CONNECTION, details={"reason": "all_mirrors_failed"})


def _run(coro):
    return asyncio.run(coro)


def test_assembly_over_two_parcels_sharing_a_unit() -> None:
    client = _FakeClient()
    refs = [{"parcel_id": 1}, {"parcel_id": 2}, {"parcel_id": 0}]
    res = _run(CadastralTools(client).build_assembly(refs))
    assert res["total"] == 3 and res["successful"] == 2
    assert res["failed"][0]["error_type"] == "parcel_not_found"
    assert res["units_fetched"] == 1 and client.unit_calls == 1
    assert res["zoning_requested"] is False
    assert [p["parcel_number"] for p in res["parcels"]] == ["1122/1", "1122/1"]
    assert res["parcels"][0]["relationship"] == "disjoint"
    assert res["parcels"][0]["score"] is not None
    assert res["scores"][0]["factors"]["in_building_area"] is None
    assert res["totals"]["parcel_count"] == 2 and res["totals"]["distinct_owners"] == 3
    assert res["persons_page"]["returned"] == len(res["persons"]) == 50
    assert res["persons_page"]["total"] > 50 and res["persons_page"]["truncated"] is True
    assert set(res["weights"]) == {
        "single_owner", "owner_is_possessor", "no_encumbrances", "no_pending_plombe",
        "in_building_area",
    }
    assert "export" not in res


def test_zoning_failure_is_a_note_not_an_error() -> None:
    client = _FakeClient()
    res = _run(CadastralTools(client).build_assembly([{"parcel_id": 1}], include_zoning=True))
    assert client.zoning_calls == 1
    assert res["zoning_requested"] is True
    assert any("zoning of 1122/1 not read (connection)" in note for note in res["notes"])
    assert res["scores"][0]["factors"]["in_building_area"] is None


def test_exports_and_paging() -> None:
    tools = CadastralTools(_FakeClient())
    res = _run(tools.build_assembly([{"parcel_id": 1}], export="persons_csv", persons_limit=2))
    assert res["export"]["format"] == "persons_csv"
    header = res["export"]["text"].splitlines()[0]
    assert header.startswith("name,surname,tax_number,party_type_inferred,parcel_count")
    assert len(res["persons"]) == 2 and res["persons_page"]["truncated"] is True
    res = _run(tools.build_assembly([{"parcel_id": 1}], export="geojson"))
    assert res["export"]["type"] == "FeatureCollection"
    assert res["export"]["skipped"] == ["1122/1"]  # no GIS outline from this fake
    res = _run(tools.build_assembly([{"parcel_id": 1}], export="matrix_csv"))
    header = res["export"]["text"].splitlines()[0]
    assert header == "name,parcel_number,role,owner_share,possessor_share,fuzzy,records"


@pytest.mark.parametrize(
    "kwargs, fragment",
    [
        ({"parcels": [{"parcel_id": i} for i in range(51)]}, "at most 50"),
        ({"parcels": []}, "at least one"),
        ({"parcels": [{"parcel_id": 1}], "export": "xlsx"}, "export must be"),
        ({"parcels": [{"parcel_id": 1}], "weights": {"price": 1}}, "unknown factor"),
        ({"parcels": [{"parcel_id": 1}], "persons_limit": 0}, "persons_limit"),
        ({"parcels": [{"parcel_id": 0}]}, "None of the parcels"),
    ],
)
def test_validation(kwargs, fragment) -> None:
    with pytest.raises(ValueError) as excinfo:
        _run(CadastralTools(_FakeClient()).build_assembly(**kwargs))
    assert fragment in str(excinfo.value)


def test_the_blockers_table_and_its_export() -> None:
    client = _FakeClient()
    tools = CadastralTools(client)
    res = _run(tools.build_assembly([{"parcel_id": 1}], export="blockers_csv"))
    assert res["blocker_count"] == len(res["blockers"]) > 0
    first = res["blockers"][0]
    assert first["parcel_number"] == "1122/1" and first["kind"] == "pending_entry"
    assert first["lr_unit_number"] == "449" and "amount" not in first  # nulls left out
    assert res["export"]["format"] == "blockers_csv"
    assert res["export"]["text"].splitlines()[0].startswith("parcel_number,municipality_code")
    lean = _run(tools.build_assembly([{"parcel_id": 1}], include_blockers=False))
    assert lean["blockers"] is None and lean["blocker_count"] == res["blocker_count"]
