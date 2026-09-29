"""Tests for get_parcel register selection and per-parcel results.

The MCP package __init__ imports the MCP SDK (MCPServer), which need not be
installed to exercise the pure handler logic. tools.py only depends on
cadastral_api, so we load it as a standalone module and drive it with a fake
client backed by a real (redacted) parcel-info fixture.
"""

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "api" / "src"))

from cadastral_api.models.entities import ParcelInfo  # noqa: E402

# Load mcp/src/cadastral_mcp/tools.py without triggering the package __init__.
_TOOLS_PATH = REPO / "mcp" / "src" / "cadastral_mcp" / "tools.py"
_spec = importlib.util.spec_from_file_location("cadastral_mcp_tools_standalone", _TOOLS_PATH)
_tools = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tools)
CadastralTools = _tools.CadastralTools

FIXTURE = REPO / "api" / "src" / "cadastral_api" / "tests" / "fixtures" / "parcel_info_linked.json"


class _FakeClient:
    """Returns a fixed ParcelInfo regardless of id (1122/1: lr_unit is null,
    but reachable via parcel links)."""

    def __init__(self) -> None:
        self._parcel = ParcelInfo.model_validate(
            json.loads(FIXTURE.read_text(encoding="utf-8"))
        )

    def get_parcel_info(self, parcel_id: str, **kwargs) -> ParcelInfo:
        return self._parcel


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def tools() -> "CadastralTools":
    return CadastralTools(_FakeClient())


def test_cadastre_source_includes_tagged_possessors(tools) -> None:
    res = _run(tools.get_parcel([{"parcel_id": "6564741"}], source="cadastre"))
    assert res["source"] == "cadastre"
    result = res["results"][0]
    assert result["register"] == "cadastre"
    possessors = result["data"]["possession_sheets"][0]["possessors"]
    assert all(p["register"] == "cadastre" for p in possessors)


def test_land_registry_source_omits_possessors_and_hints(tools) -> None:
    res = _run(tools.get_parcel([{"parcel_id": "6564741"}], source="land_registry"))
    assert res["source"] == "land_registry"
    data = res["results"][0]["data"]
    assert "possession_sheets" not in data
    hint = data["land_registry_hint"]
    # 1122/1 has no direct lr_unit but resolves via parcel links (F3 scenario).
    assert hint["in_land_registry"] is True
    assert hint["lr_unit_derived_from_links"] is True
    assert hint["lr_unit_ref"]["lr_unit_number"]


def test_linked_unit_is_promoted_into_data_lr_unit(tools) -> None:
    # 1122/1 has lrUnit null; the docs promise data.lr_unit, so the unit
    # reachable through the parcel links is placed there and labelled.
    for source in ("cadastre", "land_registry", "none"):
        res = _run(tools.get_parcel([{"parcel_id": "6564741"}], source=source))
        data = res["results"][0]["data"]
        assert data["lr_reference_shape"] == "linked"
        assert data["lr_unit"] is not None
        linked = data["lr_units_from_parcel_links"][0]
        assert (data["lr_unit"]["lr_unit_number"], data["lr_unit"]["main_book_id"]) == (
            linked["lr_unit_number"], linked["main_book_id"]
        )


def test_none_source_drops_possessors(tools) -> None:
    res = _run(tools.get_parcel([{"parcel_id": "6564741"}], source="none"))
    data = res["results"][0]["data"]
    assert "possession_sheets" not in data
    assert "land_registry_hint" not in data


def test_invalid_source_raises(tools) -> None:
    with pytest.raises(ValueError):
        _run(tools.get_parcel([{"parcel_id": "6564741"}], source="bogus"))


