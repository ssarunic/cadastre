"""A parcel in sheet A can carry a possession sheet with no number."""

from __future__ import annotations

import json
from pathlib import Path

from cadastral_api.models.entities import LandRegistryUnitDetailed, PossessionSheet

FIXTURES = Path(__file__).resolve().parents[2] / "src" / "cadastral_api" / "tests" / "fixtures"


def _first_sheet(unit: dict) -> dict:
    return unit["possessionSheetA1"]["cadParcels"][0]["possessionSheets"][0]


def _unit_with_unnumbered_sheet() -> dict:
    data = json.loads((FIXTURES / "lr_unit_cadparcels.json").read_text())
    unit = data[0] if isinstance(data, list) else data
    # Unit 11216 of main book 221290 lists a parcel whose sheet has no number.
    _first_sheet(unit)["possessionSheetNumber"] = None
    return unit


def test_unit_with_unnumbered_sheet_validates() -> None:
    unit = LandRegistryUnitDetailed.model_validate(_unit_with_unnumbered_sheet())

    sheet = unit.possessory_sheet_a1.cad_parcels[0].possession_sheets[0]
    assert sheet.possession_sheet_number is None
    assert sheet.possession_sheet_id == 14823683
    assert unit.ownership_sheet_b.lr_unit_shares  # the rest of the unit is intact


def test_sheet_without_number_key_validates() -> None:
    sheet = PossessionSheet.model_validate({"possessionSheetId": 1, "cadMunicipalityId": 2387})

    assert sheet.possession_sheet_number is None


def test_sheet_number_still_read_when_present() -> None:
    data = _unit_with_unnumbered_sheet()
    _first_sheet(data)["possessionSheetNumber"] = "625"

    unit = LandRegistryUnitDetailed.model_validate(data)
    sheet = unit.possessory_sheet_a1.cad_parcels[0].possession_sheets[0]
    assert sheet.possession_sheet_number == "625"
