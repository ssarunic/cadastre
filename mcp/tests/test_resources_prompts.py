"""Resources and prompts run against the SDK as it is.

Both modules once called methods the SDK does not have (``get_parcel_by_id``,
``search_municipalities``) and read fields ParcelInfo does not have; nothing
exercised them. This drives each handler with a fake client that serves the
redacted fixtures through the real client method names.
"""

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "api" / "src"))

from cadastral_api.models.entities import (  # noqa: E402
    CadastralOffice,
    MunicipalitySearchResult,
    ParcelInfo,
)

FIXTURES = REPO / "api" / "src" / "cadastral_api" / "tests" / "fixtures"


def _load(name: str):
    path = REPO / "mcp" / "src" / "cadastral_mcp" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"cadastral_mcp_{name}_standalone", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CadastralResources = _load("resources").CadastralResources
CadastralPrompts = _load("prompts").CadastralPrompts


class _FakeClient:
    def __init__(self) -> None:
        self.parcel = ParcelInfo.model_validate(
            json.loads((FIXTURES / "parcel_info_direct.json").read_text(encoding="utf-8"))
        )
        self.municipalities = [
            MunicipalitySearchResult.model_validate(item)
            for item in json.loads(
                (FIXTURES / "municipalities_savar.json").read_text(encoding="utf-8")
            )
        ]
        self.offices = [
            CadastralOffice.model_validate(item)
            for item in json.loads((FIXTURES / "offices.json").read_text(encoding="utf-8"))
        ]

    def get_parcel_info(self, parcel_id, **kwargs):
        return self.parcel

    def find_municipality(self, search_term=None, office_id=None, department_id=None):
        return [m for m in self.municipalities if search_term in m.code_and_name]

    def list_cadastral_offices(self):
        return self.offices


@pytest.fixture
def client() -> _FakeClient:
    return _FakeClient()


def test_parcel_resource_returns_the_parcel_record(client) -> None:
    result = asyncio.run(CadastralResources(client).get_parcel_resource("6564817"))
    assert result["parcel_number"] == client.parcel.parcel_number
    assert "possession_sheets" in result


def test_municipality_resource_finds_the_record_by_code(client) -> None:
    result = asyncio.run(CadastralResources(client).get_municipality_resource("334979"))
    assert result["municipality_reg_num"] == "334979"
    assert result["municipality_name"] == "SAVAR"
    with pytest.raises(ValueError):
        asyncio.run(CadastralResources(client).get_municipality_resource("000000"))


def test_office_resource_finds_the_office_by_id(client) -> None:
    office = client.offices[0]
    result = asyncio.run(CadastralResources(client).get_office_resource(str(office.id)))
    assert result["name"] == office.name


@pytest.mark.parametrize(
    "prompt", ["explain_ownership_structure", "property_report", "land_use_summary"]
)
def test_single_parcel_prompts_render(client, prompt: str) -> None:
    text = asyncio.run(getattr(CadastralPrompts(client), prompt)("6564817"))
    assert client.parcel.parcel_number in text
    assert client.parcel.cad_municipality_name in text
    assert "Please" in text


def test_compare_parcels_prompt_renders_every_parcel(client) -> None:
    text = asyncio.run(CadastralPrompts(client).compare_parcels(["1", "2"]))
    assert text.count("**Parcel") == 2
    assert client.parcel.parcel_parts[0].name in text
    with pytest.raises(ValueError):
        asyncio.run(CadastralPrompts(client).compare_parcels(["1"]))


def test_due_diligence_report_prompt_names_the_call_the_sections_and_the_terms(client) -> None:
    text = CadastralPrompts(client).due_diligence_report("103/2, 1122/1, 6564817", "SAVAR")
    call = 'build_assembly with parcels=[{"parcel_number": "103/2", "municipality": "SAVAR"}'
    assert call in text
    assert '{"parcel_id": 6564817}' in text and "include_plombe_detail=true" in text
    assert "Croatian" in text and "vlastovnica" in text and "ostavina" in text
    for section in ("1. Header", "2. Verdict roll-up", "3. Parcels", "4. Persons", "5. Closing"):
        assert section in text
    assert "not a legal opinion" in text and "never recompute" in text
    assert "Markdown" in text and "HTML" not in text.split("Format.")[1]
    html = CadastralPrompts(client).due_diligence_report("103/2", "SAVAR", "en", "html")
    assert "English" in html and "self-contained" in html
    with pytest.raises(ValueError):
        CadastralPrompts(client).due_diligence_report(" , ", "SAVAR")
    with pytest.raises(ValueError):
        CadastralPrompts(client).due_diligence_report("103/2", "SAVAR", language="de")