class _FakeClientWithGis(_FakeClient):
    """Like _FakeClient, but the municipality GIS data is available."""

    def __init__(self) -> None:
        super().__init__()
        self.geometry_calls: list[tuple[str, str]] = []

    def get_parcel_geometry(self, parcel_number: str, municipality_reg_num: str):
        from cadastral_api.models.gis_entities import ParcelGeometry

        self.geometry_calls.append((parcel_number, municipality_reg_num))
        return ParcelGeometry(
            cestica_id="1",
            broj_cestice=parcel_number,
            povrsina_graficka=1.0,
            maticni_broj_ko=municipality_reg_num,
            coordinates=[{"x": 380596.77, "y": 4880892.83}, {"x": 380636.77, "y": 4880922.83}],
        )


def test_entry_carries_map_url_when_gis_is_available() -> None:
    client = _FakeClientWithGis()
    res = _run(CadastralTools(client).get_parcel([{"parcel_id": "6564741"}]))

    entry = res["results"][0]
    assert entry["status"] == "success"
    # Resolved from the detailed record, even though the spec gave only parcel_id.
    assert client.geometry_calls == [("1122/1", "334979")]
    assert entry["map_url"].startswith(
        "https://oss.uredjenazemlja.hr/map?center=380616.77,4880907.83&zoom=19&"
    )


def test_entry_omits_map_url_when_gis_is_unavailable(tools) -> None:
    # _FakeClient has no GIS support at all; the lookup must still succeed.
    res = _run(tools.get_parcel([{"parcel_id": "6564741"}]))

    entry = res["results"][0]
    assert entry["status"] == "success"
    assert "map_url" not in entry
    assert res["successful"] == 1


def test_each_reference_gets_its_own_entry_and_bad_refs_are_reported(tools) -> None:
    res = _run(
        tools.get_parcel(
            [{"parcel_id": "6564741"}, {"parcel_number": "103/2"}, {"parcel_id": 6564742}],
            source="none",
        )
    )
    assert [r["status"] for r in res["results"]] == ["success", "error", "success"]
    assert res["total"] == 3 and res["successful"] == 2 and res["failed"] == 1
    assert "municipality" in res["results"][1]["error"]
    assert res["results"][0]["ref"] == {"parcel_id": 6564741}


def test_empty_reference_list_is_refused(tools) -> None:
    with pytest.raises(ValueError):
        _run(tools.get_parcel([], source="cadastre"))


def test_own_output_parcel_id_is_accepted_as_input(tools) -> None:
    first = _run(tools.get_parcel([{"parcel_id": "6564741"}], source="none"))
    parcel_id = first["results"][0]["data"]["parcel_id"]  # an integer, as the model types it
    assert isinstance(parcel_id, int)
    again = _run(tools.get_parcel([{"parcel_id": parcel_id}], source="none"))
    assert again["results"][0]["status"] == "success"
    assert again["results"][0]["ref"] == {"parcel_id": parcel_id}
    # A numeric string is accepted and normalised to the integer id.
    as_text = _run(tools.get_parcel([{"parcel_id": str(parcel_id)}], source="none"))
    assert as_text["results"][0]["ref"] == {"parcel_id": parcel_id}


# --- Paging through the possessors of a large parcel -------------------------


def _possessor_names(entry: dict) -> list[str]:
    return [
        p["name"]
        for sheet in entry["data"]["possession_sheets"]
        for p in sheet["possessors"]
    ]


class _FakeCondominiumClient:
    """A parcel under a condominium: a first sheet with three possessors and a
    second sheet with ``n`` of them, each carrying an address, so the record
    is as heavy as a real one."""

    def __init__(self, n: int = 400) -> None:
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        template = (raw["possessionSheets"][0]["possessors"] or [{"name": "X"}])[0]
        first = dict(raw["possessionSheets"][0])
        first["possessors"] = [
            {**template, "name": f"FIRST {i}", "ownership": "1/3"} for i in range(3)
        ]
        second = dict(raw["possessionSheets"][0])
        second["possessionSheetId"] = 99
        second["possessionSheetNumber"] = "99"
        second["possessors"] = [
            {
                **template,
                "name": f"POSSESSOR {i:04d}",
                "address": "Ulica grada Vukovara 269d, 10000 Zagreb, Hrvatska",
                "condominiumShareNumber": str(i),
                "condominiumShareOwnership": f"{i}/4651",
            }
            for i in range(n)
        ]
        raw["possessionSheets"] = [first, second]
        self._parcel = ParcelInfo.model_validate(raw)

    def get_parcel_info(self, parcel_id: str, **kwargs) -> ParcelInfo:
        return self._parcel


