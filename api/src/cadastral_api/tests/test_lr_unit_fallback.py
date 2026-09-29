"""F3: resolving an LR unit when the parcel has no direct lr_unit.

Covers the pure resolution logic (CadastralAPIClient._resolve_lr_unit_ref) and
the model provenance field. The full networked get_lr_unit_from_parcel path is
exercised by integration tests; here we use the redacted 1122/1 fixture, which
has lr_unit=null but a link-derived unit (449 / 21277).
"""

import json
from pathlib import Path

from cadastral_api.client.api_client import CadastralAPIClient
from cadastral_api.models.entities import LandRegistryUnitDetailed, ParcelInfo

FIXTURE = Path(__file__).parent / "fixtures" / "parcel_info_linked.json"


def _parcel() -> ParcelInfo:
    return ParcelInfo.model_validate(json.loads(FIXTURE.read_text(encoding="utf-8")))


def test_resolves_via_parcel_links_when_no_direct_lr_unit() -> None:
    parcel = _parcel()
    assert parcel.lr_unit is None  # the F3 trigger condition
    ref = CadastralAPIClient._resolve_lr_unit_ref(parcel)
    assert ref == ("449", 21277)


def test_returns_none_when_not_in_land_registry() -> None:
    parcel = _parcel()
    parcel.lr_unit = None
    parcel.parcel_links = []
    parcel.lr_units_from_parcel_links = []
    assert CadastralAPIClient._resolve_lr_unit_ref(parcel) is None


def test_prefers_direct_lr_unit_over_links() -> None:
    parcel = _parcel()
    # Synthesize a direct lr_unit; it must win over the link-derived one.
    parcel.lr_unit = parcel.lr_units_from_parcel_links[0].model_copy(
        update={"lr_unit_number": "999", "main_book_id": 12345}
    )
    assert CadastralAPIClient._resolve_lr_unit_ref(parcel) == ("999", 12345)


def test_derived_flag_defaults_false() -> None:
    raw = json.loads(
        (FIXTURE.parent / "lr_unit_lrparcels.json").read_text(encoding="utf-8")
    )
    payload = raw[0] if isinstance(raw, list) else raw
    unit = LandRegistryUnitDetailed.model_validate(payload)
    assert unit.lr_unit_derived_from_links is False


def test_get_lr_unit_from_parcel_integration_sets_derived_flag(monkeypatch) -> None:
    """End-to-end (network mocked): a parcel with lr_unit=null resolves via links
    and the returned unit is flagged lr_unit_derived_from_links=True."""
    parcel = _parcel()  # 1122/1: lr_unit=null, link-derived unit 449
    raw = json.loads(
        (FIXTURE.parent / "lr_unit_lrparcels.json").read_text(encoding="utf-8")
    )
    unit = LandRegistryUnitDetailed.model_validate(raw[0] if isinstance(raw, list) else raw)

    with CadastralAPIClient(base_url="http://localhost:0") as client:
        monkeypatch.setattr(client, "get_parcel_by_number", lambda pn, muni, **kw: parcel)
        monkeypatch.setattr(
            client,
            "get_lr_unit_detailed",
            lambda lr_unit_number, main_book_id, historical_overview=False, **kw: unit,
        )
        result = client.get_lr_unit_from_parcel("1122/1", "334979")

    assert result.lr_unit_number == "449"
    assert result.lr_unit_derived_from_links is True
    # The source parcel (1122/1) is not harmonized; this must propagate so the ZK
    # view can disclose the cadastre divergence.
    assert result.cadastre_harmonized is False