def test_cadastre_entry_carries_a_page_block_and_totals(tools) -> None:
    entry = _run(tools.get_parcel([{"parcel_id": "6564741"}]))["results"][0]
    total = sum(s["total_possessors"] for s in entry["data"]["possession_sheets"])
    assert entry["total_possessors"] == total > 0
    assert entry["possessors_truncated"] is False
    assert entry["page"] == {
        "offset": 0, "limit": None, "total": total, "returned": total, "truncated": False,
    }


def test_other_sources_carry_no_page_block(tools) -> None:
    for source in ("land_registry", "none"):
        entry = _run(tools.get_parcel([{"parcel_id": "1"}], source=source))["results"][0]
        assert "page" not in entry and "total_possessors" not in entry


def test_possessors_are_paged_across_sheets_and_none_is_lost() -> None:
    tools = CadastralTools(_FakeCondominiumClient(n=10))
    seen: list[str] = []
    offset = 0
    while True:
        res = _run(tools.get_parcel([{"parcel_id": "1"}], offset=offset, limit=4))
        entry = res["results"][0]
        assert entry["status"] == "success", entry
        seen.extend(_possessor_names(entry))
        # Both sheet headers stay visible on every page, with their own totals.
        assert [s["total_possessors"] for s in entry["data"]["possession_sheets"]] == [3, 10]
        assert entry["total_possessors"] == 13
        if not entry["page"]["truncated"]:
            break
        offset = entry["page"]["next_offset"]
    assert seen == [f"FIRST {i}" for i in range(3)] + [f"POSSESSOR {i:04d}" for i in range(10)]
    # The first page cuts through the sheet boundary: 3 from the first, 1 from the second.
    first = _run(tools.get_parcel([{"parcel_id": "1"}], limit=4))["results"][0]
    assert [len(s["possessors"]) for s in first["data"]["possession_sheets"]] == [3, 1]
    assert first["page"] == {
        "offset": 0, "limit": 4, "total": 13, "returned": 4, "truncated": True, "next_offset": 4,
    }
    assert first["possessors_truncated"] is True


def test_window_past_the_end_is_empty_not_an_error() -> None:
    tools = CadastralTools(_FakeCondominiumClient(n=10))
    entry = _run(tools.get_parcel([{"parcel_id": "1"}], offset=50, limit=5))["results"][0]
    assert entry["status"] == "success"
    assert _possessor_names(entry) == []
    assert entry["page"]["returned"] == 0 and entry["page"]["truncated"] is False


def test_a_parcel_too_large_to_return_is_that_parcels_error_with_a_smaller_limit() -> None:
    tools = CadastralTools(_FakeCondominiumClient(n=400))
    res = _run(tools.get_parcel([{"parcel_id": "1"}]))
    entry = res["results"][0]
    assert entry["status"] == "error"
    assert res["failed"] == 1
    assert "too large" in entry["error"]
    assert "limit=" in entry["error"] and 'source="none"' in entry["error"]
    # The way forward it names works.
    paged = _run(tools.get_parcel([{"parcel_id": "1"}], limit=50))["results"][0]
    assert paged["status"] == "success"
    assert paged["page"]["returned"] == 50 and paged["page"]["total"] == 403
    assert len(json.dumps(paged, ensure_ascii=False)) <= CadastralTools.MAX_PARCEL_RESPONSE_CHARS
    # The suggested limit is proportional to what fits, not a quarter of the window.
    refused = _run(tools.get_parcel([{"parcel_id": "1"}], limit=300))["results"][0]
    assert refused["status"] == "error"
    suggested = int(refused["error"].split("limit=")[1].split(")")[0])
    assert 150 < suggested < 300
    retry = _run(tools.get_parcel([{"parcel_id": "1"}], limit=suggested))["results"][0]
    assert retry["status"] == "success"
    # Without the possessors the parcel itself is never refused.
    bare = _run(tools.get_parcel([{"parcel_id": "1"}], source="none"))["results"][0]
    assert bare["status"] == "success"


def test_bad_paging_arguments_are_refused(tools) -> None:
    with pytest.raises(ValueError):
        _run(tools.get_parcel([{"parcel_id": "1"}], limit=0))
    with pytest.raises(ValueError):
        _run(tools.get_parcel([{"parcel_id": "1"}], offset=-1))


def test_distinct_possessors_counts_names_not_records() -> None:
    client = _FakeCondominiumClient(n=6)
    # The same person holds a flat and a storage room: two records, one name.
    sheet = client._parcel.possession_sheets[1]
    sheet.possessors[1].name = "ANA  Anić"
    sheet.possessors[4].name = "Ana Anić"
    tools = CadastralTools(client)
    entry = _run(tools.get_parcel([{"parcel_id": "1"}], limit=2))["results"][0]
    assert entry["total_possessors"] == 9
    assert entry["distinct_possessors"] == 8
    # Counted over the whole parcel, whatever the window.
    later = _run(tools.get_parcel([{"parcel_id": "1"}], offset=8, limit=2))["results"][0]
    assert later["distinct_possessors"] == 8


def test_possessor_name_filter_finds_a_person_without_paging() -> None:
    client = _FakeCondominiumClient(n=30)
    sheet = client._parcel.possession_sheets[1]
    sheet.possessors[17].name = "ANĐELIĆ BRKIĆ MARIJA"
    sheet.possessors[23].name = "Brkić Ivan"
    tools = CadastralTools(client)
    entry = _run(
        tools.get_parcel([{"parcel_id": "1"}], possessor_name="brkic andelic")
    )["results"][0]
    assert entry["status"] == "success", entry
    assert _possessor_names(entry) == ["ANĐELIĆ BRKIĆ MARIJA"]
    assert entry["matching_possessors"] == 1
    assert entry["possessor_filter"] == {"possessor_name": "brkic andelic"}
    assert entry["page"]["total"] == 1 and entry["page"]["truncated"] is False
    # The whole-parcel counts are untouched by the filter.
    assert entry["total_possessors"] == 33
    assert [s["total_possessors"] for s in entry["data"]["possession_sheets"]] == [3, 30]
    both = _run(tools.get_parcel([{"parcel_id": "1"}], possessor_name="brkić"))["results"][0]
    assert _possessor_names(both) == ["ANĐELIĆ BRKIĆ MARIJA", "Brkić Ivan"]
    # Paging applies to the matches.
    second = _run(
        tools.get_parcel([{"parcel_id": "1"}], possessor_name="brkić", offset=1, limit=1)
    )["results"][0]
    assert _possessor_names(second) == ["Brkić Ivan"]


def test_condominium_unit_filter_accepts_the_e_spelling() -> None:
    tools = CadastralTools(_FakeCondominiumClient(n=30))
    for spelling in ("5", "E-5", "E5", " e-5 "):
        entry = _run(
            tools.get_parcel([{"parcel_id": "1"}], condominium_unit=spelling)
        )["results"][0]
        assert _possessor_names(entry) == ["POSSESSOR 0005"], spelling
    none = _run(tools.get_parcel([{"parcel_id": "1"}], condominium_unit="99"))["results"][0]
    assert none["status"] == "success" and none["matching_possessors"] == 0


def test_filters_need_the_cadastre_source_and_a_value(tools) -> None:
    with pytest.raises(ValueError):
        _run(tools.get_parcel([{"parcel_id": "1"}], source="none", possessor_name="x"))
    with pytest.raises(ValueError):
        _run(tools.get_parcel([{"parcel_id": "1"}], possessor_name="   "))
    with pytest.raises(ValueError):
        _run(tools.get_parcel([{"parcel_id": "1"}], condominium_unit=""))


# ---------------------------------------------------------------------------
# Provenance, area check and typed errors (foundation increment)
# ---------------------------------------------------------------------------


def test_entry_carries_provenance_next_to_register(tools) -> None:
    entry = _run(tools.get_parcel([{"parcel_id": "6564741"}]))["results"][0]
    # A fixture record was never fetched, so its provenance is null, but the
    # key is always there; it is not repeated inside the record.
    assert "provenance" in entry and entry["provenance"] is None
    assert "provenance" not in entry["data"]


def test_entry_carries_an_area_check_without_gis(tools) -> None:
    entry = _run(tools.get_parcel([{"parcel_id": "6564741"}]))["results"][0]
    check = entry["area_check"]
    assert check["cadastre_m2"] == int(float(entry["data"]["area"]))
    assert check["gis_m2"] is None
    assert "cadastre" in check["compared"] and "gis" not in check["compared"]
    assert check["mismatch"] is False or check["max_difference_fraction"] > 0.05
    assert check["tolerance_fraction"] == 0.05


def test_area_check_flags_a_graphical_area_that_disagrees() -> None:
    client = _FakeClientWithGis()  # graphical area 1.0 m2 against a real cadastre area
    entry = _run(CadastralTools(client).get_parcel([{"parcel_id": "6564741"}]))["results"][0]
    check = entry["area_check"]
    assert check["gis_m2"] == 1.0
    assert "gis" in check["compared"]
    assert check["mismatch"] is True
    assert entry["map_url"]
    # The outline is looked up once and serves both the map link and the check.
    assert client.geometry_calls == [("1122/1", "334979")]


def test_a_bad_reference_is_an_invalid_request(tools) -> None:
    res = _run(tools.get_parcel([{"parcel_number": "1"}]))
    entry = res["results"][0]
    assert entry["status"] == "error"
    assert entry["error_type"] == "invalid_request"
    assert "error_details" not in entry


class _FakeClientRefusing(_FakeClient):
    def get_parcel_info(self, parcel_id: str, **kwargs) -> ParcelInfo:
        from cadastral_api.exceptions import CadastralAPIError, ErrorType

        if str(parcel_id) == "403":
            raise CadastralAPIError(
                ErrorType.ACCESS_DENIED,
                details={"endpoint": "/cad/parcel-info", "status_code": 403},
            )
        if str(parcel_id) == "0":
            raise CadastralAPIError(ErrorType.PARCEL_NOT_FOUND, details={"parcel_id": "0"})
        return super().get_parcel_info(parcel_id)


def test_sdk_errors_keep_their_type_and_details() -> None:
    res = _run(
        CadastralTools(_FakeClientRefusing()).get_parcel(
            [{"parcel_id": "403"}, {"parcel_id": "0"}, {"parcel_id": "6564741"}]
        )
    )
    denied, missing, found = res["results"]
    assert denied["status"] == "error"
    assert denied["error_type"] == "access_denied"
    assert denied["error_details"] == {"endpoint": "/cad/parcel-info", "status_code": 403}
    assert missing["error_type"] == "parcel_not_found"
    assert missing["error_details"] == {"parcel_id": "0"}
    assert found["status"] == "success"
    assert res["successful"] == 1 and res["failed"] == 2


def test_a_too_large_entry_is_response_too_large(monkeypatch) -> None:
    tools = CadastralTools(_FakeClient())
    monkeypatch.setattr(CadastralTools, "MAX_PARCEL_RESPONSE_CHARS", 10)  # every entry is too large
    entry = _run(tools.get_parcel([{"parcel_id": "6564741"}]))["results"][0]
    assert entry["status"] == "error"
    assert entry["error_type"] == "response_too_large"
    assert "limit=" in entry["error"]
