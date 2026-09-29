"""MCP Tools - AI-invoked actions that perform operations."""

import asyncio
import json
import logging
from typing import Any

from cadastral_api import CadastralAPIClient, GMLParser
from cadastral_api.analysis import (
    AssemblyInput,
    blockers_csv,
    build_assembly,
    check_area,
    compare_registers,
    count_distinct_persons,
    count_owner_flags,
    detect_blockers,
    matrix_csv,
    owner_flags_for_unit,
    parcels_csv,
    parcels_geojson,
    persons_csv,
    resolve_weights,
    unit_key,
)
from cadastral_api.exceptions import CadastralAPIError, ErrorType
from cadastral_api.gis import IndexedParcel, ParcelIndex
from cadastral_api.gis.geometry_ops import parse_ring
from cadastral_api.gis.spatial_index import Relation
from cadastral_api.models.entities import FileStatus, ParcelInfo
from cadastral_api.models.gis_entities import DEFAULT_MAP_ZOOM, ParcelGeometry
from cadastral_api.planning import validate_min_overlap
from cadastral_api.utils import fold_text, is_building_parcel_number, normalize_parcel_number
from pydantic import BaseModel, ConfigDict, Field, model_validator

logger = logging.getLogger(__name__)


#: The six generic keys every ``/search-*`` record carries. The typed models
#: expose them under meaningful names (``main_book_id``, ``sheet_number`` ...),
#: so the raw keys are dropped from tool results to avoid two spellings of
#: one value.
RAW_SEARCH_KEYS = frozenset({"key1", "value1", "key2", "value2", "value3", "display_value1"})


def search_record(model: Any) -> dict[str, Any]:
    """A search-result model as the agent should see it: named fields only."""
    record = model.model_dump(mode="json", exclude=RAW_SEARCH_KEYS)
    if not record.get("source_fields"):
        record.pop("source_fields", None)
    return record


class ResponseTooLargeError(ValueError):
    """A shaped entry exceeds the response ceiling; the message names the smaller options."""


def error_kind(exc: BaseException) -> tuple[str, dict[str, Any]]:
    """The machine-readable kind of a failure, and its details.

    The SDK raises ``CadastralAPIError`` with an ``ErrorType`` (parcel_not_found,
    lr_unit_not_found, rate_limit, access_denied, timeout ...); the handlers
    wrap it in a ``ValueError`` written for the agent, so the chain of causes
    is walked back to it. A ``ResponseTooLargeError`` is ``response_too_large``,
    any other ``ValueError`` (a bad reference, a bad option) is
    ``invalid_request``, anything else ``internal_error``. An empty answer is
    then never read as an empty parcel: the kind says whether nothing exists,
    the server refused, or the request was throttled.
    """
    current: BaseException | None = exc
    while current is not None:
        if isinstance(current, CadastralAPIError):
            details = {
                key: value if isinstance(value, (str, int, float, bool)) else str(value)
                for key, value in current.details.items()
                if value is not None
            }
            return current.error_type.value, details
        if isinstance(current, ResponseTooLargeError):
            return "response_too_large", {}
        current = current.__cause__
    if isinstance(exc, ValueError):
        return "invalid_request", {}
    return "internal_error", {}


def error_fields(exc: BaseException) -> dict[str, Any]:
    """The ``error``, ``error_type`` and ``error_details`` keys of a failed entry."""
    kind, details = error_kind(exc)
    fields: dict[str, Any] = {"error": str(exc), "error_type": kind}
    if details:
        fields["error_details"] = details
    return fields


def _int_area(text: str | None) -> int | None:
    """An area the server wrote as text ("1200", "1200.00", "1 200") as an int, or None."""
    if not text:
        return None
    try:
        return int(float(str(text).replace(" ", "").replace(",", ".")))
    except ValueError:
        return None


class ParcelRef(BaseModel):
    """One parcel to fetch: by ``parcel_id``, or by ``parcel_number`` + ``municipality``."""

    model_config = ConfigDict(extra="forbid")

    # Parcel ids are integers everywhere in the SDK; a numeric string is accepted too.
    parcel_id: int | None = Field(
        default=None,
        description="Parcel id as find_parcel returns it (`parcel_id`); alone it names the parcel",
    )
    parcel_number: str | None = Field(
        default=None,
        description='Cadastral parcel number, e.g. "103/2" or "35/1.ZGR"; needs municipality',
    )
    municipality: str | None = Field(
        default=None,
        description='Cadastral municipality (k.o.) name, e.g. "SAVAR", or code, e.g. "334979"',
    )

    @model_validator(mode="after")
    def _complete(self) -> "ParcelRef":
        if self.parcel_id is None and not (self.parcel_number and self.municipality):
            raise ValueError(
                "a parcel reference needs parcel_id, or parcel_number and municipality"
            )
        return self


class LRUnitRef(BaseModel):
    """One land registry unit to fetch, named in one of three ways.

    - ``lr_unit_number`` + ``main_book_id`` (the direct reference);
    - ``lr_unit_number`` + ``main_book_name`` (the glavna knjiga name, resolved
      through the main-book search);
    - ``parcel_number`` + ``municipality`` (the unit the parcel belongs to,
      resolved through parcel links when the parcel has no direct unit).
    """

    model_config = ConfigDict(extra="forbid")

    # Unit numbers are strings ("769", "374/A") but are often typed as numbers.
    lr_unit_number: str | int | None = Field(
        default=None,
        description=(
            'Land-registry unit number (broj uloška), e.g. "769" or "374/A"; needs '
            "main_book_id or main_book_name"
        ),
    )
    main_book_id: int | None = Field(
        default=None,
        description=(
            "Main book (glavna knjiga) id, as get_parcel returns under data.lr_unit or "
            "find_main_book gives"
        ),
    )
    main_book_name: str | None = Field(
        default=None,
        description=(
            'Main book name, e.g. "SAVAR", resolved through the main-book search instead of'
            " main_book_id"
        ),
    )
    parcel_number: str | None = Field(
        default=None,
        description=(
            'Cadastral parcel number, e.g. "279/6", to fetch the unit the parcel belongs '
            "to; needs municipality"
        ),
    )
    municipality: str | None = Field(
        default=None,
        description='Cadastral municipality (k.o.) name, e.g. "SAVAR", or code, e.g. "334979"',
    )

    @model_validator(mode="after")
    def _complete(self) -> "LRUnitRef":
        if self.lr_unit_number is not None:
            self.lr_unit_number = str(self.lr_unit_number)
        by_unit = bool(self.lr_unit_number) and (
            self.main_book_id is not None or bool(self.main_book_name)
        )
        by_parcel = bool(self.parcel_number) and bool(self.municipality)
        if by_unit == by_parcel:
            raise ValueError(
                "a unit reference is lr_unit_number with main_book_id or main_book_name, "
                "or parcel_number with municipality (not both, not neither)"
            )
        return self

    @property
    def by_parcel(self) -> bool:
        return bool(self.parcel_number)

    def describe(self) -> str:
        if self.by_parcel:
            return f"parcel {self.parcel_number} in {self.municipality}"
        return f"unit {self.lr_unit_number} in main book {self.main_book_id or self.main_book_name}"


class CadastralTools:
    """
    MCP Tools for cadastral operations.

    Tools are executable functions that the AI can invoke to perform
    actions like searching, fetching data, or resolving identifiers.
    """

    def __init__(self, client: CadastralAPIClient) -> None:
        """Initialize tools with a cadastral API client."""
        self.client = client

    async def search_parcel(
        self, parcel_number: str, municipality: str, max_matches: int = 0
    ) -> dict[str, Any]:
        """
        Search for a parcel and return basic information.

        This tool aggregates the 3-step API workflow:
        1. Resolve municipality name to code (if needed)
        2. Search for parcel by number
        3. Return parcel ID and basic info

        Args:
            parcel_number: Cadastral parcel number (e.g., "103/2")
            municipality: Municipality name or registration code
            max_matches: When above 0, also return every search record the
                server answered with (up to this many) under ``matches``, with
                ``matches_total`` and ``matches_truncated``; 0 keeps the
                response to the one chosen parcel. With it, a search from
                which no single parcel can be chosen (nothing found, or only
                the other numbering series) is not an error: ``success`` is
                False, ``parcel_id`` is null, ``match_note`` carries the
                warning and ``matches`` the records.

        Returns:
            Dictionary with parcel search results including parcel_id and,
            when the municipality's GIS data is available, ``map_url`` (the
            interactive map centred on the parcel). The GIS data is downloaded
            on the first request for a municipality and cached afterwards; if
            it cannot be fetched or the parcel is not in it, ``map_url`` is
            simply omitted and the search still succeeds.

            The server matches on a substring, so a number that does not exist
            can still return a longer one ("973" -> 973/1). ``exact_match``
            says whether the returned ``parcel_number`` is the requested
            ``requested_parcel_number``; when it is not, ``match_note`` and
            ``other_matches`` describe what was found instead, and say whether
            the fallback begins with the requested number or merely contains
            it. A building parcel never falls back to a land parcel, or the
            other way round.

        Example:
            >>> await search_parcel("103/2", "SAVAR")
            {
                "parcel_id": "...",
                "parcel_number": "103/2",
                "requested_parcel_number": "103/2",
                "exact_match": True,
                "municipality": "SAVAR",
                "municipality_code": "334979",
                "map_url": "https://oss.uredjenazemlja.hr/map?center=...",
                "success": True
            }
        """
        response, _geometry = await self._search_parcel(parcel_number, municipality, max_matches)
        return response

    async def _search_parcel(
        self, parcel_number: str, municipality: str, max_matches: int
    ) -> tuple[dict[str, Any], ParcelGeometry | None]:
        """``search_parcel``, with the parcel outline it looked up for the map link (or None)."""
        try:
            logger.info(f"Searching for parcel {parcel_number} in {municipality}")

            # Step 1: Resolve municipality if needed
            muni_code = await self._municipality_code(municipality)

            # Step 2: Find parcel. The server matches on a substring, so prefer
            # the exact number (in the API spelling: "35/1.ZGR" -> "*35/1").
            wanted = normalize_parcel_number(parcel_number)
            results = await asyncio.to_thread(self.client.find_parcel, wanted, muni_code)

            matches: dict[str, Any] = {}
            if max_matches > 0:
                # The complete search response, not only the parcel chosen
                # from it: every record the server matched, in its order.
                matches = {
                    "matches": [search_record(r) for r in results[:max_matches]],
                    "matches_total": len(results),
                    "matches_truncated": len(results) > max_matches,
                }

            try:
                if not results:
                    raise ValueError(
                        f"No parcels found matching '{parcel_number}' in {municipality}"
                    )
                result, kind, siblings = self._pick_parcel_match(results, wanted, municipality)
            except ValueError as e:
                if not matches:
                    raise
                # No single parcel answers the request (nothing found, or only
                # the other numbering series); the search records were asked
                # for, so return them with the warning instead of nothing.
                return {
                    "parcel_id": None,
                    "parcel_number": None,
                    "requested_parcel_number": wanted,
                    "exact_match": False,
                    "match_note": str(e),
                    "municipality": municipality,
                    "municipality_code": muni_code,
                    "success": False,
                    **matches,
                }, None
            exact_match = kind == "exact"
            response: dict[str, Any] = {
                "parcel_id": result.parcel_id,
                "parcel_number": result.parcel_number,
                "requested_parcel_number": wanted,
                "exact_match": exact_match,
                "is_building_parcel": result.is_building_parcel,
                "municipality": municipality,
                "municipality_code": muni_code,
                "success": True,
            }
            if not exact_match:
                # The server matches on a substring, so "973" can come back as
                # 973/1 only. Say so instead of passing a different parcel off
                # as the one that was asked for.
                response["match_note"] = self._match_note(wanted, result.parcel_number, kind)
                response["other_matches"] = [
                    r.parcel_number for r in siblings
                ][: self.MAX_OTHER_MATCHES]
            response.update(matches)
            geometry = await asyncio.to_thread(self._geometry_for, result.parcel_number, muni_code)
            if geometry is not None:
                response["map_url"] = geometry.map_url()
            return response, geometry

        except CadastralAPIError as e:
            logger.error(f"Search failed for {parcel_number} in {municipality}: {e}", exc_info=True)
            raise ValueError(
                f"Could not search for parcel '{parcel_number}'. Please verify the parcel number "
                f"and municipality."
            ) from e

    #: Valid register sources for parcel-level ownership data.
    VALID_SOURCES = ("cadastre", "land_registry", "none")

    #: How many further matches to name when the match is not exact.
    MAX_OTHER_MATCHES = 10

    @staticmethod
    def _match_note(wanted: str, found: str, kind: str) -> str:
        """Explain, in the response, why a different parcel came back."""
        if kind == "prefix":
            how = f"'{found}' is the first parcel number that begins with it"
        else:
            how = (
                f"'{found}' merely contains it: no parcel number in this cadastral "
                f"municipality begins with '{wanted}'"
            )
        return (
            f"No parcel numbered '{wanted}' exists in this cadastral municipality. "
            f"{how}; confirm it is the parcel you meant."
        )

    @classmethod
    def _pick_parcel_match(
        cls, results: list[Any], wanted: str, municipality: str
    ) -> tuple[Any, str, list[Any]]:
        """Choose which search result answers ``wanted``, and say how it matched.

        The server matches on a substring, so "*56/" (before it was normalised)
        returned 56/1, 56/2, 256/1, 656/1 ... Two rules keep a fallback from
        answering with a parcel that cannot be the one meant:

        - a building parcel ("*56") never falls back to a land parcel, nor the
          other way round: the two are separate numbering series;
        - a prefix match is preferred over a mere substring match, and the
          response says which of the two happened.

        Returns (result, kind, other candidates of the same kind), where kind is
        "exact", "prefix" or "contains".
        """
        wants_building = is_building_parcel_number(wanted)
        candidates = [
            r for r in results
            if is_building_parcel_number(r.parcel_number) == wants_building
        ]
        if not candidates:
            numbers = [r.parcel_number for r in results]
            if not wants_building and f"*{wanted}" in numbers:
                # The everyday confusion: the number belongs to the building
                # parcel alone. Name the spelling that asks for it.
                raise ValueError(
                    f"There is no land parcel {wanted} in {municipality}, only the "
                    f"building parcel zgr. {wanted}. Ask for it as '{wanted} ZGR'."
                )
            asked, other = (
                ("building parcel", "land") if wants_building else ("land parcel", "building")
            )
            found = ", ".join(numbers[: cls.MAX_OTHER_MATCHES])
            raise ValueError(
                f"No {asked} matching '{wanted}' in {municipality}; the search returned "
                f"only {other} parcels ({found}), which are a separate numbering series."
            )

        exact = next((r for r in candidates if r.parcel_number == wanted), None)
        if exact is not None:
            return exact, "exact", []

        prefixed = [r for r in candidates if r.parcel_number.startswith(wanted)]
        pool = prefixed or candidates
        kind = "prefix" if prefixed else "contains"
        return pool[0], kind, pool[1:]

    @staticmethod
    def _lr_unit_hint(parcel: ParcelInfo) -> dict[str, Any]:
        """Build a routing hint to the land-registry owners for a parcel.

        The direct ``lr_unit`` may be null while the unit is still reachable via
        parcel links; surface whichever is available so the caller can chain to
        get_lr_unit for the true owners.
        """
        unit = parcel.resolved_lr_unit()
        ref = (
            {"lr_unit_number": unit.lr_unit_number, "main_book_id": unit.main_book_id}
            if unit is not None
            else None
        )
        return {
            "message": (
                "Cadastre possessors omitted. For registered owners "
                "(vlasnici / vlastovnica B-list), call get_lr_unit with this "
                "reference (or with the parcel_number and municipality)."
            ),
            "lr_unit_ref": ref,
            "in_land_registry": ref is not None,
            "lr_unit_derived_from_links": parcel.lr_unit_from_links,
        }

    async def get_parcel(
        self,
        parcels: list[ParcelRef | dict[str, Any]],
        source: str = "cadastre",
        offset: int = 0,
        limit: int | None = None,
        possessor_name: str | None = None,
        condominium_unit: str | None = None,
        refresh: bool = False,
    ) -> dict[str, Any]:
        """
        Fetch the detailed cadastre record of one or more parcels.

        ⚠️ Cadastre possessors (posjedovni list) and land-registry owners
        (vlasnici / vlastovnica / B-list) are DIFFERENT registers and frequently
        list different people. Every person record is tagged with a ``register``
        field so the two can never be confused.

        Register selection (``source``):
        - "cadastre" (default): include the possession sheet (posjedovni list),
          i.e. cadastre POSSESSORS - NOT necessarily the registered owners.
        - "land_registry": omit possessors and instead return, per parcel, the
          land-registry unit reference plus a hint to fetch the true owners via
          get_lr_unit.
        - "none": parcel metadata only.

        Args:
            parcels: One or more parcel references (``ParcelRef``): parcel_id, or
                parcel_number + municipality.
            source: One of "cadastre", "land_registry", "none".
            offset: Skip this many possessor records of each parcel (with
                ``source="cadastre"``). Possessors are counted across the
                parcel's possession sheets, in sheet order.
            limit: Return at most this many possessor records per parcel.
                Each cadastre entry carries a ``page`` block (offset, limit,
                total, returned, truncated, next_offset); when ``truncated``
                is true call again with ``offset=next_offset`` for the rest.
                An entry whose possession sheets are too large to return is
                recorded as that parcel's error, naming the smaller options.
                ``total_possessors`` counts records and ``distinct_possessors``
                the different names among them (a person holding two units is
                two records).
            possessor_name: Keep only the possessors whose name contains every
                word of this text (case and diacritics ignored, words in any
                order), so a person can be found on a large sheet without
                paging through it. ``page.total`` then counts the matching
                records; ``total_possessors`` still counts the whole parcel.
            condominium_unit: Keep only the possessors of this condominium
                unit (``condominium_share_number``; "E-16", "E16" and "16"
                are the same unit).

        Returns:
            Dictionary with ``results`` (one entry per reference, in order),
            counts, and the resolved ``source``. Each successful entry also
            carries ``map_url`` (the interactive map centred on the parcel)
            when the municipality's GIS data is available; it is omitted
            otherwise. An entry resolved from a fallback match rather than the
            exact number carries ``exact_match`` False with
            ``requested_parcel_number`` and ``match_note``.
        """
        if source not in self.VALID_SOURCES:
            raise ValueError(
                f"Invalid source '{source}'. Expected one of {self.VALID_SOURCES}."
            )
        if not parcels:
            raise ValueError("Give at least one parcel reference.")
        if limit is not None and limit < 1:
            raise ValueError(f"limit must be at least 1, got {limit}")
        if offset < 0:
            raise ValueError(f"offset must not be negative, got {offset}")
        possessor_filter = self._possessor_filter(possessor_name, condominium_unit)
        if possessor_filter and source != "cadastre":
            raise ValueError(
                'possessor_name and condominium_unit filter the possession sheet, '
                'which only source="cadastre" returns.'
            )

        logger.info(
            f"Fetching {len(parcels)} parcel(s) (source={source}, offset={offset}, "
            f"limit={limit}, filter={possessor_filter})"
        )
        results: list[dict[str, Any]] = []
        for spec in parcels:
            try:
                ref = spec if isinstance(spec, ParcelRef) else ParcelRef.model_validate(spec)
            except ValueError as e:
                results.append({"status": "error", **error_fields(e), "ref": spec})
                continue
            try:
                results.append(
                    await self._get_one_parcel(
                        ref, source, offset, limit, possessor_filter, refresh=refresh
                    )
                )
            except Exception as e:  # noqa: BLE001 - recorded per item on purpose
                logger.error(f"Failed to fetch parcel {ref}: {e}")
                results.append({
                    "status": "error",
                    **error_fields(e),
                    "ref": ref.model_dump(exclude_none=True),
                })

        successful = sum(1 for r in results if r["status"] == "success")
        return {
            "results": results,
            "total": len(parcels),
            "successful": successful,
            "failed": len(results) - successful,
            "source": source,
        }

    async def _get_one_parcel(
        self,
        ref: ParcelRef,
        source: str,
        offset: int = 0,
        limit: int | None = None,
        possessor_filter: dict[str, Any] | None = None,
        *,
        refresh: bool = False,
    ) -> dict[str, Any]:
        """The ``results`` entry of one parcel reference (raises on failure)."""
        parcel, geometry, search_result = await self._load_parcel(ref, refresh=refresh)
        result_data = parcel.model_dump(mode="json")
        # Retrieval provenance describes the entry, so it sits next to
        # ``register`` rather than inside the record it is about.
        provenance = result_data.pop("provenance", None)

        # A parcel whose unit is reachable only through parcel links has a
        # null ``lr_unit``; put the resolved unit there, as promised, and let
        # ``lr_reference_shape`` ("linked") say where it came from. The links
        # themselves stay in the dump.
        if result_data.get("lr_unit") is None:
            resolved = parcel.resolved_lr_unit()
            if resolved is not None:
                result_data["lr_unit"] = resolved.model_dump(mode="json")

        # Possession sheets are CADASTRE data; only include them when
        # cadastre possessors were explicitly requested.
        page: dict[str, Any] | None = None
        if source != "cadastre":
            result_data.pop("possession_sheets", None)
        else:
            page = self._window_possessors(result_data, offset, limit, possessor_filter)
            fetched_at = (provenance or {}).get("retrieved_at")
            if fetched_at:
                page["fetched_at"] = fetched_at
        if source == "land_registry":
            result_data["land_registry_hint"] = self._lr_unit_hint(parcel)

        entry: dict[str, Any] = {
            "status": "success",
            "ref": ref.model_dump(exclude_none=True),
            "register": source,
            "provenance": provenance,
            "cadastre_lr_harmonized": parcel.is_harmonized,
            "data": result_data,
        }
        if page is not None:
            entry["total_possessors"] = parcel.total_possessors
            entry["distinct_possessors"] = self._distinct_possessors(parcel)
            if possessor_filter:
                entry["possessor_filter"] = possessor_filter
                entry["matching_possessors"] = page["total"]
            entry["possessors_truncated"] = page["truncated"]
            entry["page"] = page
            self._check_parcel_size(entry, parcel, page)
        # A fallback match is not the parcel that was asked for; carry the
        # warning out of search_parcel rather than losing it here.
        if search_result is not None and not search_result["exact_match"]:
            entry["exact_match"] = False
            entry["requested_parcel_number"] = search_result["requested_parcel_number"]
            entry["match_note"] = search_result["match_note"]
        if geometry is not None:
            entry["map_url"] = geometry.map_url()
        entry["area_check"] = self._area_check(parcel, geometry)
        return entry

    async def _load_parcel(
        self, ref: ParcelRef, *, refresh: bool = False
    ) -> tuple[ParcelInfo, ParcelGeometry | None, dict[str, Any] | None]:
        """The record a reference names, its outline (best effort) and the search response.

        A parcel given by number is searched first (which also looks up the
        outline for the map link); one given by id is fetched directly and
        its outline looked up afterwards, once. The outline serves the map
        link and the graphical area of ``area_check``; None when the
        municipality's GIS data has no such parcel.
        """
        search_result: dict[str, Any] | None = None
        geometry: ParcelGeometry | None = None
        if ref.parcel_id is not None:
            parcel_id = ref.parcel_id
        else:
            assert ref.parcel_number is not None and ref.municipality is not None
            search_result, geometry = await self._search_parcel(
                ref.parcel_number, ref.municipality, 0
            )
            parcel_id = search_result["parcel_id"]
        parcel = await asyncio.to_thread(self.client.get_parcel_info, parcel_id, refresh=refresh)
        if search_result is None:
            geometry = await asyncio.to_thread(
                self._geometry_for, parcel.parcel_number, parcel.cad_municipality_reg_num
            )
        return parcel, geometry, search_result

    #: Relative difference between two areas of one parcel above which they disagree.
    AREA_TOLERANCE = 0.05

    @classmethod
    def _area_check(cls, parcel: ParcelInfo, geometry: ParcelGeometry | None) -> dict[str, Any]:
        """Compare the areas the registers give one parcel (``check_area``).

        The cadastre area is the record's own; the graphical area comes from
        the cached GIS outline when there is one; the land-register area is
        the one the cadastre carries on the parcel link (the "linked" shape
        only). Sheet A of the unit is not read here, since that costs a
        land-registry request: get_lr_unit with detail="parcels" has it.
        """
        lr_area: int | None = None
        note: str | None = None
        links = [link for link in parcel.parcel_links or [] if link.area]
        same_number = [link for link in links if link.parcel_number == parcel.parcel_number]
        if same_number:
            lr_area = _int_area(same_number[0].area)
        elif len(links) == 1:
            lr_area = _int_area(links[0].area)
            note = (
                f"land-register area is that of land-register parcel {links[0].parcel_number}, "
                f"linked to this cadastre parcel"
            )
        if lr_area is None:
            note = (
                'land-register area not on the cadastre record; get_lr_unit detail="parcels" '
                "reads it from sheet A"
            )
        return check_area(
            cadastre_m2=parcel.area_numeric or None,
            land_registry_m2=lr_area,
            gis_m2=geometry.povrsina_graficka if geometry is not None else None,
            tolerance=cls.AREA_TOLERANCE,
            note=note,
        ).model_dump(mode="json")

    @staticmethod
    def _fold(text: str) -> str:
        """Text for matching: lower case, no diacritics, single spaces."""
        return fold_text(text)

    @staticmethod
    def _unit_key(unit: str) -> str:
        """A condominium unit number for comparison: "E-16", "E16" and "16" agree."""
        return unit_key(unit)

    @classmethod
    def _possessor_filter(
        cls, possessor_name: str | None, condominium_unit: str | None
    ) -> dict[str, Any] | None:
        """The filter the caller asked for, or None; validated once per call."""
        filter_: dict[str, Any] = {}
        if possessor_name is not None:
            if not cls._fold(possessor_name):
                raise ValueError("possessor_name must not be blank")
            filter_["possessor_name"] = possessor_name
        if condominium_unit is not None:
            if not cls._unit_key(condominium_unit):
                raise ValueError("condominium_unit must not be blank")
            filter_["condominium_unit"] = condominium_unit
        return filter_ or None

    @classmethod
    def _possessor_matches(cls, possessor: dict[str, Any], filter_: dict[str, Any]) -> bool:
        """Whether a dumped possessor record passes the filter."""
        name = filter_.get("possessor_name")
        if name is not None:
            haystack = cls._fold(possessor.get("name") or "")
            if not all(word in haystack for word in cls._fold(name).split()):
                return False
        unit = filter_.get("condominium_unit")
        if unit is not None:
            number = possessor.get("condominium_share_number")
            if number is None or cls._unit_key(str(number)) != cls._unit_key(unit):
                return False
        return True

    @classmethod
    def _window_possessors(
        cls,
        result_data: dict[str, Any],
        offset: int,
        limit: int | None,
        possessor_filter: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Keep the window ``[offset, offset + limit)`` of possessor records in a parcel dump.

        Possessors are counted across the parcel's possession sheets, in sheet
        order, and the window is cut through that flat sequence: a condominium
        keeps its hundreds of possessors on one sheet, so paging by sheet would
        change nothing. Every sheet stays in the dump with its header and a
        ``total_possessors`` of its own, holding only the possessors that fall
        inside the window (none, if the window is elsewhere), so the sheet
        numbers are always visible and the continuation contract never skips
        a record. With a ``possessor_filter`` only the matching records are
        counted and windowed; ``total_possessors`` on the sheet still counts
        them all.

        Returns the ``page`` block for the entry.
        """
        sheets = result_data.get("possession_sheets") or []
        matching: list[list[dict[str, Any]]] = []
        for sheet in sheets:
            possessors = sheet.get("possessors") or []
            sheet["total_possessors"] = len(possessors)
            if possessor_filter:
                possessors = [p for p in possessors if cls._possessor_matches(p, possessor_filter)]
            matching.append(possessors)
        total = sum(len(possessors) for possessors in matching)
        end = total if limit is None else offset + limit
        seen = 0
        returned = 0
        for sheet, possessors in zip(sheets, matching):
            start_here = max(offset - seen, 0)
            end_here = max(min(end - seen, len(possessors)), 0)
            sheet["possessors"] = possessors[start_here:end_here] if start_here < end_here else []
            returned += len(sheet["possessors"])
            seen += len(possessors)
        return cls._page(offset, limit, total, returned)

    @staticmethod
    def _distinct_possessors(parcel: Any) -> int:
        """How many different people the parcel's possessor records name.

        A person who holds two units of a condominium (a flat and a storage
        room, say) is two possessor records, often with two addresses; the
        records are kept as the cadastre holds them and this count, across
        every sheet, says how many people that is. Names are compared with
        ``count_distinct_persons`` (case, diacritics, spacing and punctuation
        ignored), the same identity the land-registry ``distinct_owners`` and
        the register comparison use. Two different people with the same name
        count once.
        """
        return count_distinct_persons(
            (possessor.name, None)
            for sheet in parcel.possession_sheets
            for possessor in sheet.possessors
        )

    @classmethod
    def _check_parcel_size(
        cls, entry: dict[str, Any], parcel: Any, page: dict[str, Any]
    ) -> None:
        """Refuse a parcel entry too large to be read, with a way forward.

        A parcel under a large condominium carries hundreds of possessors on
        its possession sheet; returned whole it overruns the caller's
        response limit and is lost. The ceiling and the message follow the
        land-registry levels (``_check_size``).
        """
        size = len(json.dumps(entry, ensure_ascii=False))
        if size <= cls.MAX_PARCEL_RESPONSE_CHARS:
            return
        returned = page.get("returned") or 0
        # Possessor records are uniform, so the size scales with the window:
        # suggest the largest window that fits, with a tenth to spare.
        fits = int(returned * cls.MAX_PARCEL_RESPONSE_CHARS / size * 0.9) if returned else 10
        smaller = max(1, fits)
        raise ResponseTooLargeError(
            f"The cadastre record of parcel {parcel.parcel_number} is {size:,} "
            f"characters ({returned} of {page['total']} possessor records in this "
            f"window), too large to return in one response. Pass a smaller limit "
            f"(e.g. limit={smaller}) and page through the possessors with offset "
            f"(the page block says where to continue), possessor_name or "
            f"condominium_unit to pick the records you need, or source=\"none\" "
            f"for the parcel without its possessors (source=\"land_registry\" for "
            f"the land-registry reference instead)."
        )

    @staticmethod
    def _municipality_record(muni: Any) -> dict[str, Any]:
        """A municipality search record as the agent should see it."""
        return {
            "code": muni.municipality_reg_num,
            "name": muni.municipality_name,
            "full_name": muni.display_value,
            "municipality_id": muni.municipality_id,
            "office_id": muni.institution_id,
            "department_id": muni.department_id,
        }

    async def resolve_municipality(self, name_or_code: str) -> dict[str, Any]:
        """
        Resolve municipality name (or code) to its complete search record.

        Args:
            name_or_code: Municipality name (e.g., "SAVAR") or code (e.g., "334979")

        Returns:
            Dictionary with ``code`` (the registration number every parcel
            search needs), ``name``, ``full_name`` (with the cadastral office),
            ``municipality_id``, ``office_id`` and ``department_id``. When the
            name matched several municipalities the first is returned and the
            others are listed under ``other_matches``.

        Example:
            >>> await resolve_municipality("SAVAR")
            {"code": "334979", "name": "SAVAR", "full_name": "334979 SAVAR, ZADAR, PUK ZADAR",
             "municipality_id": 2387, "office_id": 114, "department_id": 116}
        """
        try:
            logger.info(f"Resolving municipality: {name_or_code}")
            municipalities = await asyncio.to_thread(self.client.find_municipality, name_or_code)
            if name_or_code.isdigit():
                municipalities = [
                    m for m in municipalities if m.municipality_reg_num == name_or_code
                ]
            if not municipalities:
                raise ValueError(f"Municipality '{name_or_code}' not found")

            record = self._municipality_record(municipalities[0])
            if len(municipalities) > 1:
                record["other_matches"] = [
                    self._municipality_record(m)
                    for m in municipalities[1 : 1 + self.MAX_OTHER_MATCHES]
                ]
                record["matches_total"] = len(municipalities)
            return record

        except CadastralAPIError as e:
            logger.error(f"Failed to resolve municipality {name_or_code}: {e}", exc_info=True)
            raise ValueError(f"Could not resolve municipality '{name_or_code}'.") from e

    #: Municipality records returned by list_municipalities unless asked otherwise.
    DEFAULT_MUNICIPALITY_LIMIT = 200

    async def list_municipalities(
        self,
        search: str | None = None,
        office_id: str | int | None = None,
        department_id: str | int | None = None,
        offset: int = 0,
        limit: int | None = DEFAULT_MUNICIPALITY_LIMIT,
    ) -> dict[str, Any]:
        """
        List cadastral municipalities, filtered by name, office or department.

        Args:
            search: Name or code to match (substring); None for all.
            office_id: Cadastral office id (``id`` from list_cadastral_offices).
            department_id: Department id within the office.
            offset: Skip this many records.
            limit: Return at most this many (default 200; None for all).

        Returns:
            {"municipalities": [record, ...], "total": n, "page": {...}} where
            each record is shaped as in resolve_municipality.
        """
        if limit is not None and limit < 1:
            raise ValueError(f"limit must be at least 1, got {limit}")
        if offset < 0:
            raise ValueError(f"offset must not be negative, got {offset}")
        try:
            logger.info(
                f"Listing municipalities (search={search}, office={office_id}, "
                f"department={department_id})"
            )
            municipalities = await asyncio.to_thread(
                self.client.find_municipality,
                search,
                office_id=office_id,
                department_id=department_id,
            )
            window = self._window(municipalities, offset, limit)
            return {
                "municipalities": [self._municipality_record(m) for m in window],
                "total": len(municipalities),
                "page": self._page(offset, limit, len(municipalities), len(window)),
            }
        except CadastralAPIError as e:
            logger.error(f"Failed to list municipalities: {e}", exc_info=True)
            raise ValueError("Could not list municipalities.") from e

    async def get_parcel_geometry(
        self,
        parcel_number: str,
        municipality: str,
        format: str = "geojson",
        zoom: int = DEFAULT_MAP_ZOOM,
    ) -> dict[str, Any] | str:
        """
        Get parcel boundary geometry.

        Downloads and caches GML data if needed, then extracts geometry.

        Args:
            parcel_number: Cadastral parcel number (e.g., "103/2")
            municipality: Municipality name or registration code
            format: Output format - "geojson", "wkt", or "dict"
            zoom: Zoom level of the ``map_url`` link (geojson and dict output)

        Returns:
            Geometry data in requested format. "geojson" and "dict" include a
            ``map_url`` pointing the interactive map at the parcel; "wkt" is
            the bare polygon.

        Example:
            >>> await get_parcel_geometry("103/2", "SAVAR", format="geojson")
            {
                "type": "Feature",
                "geometry": {...},
                "properties": {...}
            }
        """
        try:
            logger.info(
                f"Fetching geometry for {parcel_number} in {municipality} (format: {format})"
            )

            # Resolve municipality
            muni_code = await self._municipality_code(municipality)

            # Fetch geometry using SDK (None when the parcel is not in the GML)
            geometry = await asyncio.to_thread(
                self.client.get_parcel_geometry, parcel_number, muni_code
            )
            if geometry is None:
                raise ValueError(
                    f"Parcel '{parcel_number}' has no geometry in the GIS data for "
                    f"municipality '{municipality}' ({muni_code}). Check the parcel "
                    f"number; if the cached GIS data may be stale, clear it for this "
                    f"municipality and try again."
                )

            # Return in requested format
            if format.lower() == "geojson":
                return geometry.to_geojson(zoom=zoom)
            elif format.lower() == "wkt":
                return geometry.to_wkt()
            else:  # dict
                data = geometry.model_dump(mode="json")
                data["map_url"] = geometry.map_url(zoom)
                return data

        except CadastralAPIError as e:
            logger.error(f"Failed to fetch geometry for {parcel_number}: {e}", exc_info=True)
            raise ValueError(
                f"Could not retrieve geometry for parcel '{parcel_number}'. "
                f"GIS data may not be available."
            ) from e

    async def get_parcel_zoning(
        self,
        parcel_number: str,
        municipality: str,
        include_geometry: bool = False,
        min_overlap: float = 0.02,
    ) -> dict[str, Any]:
        """
        Screening of a parcel against the spatial plans' building areas.

        Matches the parcel outline (from the cached cadastral GIS data)
        against the building areas derived from the plans in force and
        reports the zones that cover it with the estimated share of the
        parcel each one covers. It never determines whether anything may be
        built (``buildability`` is always ``"unknown"``). The blocking work
        (GIS download, WFS calls over several mirrors) runs in a worker
        thread so the event loop stays free.

        Args:
            parcel_number: Cadastral parcel number (e.g., "103/2")
            municipality: Municipality name or registration code
            include_geometry: Include the zone polygons (EPSG:3765) in the answer
            min_overlap: Zones covering a smaller share of the parcel go to
                ``below_threshold`` (0 to 1, default 0.02)

        Returns:
            Dictionary with ``status`` (``inside_settlement``, ``detached_zone``,
            ``touches_below_threshold`` or ``outside``), ``buildability``
            (always ``"unknown"``), ``matches`` (zone with designation code, text,
            zone name, plan name and id, generation of the code list, overlap
            fraction and m2), ``plans``, ``dataset`` (name, state and the
            disclaimer that must accompany any use), ``summary`` and a
            ``generation_note``.
        """
        min_overlap = validate_min_overlap(min_overlap)
        try:
            logger.info(f"Fetching zoning for {parcel_number} in {municipality}")
            muni_code = await self._municipality_code(municipality)
            zoning = await asyncio.to_thread(
                self.client.get_parcel_zoning, parcel_number, muni_code, min_overlap
            )
            if zoning is None:
                raise ValueError(
                    f"Parcel '{parcel_number}' has no geometry in the GIS data for "
                    f"municipality '{municipality}' ({muni_code}), so it cannot be matched "
                    f"against the spatial plans. Check the parcel number; if the cached GIS "
                    f"data may be stale, clear it for this municipality and try again."
                )
            exclude = None
            if not include_geometry:
                without_polygons = {"__all__": {"zone": {"polygons"}}}
                exclude = {"matches": without_polygons, "below_threshold": without_polygons}
            data = zoning.model_dump(mode="json", exclude=exclude)
            data["summary"] = zoning.summary()
            data["generation_note"] = (
                "Designation codes follow the code list of the plan's generation: in old "
                "plans T1 is a hotel zone, T2 a tourist settlement and T3 a camp; in plans "
                "made under the 2024 Pravilnik T1 is tourism inside a settlement, T2 a "
                "detached zone with accommodation and T3 one without."
            )
            return data
        except CadastralAPIError as e:
            logger.error(f"Failed to fetch zoning for {parcel_number}: {e}", exc_info=True)
            raise ValueError(
                f"Could not match parcel '{parcel_number}' against the building areas: "
                f"{e}. {self._planning_endpoint_hint()}"
            ) from e

    def _planning_endpoint_hint(self) -> str:
        """Say which building-areas endpoints were tried and, when they are the
        default (the mock server's imitation) on a server that is not the mock,
        how to point the lookup at the real WFS."""
        planning = getattr(self.client, "planning", None)
        urls = list(getattr(planning, "base_urls", None) or [])
        if not urls:
            return "The building-areas service may be unavailable."
        hint = f"Building-areas WFS endpoint(s) tried: {', '.join(urls)}."
        default_path = urls[0].endswith("/planning/wfs")
        on_mock = "localhost" in urls[0] or "127.0.0.1" in urls[0]
        if default_path and not on_mock:
            hint += (
                " That is the default endpoint, the mock server's imitation of the WFS, "
                "which does not exist on other servers. Set CADASTRAL_PLANNING_WFS_URLS "
                "to the building-areas WFS mirror(s) (see .env.example; verify your "
                "rights to use them first) and restart the MCP server."
            )
        else:
            hint += " The service may be unavailable; try again later."
        return hint

    async def list_cadastral_offices(self, filter_name: str | None = None) -> dict[str, Any]:
        """
        List all cadastral offices, optionally filtered by name.

        Args:
            filter_name: Optional filter string to match office names

        Returns:
            Dictionary with list of offices and count

        Example:
            >>> await list_cadastral_offices()
            {
                "offices": [...],
                "count": 15
            }
        """
        try:
            logger.info(f"Listing cadastral offices (filter: {filter_name})")

            offices = await asyncio.to_thread(self.client.list_cadastral_offices)

            # Apply filter if provided
            if filter_name:
                filter_lower = filter_name.lower()
                offices = [
                    office for office in offices
                    if filter_lower in office.name.lower()
                ]

            return {
                "offices": [office.model_dump(mode="json") for office in offices],
                "count": len(offices),
            }

        except CadastralAPIError as e:
            logger.error(f"Failed to list cadastral offices: {e}", exc_info=True)
            raise ValueError("Could not retrieve cadastral offices.") from e

    #: Valid detail levels for land-registry unit output.
    VALID_DETAIL = ("summary", "ownership", "shares", "parcels", "encumbrances", "full")

    #: The list that ``offset`` and ``limit`` page through at each detail level.
    PAGED_LIST = {
        "ownership": "owners",
        "shares": "shares",
        "full": "shares",
        "parcels": "parcels",
        "encumbrances": "entry_groups",
    }

    @staticmethod
    def _page(
        offset: int,
        limit: int | None,
        total: int,
        returned: int,
        *,
        fetched_at: str | None = None,
    ) -> dict[str, Any]:
        """The paging block of a shaped unit: which window of the list came back.

        ``fetched_at`` is when the upstream sent the record the window was
        cut from (the original fetch when it was served from the response
        cache), so the agent can say how old the record is.
        """
        truncated = offset + returned < total
        page: dict[str, Any] = {
            "offset": offset,
            "limit": limit,
            "total": total,
            "returned": returned,
            "truncated": truncated,
        }
        if truncated:
            page["next_offset"] = offset + returned
        if fetched_at is not None:
            page["fetched_at"] = fetched_at
        return page

    @staticmethod
    def _window(rows: list[Any], offset: int, limit: int | None) -> list[Any]:
        """The window ``[offset, offset + limit)`` of a list (all of it past offset if no limit)."""
        return rows[offset:] if limit is None else rows[offset : offset + limit]

    @classmethod
    def _name_matches(cls, name: str | None, wanted: str) -> bool:
        """Whether a register name contains every word of ``wanted``.

        Folded with ``_fold`` (case and diacritics ignored), words in any
        order: the registers write the surname first ("ŠARUNIĆ SAŠA"), people
        write it last, and a caller unsure of the spelling passes the surname
        alone.
        """
        haystack = cls._fold(name or "")
        return all(word in haystack for word in cls._fold(wanted).split())

    @classmethod
    def _owner_name_filter(cls, owner_name: str | None, detail: str) -> str | None:
        """The owner-name filter as given, or None; validated once per call."""
        if owner_name is None:
            return None
        if not cls._fold(owner_name):
            raise ValueError("owner_name must not be blank")
        if detail not in cls.NAME_FILTERED_DETAIL:
            raise ValueError(
                f"owner_name filters owners, which detail \"{detail}\" does not "
                f"return; use one of {cls.NAME_FILTERED_DETAIL}."
            )
        return owner_name

    @classmethod
    def _ownership_rows(
        cls,
        lr_unit: Any,
        offset: int,
        limit: int | None,
        owner_name: str | None = None,
        flag_rows: list[Any] | None = None,
    ) -> tuple[list[dict[str, Any]], int, int, bool]:
        """Owner rows for an LR unit, filtered by name and windowed at offset/limit.

        Returns (rows, total_owners, matching_owners, truncated); the window
        and ``truncated`` walk the matching rows (all of them without a
        filter). The canonical row shape comes from
        OwnershipSheetB.owner_rows() (shared with the CLI); ``flag_rows``
        (``owner_flags_for_unit``, in the same order) puts each owner's
        inferred ``flags`` on the row.
        """
        rows = lr_unit.ownership_sheet_b.owner_rows()
        for row, flagged in zip(rows, flag_rows or [], strict=bool(flag_rows)):
            row["flags"] = flagged.flags.model_dump(mode="json")
        total = len(rows)
        if owner_name is not None:
            rows = [row for row in rows if cls._name_matches(row.get("name"), owner_name)]
        window = cls._window(rows, offset, limit)
        return window, total, len(rows), offset + len(window) < len(rows)

    #: Characters of JSON a full dump may reach before it is refused. A large
    #: condominium runs to hundreds of shares, each with its own registration
    #: entry, and overruns an agent's context long before it is read; refusing
    #: with a way forward beats returning something unusable. The ceiling is
    #: well under a typical MCP client's per-response limit, since a response
    #: the client truncates is worse than one it never asked for.
    MAX_FULL_RESPONSE_CHARS = 50_000

    #: The same ceiling for one parcel's cadastre entry. Possessor records are
    #: flat and uniform (a condominium's sheet is thousands of them at a few
    #: hundred characters each, no nested entries), so the cost of a low
    #: ceiling is paid in calls: at 50,000 a building of 3,000 possessors is
    #: 25 pages. 100,000 halves that and is still an order of magnitude under
    #: the per-response limit of the MCP clients seen so far.
    MAX_PARCEL_RESPONSE_CHARS = 100_000

    @staticmethod
    def _sub_shares(share: dict[str, Any]) -> list[dict[str, Any]]:
        """The nested share dicts of a share (an apartment's co-owners)."""
        nested = share.get("sub_shares_and_entries") or []
        return [item for item in nested if isinstance(item, dict) and "owners" in item]

    @classmethod
    def _count_owner_records(cls, shares: list[dict[str, Any]]) -> int:
        """Owner records held by these shares and their sub-shares."""
        total = 0
        for share in shares:
            total += len(share.get("owners") or [])
            total += cls._count_owner_records(cls._sub_shares(share))
        return total

    @classmethod
    def _share_matches(cls, share: dict[str, Any], owner_name: str) -> bool:
        """Whether a dumped share, or one of its sub-shares, has an owner of that name."""
        if any(
            cls._name_matches(owner.get("name"), owner_name)
            for owner in share.get("owners") or []
        ):
            return True
        return any(cls._share_matches(sub, owner_name) for sub in cls._sub_shares(share))

    @classmethod
    def _window_shares(
        cls,
        dump: dict[str, Any],
        offset: int,
        limit: int | None,
        owner_name: str | None = None,
    ) -> tuple[int, int, int, int]:
        """Keep the window ``[offset, offset + limit)`` of top-level shares in a sheet-B dump.

        ``dump`` is a full unit dump or a bare sheet-B dump. A share is kept
        whole, with its sub-shares (an apartment's co-owners) and its entries;
        the shares outside the window are dropped whole. Paging by share, not
        by owner record, keeps every share reachable: a share without owners
        (one that holds only annotations) is a page item like any other, so
        the continuation contract never skips it. Dropping shares rather than
        emptying them matters because a condominium keeps its weight in the
        shares themselves, each with its own description and registration
        entry.

        With ``owner_name`` only the shares holding a matching owner (in the
        share itself or in a sub-share) are page items, and the window walks
        those; a matching share is kept whole, its co-owners included.

        Returns (total_shares, matching_shares, returned_shares,
        shares_omitted), the last counting sub-shares of the dropped shares
        too; ``matching_shares`` equals ``total_shares`` without a filter.
        """
        sheet = dump.get("ownership_sheet_b", dump) or {}
        shares = sheet.get("lr_unit_shares") or []
        matching = shares
        if owner_name is not None:
            matching = [share for share in shares if cls._share_matches(share, owner_name)]
        window = cls._window(matching, offset, limit)
        sheet["lr_unit_shares"] = window
        omitted = cls._count_shares(shares) - cls._count_shares(window)
        return len(shares), len(matching), len(window), omitted

    @classmethod
    def _count_shares(cls, shares: list[dict[str, Any]]) -> int:
        """Number of share dicts here and below (for the omitted-share count)."""
        return sum(1 + cls._count_shares(cls._sub_shares(share)) for share in shares)

    @staticmethod
    def _identity(lr_unit: Any) -> dict[str, Any]:
        """The fields that name a unit, present at every detail level."""
        return {
            "lr_unit_number": lr_unit.lr_unit_number,
            "main_book_id": lr_unit.main_book_id,
            "main_book_name": lr_unit.main_book_name,
            "institution_id": lr_unit.institution_id,
            "institution_name": lr_unit.institution_name,
            "lr_unit_derived_from_links": lr_unit.lr_unit_derived_from_links,
            "provenance": (
                lr_unit.provenance.as_dict()
                if getattr(lr_unit, "provenance", None) is not None
                else None
            ),
        }

    #: The detail levels ``owner_name`` applies to: the ones whose page items
    #: carry owners.
    NAME_FILTERED_DETAIL = ("ownership", "shares", "full")

    @classmethod
    def _shape_lr_unit(
        cls,
        lr_unit: Any,
        detail: str,
        limit: int | None = None,
        offset: int = 0,
        owner_name: str | None = None,
        condominium_unit: str | None = None,
        plombe_detail: dict[str, FileStatus] | None = None,
    ) -> dict[str, Any]:
        """Shape an LR unit for output at the requested detail level.

        - "summary": identity + summary statistics only.
        - "ownership" (default): B-list owners (with structured shares) + summary;
          drops geometry, Sheet A2, the C-sheet, and raw internal IDs.
        - "shares": sheet B as the register holds it (raw shares with their
          sub-shares, entries and status, plus the sheet-level entries).
        - "parcels": sheet A (the parcels of the unit, with sheet A2 entries).
        - "encumbrances": sheet C (the encumbrance entry groups).
        - "full": every sheet (raw model dump) + summary.

        ``offset`` and ``limit`` page through the list the level is about
        (``PAGED_LIST``): owner records for "ownership", top-level shares for
        "shares" and "full", parcels for "parcels", entry groups for
        "encumbrances". In "shares" and "full" the shares outside the window
        are dropped whole (counted in ``shares_omitted``), since a
        condominium's weight is in the shares themselves, not only in their
        owners. Every level but "summary" carries a ``page`` block saying what
        window came back.

        ``owner_name`` keeps only the owner rows of that name ("ownership") or
        the shares holding such an owner ("shares", "full"); the page then
        walks the matches, ``matching_owners`` / ``matching_shares`` count
        them and the totals still describe the whole sheet. The other levels
        return no owners and refuse it.

        Every level carries ``sale_blockers``: what is registered against
        the unit that bears on a sale, narrowed by ``owner_name`` or
        ``condominium_unit`` to one owner's shares or one flat, enriched with
        ``plombe_detail`` when the caller fetched it. "ownership" and
        "encumbrances" carry the blockers themselves; the other levels the
        verdict, the counts and the rule (a large condominium's list runs to
        tens of kilobytes, too much for every page of the raw sheets).
        Every level but "parcels" and "encumbrances" carries
        ``owner_flags_summary``; "ownership" puts each owner's ``flags`` on
        the row.
        """
        if detail not in cls.VALID_DETAIL:
            raise ValueError(
                f"Invalid detail '{detail}'. Expected one of {cls.VALID_DETAIL}."
            )
        owner_name = cls._owner_name_filter(owner_name, detail)
        blockers = detect_blockers(
            lr_unit,
            owner_name=owner_name,
            condominium_unit=condominium_unit,
            plombe_detail=plombe_detail,
        ).model_dump(mode="json", exclude_none=True)
        brief = cls._blockers_brief(blockers)
        # The owner flags are read once per call, and only on the levels that
        # show them ("parcels" and "encumbrances" carry no owners).
        flag_rows = (
            owner_flags_for_unit(lr_unit) if detail not in ("parcels", "encumbrances") else []
        )
        flags_summary = count_owner_flags(row.flags for row in flag_rows)
        summary = lr_unit.summary()
        provenance = getattr(lr_unit, "provenance", None)
        fetched_at = provenance.retrieved_at if provenance is not None else None
        is_condo = lr_unit.is_condominium()
        # Different people among the owner records, whatever the window or
        # filter: one person holding two shares is two records and one owner.
        distinct_owners = count_distinct_persons(
            (owner.name, owner.tax_number) for owner in lr_unit.get_all_owners()
        )
        condo_fields: dict[str, Any] = {}
        if is_condo:
            condo_fields = {
                "is_condominium": True,
                "condominium_units_count": lr_unit.get_condominium_units_count(),
            }

        if detail == "summary":
            return {
                **cls._identity(lr_unit),
                "distinct_owners": distinct_owners,
                "summary": summary,
                "sale_blockers": brief,
                "owner_flags_summary": flags_summary,
                **condo_fields,
            }

        if detail in ("full", "shares"):
            if detail == "full":
                result = lr_unit.model_dump(mode="json")
                sheet = result["ownership_sheet_b"]
            else:
                sheet = lr_unit.ownership_sheet_b.model_dump(mode="json")
                result = {**cls._identity(lr_unit), "ownership_sheet_b": sheet}
            total_owners = cls._count_owner_records(sheet.get("lr_unit_shares") or [])
            total, matching, returned, omitted = cls._window_shares(
                sheet, offset, limit, owner_name
            )
            result["total_shares"] = total
            if owner_name is not None:
                result["owner_name"] = owner_name
                result["matching_shares"] = matching
            result["total_owners"] = total_owners
            result["distinct_owners"] = distinct_owners
            result["owners_truncated"] = (
                cls._count_owner_records(sheet.get("lr_unit_shares") or []) < total_owners
            )
            if omitted:
                # The shares outside the window were dropped whole, not merely
                # emptied; say how many so the count is not read as the unit's
                # full sheet B.
                result["shares_omitted"] = omitted
            result["page"] = cls._page(offset, limit, matching, returned, fetched_at=fetched_at)
            result["summary"] = summary
            result["sale_blockers"] = brief
            result["owner_flags_summary"] = flags_summary
            result.update(condo_fields)
            cls._check_size(result, lr_unit, detail, limit)
            return result

        if detail == "parcels":
            sheet = lr_unit.possessory_sheet_a1
            window = cls._window(sheet.cad_parcels, offset, limit)
            result = {
                **cls._identity(lr_unit),
                "sheet_a1_source_key": lr_unit.sheet_a1_source_key,
                "parcels": [parcel.model_dump(mode="json") for parcel in window],
                "total_parcels": len(sheet.cad_parcels),
                "total_area_m2": sheet.total_area(),
                "sheet_a2_entries": [
                    entry.model_dump(mode="json")
                    for entry in lr_unit.possessory_sheet_a2.lr_entries
                ],
                "page": cls._page(
                    offset, limit, len(sheet.cad_parcels), len(window), fetched_at=fetched_at
                ),
                "summary": summary,
                "sale_blockers": brief,
                **condo_fields,
            }
            cls._check_size(result, lr_unit, detail, limit)
            return result

        if detail == "encumbrances":
            groups = lr_unit.encumbrance_sheet_c.lr_entry_groups
            window = cls._window(groups, offset, limit)
            result = {
                **cls._identity(lr_unit),
                "entry_groups": [group.model_dump(mode="json") for group in window],
                "total_entry_groups": len(groups),
                "page": cls._page(offset, limit, len(groups), len(window), fetched_at=fetched_at),
                "summary": summary,
                "sale_blockers": blockers,
                **condo_fields,
            }
            cls._check_size(result, lr_unit, detail, limit)
            return result

        # detail == "ownership". Each owner row carries ``entry`` (the
        # registration entry that put the owner on the share: order number,
        # receipt date, diary number, action type); ``share_entries`` are the
        # annotations (ZABILJEŽBA) registered on individual shares.
        owners, total, matching, truncated = cls._ownership_rows(
            lr_unit, offset, limit, owner_name, flag_rows
        )
        result = {
            **cls._identity(lr_unit),
            "in_land_registry": True,
            "sheet_a1_source_key": lr_unit.sheet_a1_source_key,
            "is_condominium": is_condo,
            "owners": owners,
            "total_owners": total,
            "distinct_owners": distinct_owners,
        }
        if owner_name is not None:
            result["owner_name"] = owner_name
            result["matching_owners"] = matching
        result.update({
            "owners_truncated": truncated,
            "page": cls._page(offset, limit, matching, len(owners), fetched_at=fetched_at),
            "share_entries": lr_unit.ownership_sheet_b.share_entry_rows(),
            "summary": summary,
            "sale_blockers": blockers,
            "owner_flags_summary": flags_summary,
        })
        cls._check_size(result, lr_unit, detail, limit)
        return result

    @staticmethod
    def _blockers_brief(blockers: dict[str, Any]) -> dict[str, Any]:
        """The verdict and counts of a sale-blockers dump, without the list."""
        return {
            "verdict": blockers["verdict"],
            "counts": blockers["counts"],
            "blocker_count": len(blockers["blockers"]),
            "blocker_kinds": sorted({b["kind"] for b in blockers["blockers"]}),
            "cancelled_count": len(blockers.get("blockers_cancelled") or []),
            "scope_filter": blockers.get("scope_filter"),
            "rule": blockers["rule"],
            "notes": blockers.get("notes") or [],
            "detail_note": 'the blockers themselves come with detail="ownership" or "encumbrances"',
        }

    @classmethod
    def _check_size(
        cls, result: dict[str, Any], lr_unit: Any, detail: str, limit: int | None
    ) -> None:
        """Refuse a response that is too large to be read, with a way forward.

        A unit with hundreds of shares serialises to hundreds of kilobytes even
        after the owners are capped, because every share keeps its own
        description and registration entry. Returning it silently overruns the
        caller's context; this says so and names the smaller options.
        """
        size = len(json.dumps(result, ensure_ascii=False))
        if size <= cls.MAX_FULL_RESPONSE_CHARS:
            return
        page = result.get("page") or {}
        returned = page.get("returned") or 0
        smaller = max(1, returned // 4) if returned else 10
        if detail != "full":
            blockers = (result.get("sale_blockers") or {}).get("blockers") or []
            narrow = (
                f" The unit has {len(blockers)} sale blockers; owner_name or condominium_unit "
                f"narrows them to one owner or one flat."
                if len(blockers) > 10
                else ""
            )
            raise ResponseTooLargeError(
                f"The {detail} of land-registry unit {lr_unit.lr_unit_number} are "
                f"{size:,} characters ({returned} {cls.PAGED_LIST[detail]} in this window), "
                f"too large to return in one response. Pass a smaller limit (e.g. "
                f"limit={smaller}) and page through with offset (the page block says "
                f"where to continue).{narrow}"
            )
        total_owners = result.get("total_owners") or 0
        sheet, sheet_size = cls._largest_sheet(result)
        options = [
            'detail="ownership" for the owners without the other sheets',
            (
                'detail="shares", detail="parcels" or detail="encumbrances" for one sheet '
                "at a time, each paged with offset and limit"
            ),
            'detail="summary" for the totals alone',
        ]
        # A share cap only helps while sheet B is what makes the dump large;
        # on a unit whose weight is in the encumbrances it changes nothing.
        if limit is None and total_owners > 0 and sheet == "ownership_sheet_b":
            options.insert(0, "owners_limit (e.g. owners_limit=10) to cap the shares returned")
        elif limit is not None and sheet == "ownership_sheet_b":
            options.insert(0, f"a smaller limit (e.g. limit={smaller}), paged with offset")
        raise ResponseTooLargeError(
            f"A full dump of land-registry unit {lr_unit.lr_unit_number} is "
            f"{size:,} characters ({total_owners} owner records; the largest part is "
            f"{sheet} at {sheet_size:,} characters), too large to return in one "
            f"response. Use {', or '.join(options)}."
        )

    @staticmethod
    def _largest_sheet(result: dict[str, Any]) -> tuple[str, int]:
        """The sheet that makes a full dump large, and its size in characters."""
        sizes = {
            key: len(json.dumps(value, ensure_ascii=False))
            for key, value in result.items()
            if key.startswith(("ownership_sheet", "encumbrance_sheet", "possessory_sheet"))
        }
        if not sizes:
            return "the unit", 0
        return max(sizes.items(), key=lambda item: item[1])

    @staticmethod
    def _plombe_detail(statuses: dict[str, FileStatus]) -> dict[str, Any]:
        """Pending-plomba detail shaped for JSON output.

        ``statuses`` is what ``client.get_plombe_details`` returned: a map of
        file_number -> status for the land-registry plombe that resolved
        (cadastre/unresolvable plombe are omitted, but they remain visible in
        the unit's summary ``pending_plombe`` list).
        """
        return {
            file_number: status.model_dump(mode="json", by_alias=False)
            for file_number, status in statuses.items()
        }

    async def get_lr_unit(
        self,
        units: list[LRUnitRef | dict[str, Any]],
        detail: str = "ownership",
        owners_limit: int | None = None,
        include_plombe_detail: bool = False,
        historical_overview: bool = False,
        offset: int = 0,
        limit: int | None = None,
        owner_name: str | None = None,
        condominium_unit: str | None = None,
        refresh: bool = False,
    ) -> dict[str, Any]:
        """
        Get one or more land registry units (zemljišnoknjižni uložak).

        Each reference (``LRUnitRef``) names a unit directly (lr_unit_number +
        main_book_id, or + main_book_name) or through a parcel (parcel_number +
        municipality; the unit is resolved through parcel links when the parcel
        has no direct unit, and the entry reports ``lr_unit_derived_from_links``).

        A unit that several references resolve to is fetched and returned once;
        the later references get ``status`` "duplicate" and ``same_unit_as``,
        the index of the entry that carries the data.

        Args:
            units: One or more unit references.
            detail: "summary" | "ownership" | "shares" | "parcels" |
                "encumbrances" | "full" (default "ownership"), applied to
                every unit.
            owners_limit: Synonym of ``limit`` kept for the owner-centred
                levels ("ownership" and "full"); ``limit`` wins when both are
                given.
            include_plombe_detail: Resolve what each pending plomba is (request
                type, status, dates) into a ``plombe_detail`` map per unit; one
                extra request per plomba.
            historical_overview: Ask the register for the historical overview
                (deleted entries and shares with a non-active status) as well.
            offset: Skip this many items of the list the level is about
                (owner records, shares, parcels or entry groups) before
                returning.
            limit: Return at most this many of them; ``page`` in every unit
                says what window came back and where to continue.
            owner_name: Keep only the owners whose name contains every word
                of this text (case and diacritics ignored, words in any
                order): the owner rows in "ownership", the shares holding such
                an owner in "shares" and "full"; the other levels refuse it.
                The page then walks the matches, ``matching_owners`` /
                ``matching_shares`` count them and the totals still describe
                the whole sheet, so one person is found in a condominium of
                hundreds of shares without paging through it.
            condominium_unit: Narrow ``sale_blockers`` to one condominium
                unit ("E-16", "E16" or "16"): unit-wide blockers still count,
                share-scoped ones only on that flat.

        Returns:
            Dictionary with ``results`` (one entry per reference, in order:
            status, ref, lr_unit_number, main_book_id, data | error), ``total``,
            ``unique`` (units actually fetched), ``successful``, ``failed``,
            ``duplicates`` and ``condominiums_found``. Every reference has
            exactly one of the three statuses, so
            ``successful + failed + duplicates == total``; ``successful`` counts
            fetched units, i.e. equals ``unique``. Every level of ``data``
            carries ``sale_blockers`` (``verdict``, ``counts``, ``rule``; the
            ``blockers`` themselves in "ownership" and "encumbrances") and
            ``owner_flags_summary``; "ownership" rows carry ``flags``.
        """
        if detail not in self.VALID_DETAIL:
            raise ValueError(
                f"Invalid detail '{detail}'. Expected one of {self.VALID_DETAIL}."
            )
        if not units:
            raise ValueError("Give at least one land registry unit reference.")
        if limit is None:
            limit = owners_limit
        if limit is not None and limit < 1:
            raise ValueError(f"limit must be at least 1, got {limit}")
        if offset < 0:
            raise ValueError(f"offset must not be negative, got {offset}")
        owner_name = self._owner_name_filter(owner_name, detail)

        logger.info(
            f"Fetching {len(units)} land registry unit reference(s) "
            f"(detail={detail}, historical={historical_overview}, owner_name={owner_name!r})"
        )
        results: list[dict[str, Any]] = []
        fetched: dict[tuple[str, int], int] = {}  # (unit number, main book id) -> index
        by_name: dict[tuple[str, str], int] = {}  # (unit number, MAIN BOOK NAME) -> index
        condominiums_found = 0

        for spec in units:
            try:
                ref = spec if isinstance(spec, LRUnitRef) else LRUnitRef.model_validate(spec)
            except ValueError as e:
                results.append({"status": "error", **error_fields(e), "ref": spec})
                continue
            entry: dict[str, Any] = {"ref": ref.model_dump(exclude_none=True)}

            # A direct reference that was already fetched needs no request.
            known = None
            if not ref.by_parcel:
                assert ref.lr_unit_number is not None
                if ref.main_book_id is not None:
                    known = fetched.get((ref.lr_unit_number, ref.main_book_id))
                elif ref.main_book_name:
                    known = by_name.get((ref.lr_unit_number, ref.main_book_name.upper()))
            if known is not None:
                entry.update(
                    status="duplicate",
                    same_unit_as=known,
                    lr_unit_number=results[known]["lr_unit_number"],
                    main_book_id=results[known]["main_book_id"],
                )
                results.append(entry)
                continue

            try:
                lr_unit = await asyncio.to_thread(
                    self._fetch_lr_unit, ref, historical_overview, refresh=refresh
                )
            except Exception as e:  # noqa: BLE001 - recorded per item on purpose
                logger.error(f"Failed to fetch {ref.describe()}: {e}")
                entry.update(status="error", **error_fields(e))
                results.append(entry)
                continue

            key = (str(lr_unit.lr_unit_number), int(lr_unit.main_book_id))
            entry["lr_unit_number"], entry["main_book_id"] = key
            if ref.by_parcel:
                entry["lr_unit_derived_from_links"] = lr_unit.lr_unit_derived_from_links
            if key in fetched:
                entry.update(status="duplicate", same_unit_as=fetched[key])
                results.append(entry)
                continue

            try:
                # The plomba detail is fetched before shaping so the sale
                # blockers can say what each pending request is.
                statuses: dict[str, FileStatus] | None = None
                if include_plombe_detail:
                    statuses = (
                        await asyncio.to_thread(self.client.get_plombe_details, lr_unit)
                        if lr_unit.has_pending_plombe()
                        else {}
                    )
                data = self._shape_lr_unit(
                    lr_unit,
                    detail,
                    limit,
                    offset,
                    owner_name,
                    condominium_unit=condominium_unit,
                    plombe_detail=statuses,
                )
                if statuses:
                    data["plombe_detail"] = self._plombe_detail(statuses)
            except Exception as e:  # noqa: BLE001 - e.g. a full dump too large to return
                entry.update(status="error", **error_fields(e))
                results.append(entry)
                continue

            fetched[key] = len(results)
            if ref.main_book_name:
                by_name[(key[0], ref.main_book_name.upper())] = len(results)
            entry.update(status="success", data=data)
            if lr_unit.is_condominium():
                entry["is_condominium"] = True
                condominiums_found += 1
            results.append(entry)

        successful = sum(1 for r in results if r["status"] == "success")
        failed = sum(1 for r in results if r["status"] == "error")
        duplicates = sum(1 for r in results if r["status"] == "duplicate")
        # Every reference lands in exactly one of the three; clients can check
        # successful + failed + duplicates == total.
        response: dict[str, Any] = {
            "results": results,
            "total": len(units),
            "unique": len(fetched),
            "successful": successful,
            "failed": failed,
            "duplicates": duplicates,
            "condominiums_found": condominiums_found,
        }
        if owner_name is not None:
            response["owner_name"] = owner_name
        if condominium_unit is not None:
            response["condominium_unit"] = condominium_unit
        return response

    def _fetch_lr_unit(
        self, ref: LRUnitRef, historical_overview: bool = False, *, refresh: bool = False
    ) -> Any:
        """Fetch the unit a reference names; errors carry a message for the agent."""
        try:
            if ref.by_parcel:
                assert ref.parcel_number is not None and ref.municipality is not None
                muni_code = self._resolve_municipality(ref.municipality)
                return self.client.get_lr_unit_from_parcel(
                    ref.parcel_number,
                    muni_code,
                    historical_overview=historical_overview,
                    refresh=refresh,
                )
            assert ref.lr_unit_number is not None
            return self.client.get_lr_unit_detailed(
                ref.lr_unit_number,
                ref.main_book_id,
                main_book_name=ref.main_book_name,
                historical_overview=historical_overview,
                refresh=refresh,
            )
        except CadastralAPIError as e:
            raise ValueError(
                f"Could not retrieve the land registry unit for {ref.describe()}: {e}"
            ) from e

    async def get_file_status(self, file_number: str, institution_id: int) -> dict[str, Any]:
        """
        Processing status of one land-registry file (spis, plomba) by number.

        Args:
            file_number: Rendered file number, e.g. "Z-12564/2026".
            institution_id: Owning land-registry office id (``institution_id``
                of the unit from get_lr_unit, or of the main book from
                find_main_book).

        Returns:
            {"file_number", "institution_id", "found": bool, "status": {...}}
            where ``status`` is the file's record (what the request is, its
            processing stage, key dates); ``found`` is False when the register
            has no record for that number at that office.
        """
        try:
            logger.info(f"Fetching file status {file_number} at institution {institution_id}")
            status = await asyncio.to_thread(
                self.client.get_file_status, file_number, int(institution_id)
            )
        except CadastralAPIError as e:
            logger.error(f"File status failed for {file_number}: {e}", exc_info=True)
            raise ValueError(
                f"Could not retrieve the status of file '{file_number}' at institution "
                f"{institution_id}: {e}"
            ) from e
        response: dict[str, Any] = {
            "file_number": file_number,
            "institution_id": int(institution_id),
            "found": status is not None,
        }
        if status is None:
            response["message"] = (
                f"No land-registry file '{file_number}' at institution {institution_id}. "
                "Check the number (code-order/year, e.g. Z-12564/2026) and that the "
                "institution is the office that holds the unit."
            )
        else:
            response["status"] = status.model_dump(mode="json", by_alias=False)
        return response

    async def compare_registers(
        self, parcels: list[ParcelRef | dict[str, Any]], include_plombe_detail: bool = False
    ) -> dict[str, Any]:
        """
        Are the cadastre possessors of each parcel its registered owners?

        For every reference the cadastre record and the land-registry unit
        the parcel belongs to are read (a unit shared by several parcels is
        read once) and the two lists of people are matched with the shared
        person identity: exact matches first (tax number, or the folded
        name), then fuzzy ones (a relative's name written differently or
        missing on one side, or the words in another order), which are
        flagged; each pair says how it was found (``via``). Each entry says
        whether the registers name the same
        people, overlap, or are disjoint, lists who is in one register only,
        infers each person's kind (individual, company, state, municipality;
        always labelled inferred), sums the share registered to public
        bodies, and compares the cadastre, land-register and graphical areas.

        Args:
            parcels: One or more parcel references (parcel_id, or
                parcel_number + municipality).
            include_plombe_detail: Resolve what each pending plomba is (one
                request per plomba, once per unit) so the pending blockers
                name their request.

        Returns:
            ``results`` (one entry per reference: status, ref, parcel_number,
            municipality_code, lr_unit, provenance of both registers, data,
            map_url), ``total``, ``successful``, ``failed``, ``units_fetched``,
            ``relationships`` (count per relationship) and ``people``
            (distinct possessors, owners and people across every successful
            entry). ``data`` carries ``sale_blockers`` (the unit's blockers
            plus owner_not_possessor and fuzzy_owner_match, with a verdict)
            and ``owner_flag_counts``; each owner carries ``flags``.
        """
        if not parcels:
            raise ValueError("Give at least one parcel reference.")
        logger.info(f"Comparing registers for {len(parcels)} parcel(s)")
        results: list[dict[str, Any]] = []
        units: dict[tuple[str, int], Any] = {}
        plombe: dict[tuple[str, int], dict[str, FileStatus]] | None = (
            {} if include_plombe_detail else None
        )
        possessors: list[tuple[str | None, str | None]] = []
        owners: list[tuple[str | None, str | None]] = []
        people: list[tuple[str | None, str | None]] = []
        relationships: dict[str, int] = {}
        for spec in parcels:
            try:
                ref = spec if isinstance(spec, ParcelRef) else ParcelRef.model_validate(spec)
            except ValueError as e:
                results.append({"status": "error", **error_fields(e), "ref": spec})
                continue
            entry: dict[str, Any] = {"ref": ref.model_dump(exclude_none=True)}
            try:
                parcel, geometry, unit, unit_error, comparison = await self._load_comparison(
                    ref, units, plombe
                )
            except Exception as e:  # noqa: BLE001 - recorded per item on purpose
                logger.error(f"Register comparison failed for {ref}: {e}")
                entry.update(status="error", **error_fields(e))
                results.append(entry)
                continue
            entry.update(
                status="success",
                parcel_number=parcel.parcel_number,
                municipality_code=parcel.cad_municipality_reg_num,
                lr_unit=comparison.lr_unit,
                provenance={
                    "cadastre": parcel.provenance.as_dict() if parcel.provenance else None,
                    "land_registry": (
                        unit.provenance.as_dict()
                        if unit is not None and unit.provenance is not None
                        else None
                    ),
                },
                data=comparison.model_dump(mode="json"),
            )
            if unit_error is not None:
                entry["land_registry_error"] = error_fields(unit_error)
            if geometry is not None:
                entry["map_url"] = geometry.map_url()
            results.append(entry)
            relationships[comparison.relationship] = (
                relationships.get(comparison.relationship, 0) + 1
            )
            possessors.extend((p.name, p.tax_number) for p in comparison.possessors)
            owners.extend((o.name, o.tax_number) for o in comparison.owners)
            # A matched pair is one person, counted by the owner record so the
            # two registers' spellings of one person are not two people.
            people.extend(
                (r.name, r.tax_number)
                for r in [m.owner for m in comparison.matched]
                + comparison.possessors_only
                + comparison.owners_only
            )

        successful = sum(1 for r in results if r["status"] == "success")
        return {
            "results": results,
            "total": len(parcels),
            "successful": successful,
            "failed": len(results) - successful,
            "units_fetched": len(units),
            "relationships": relationships,
            "people": {
                "distinct_possessors": count_distinct_persons(possessors),
                "distinct_owners": count_distinct_persons(owners),
                "distinct_people": count_distinct_persons(people),
                "note": (
                    "Different people by name (and tax number where given) across every "
                    "successful entry; a person on several parcels counts once, and a "
                    "person matched across the two registers counts once."
                ),
            },
        }

    async def _load_comparison(
        self,
        ref: ParcelRef,
        units: dict[tuple[str, int], Any],
        plombe: dict[tuple[str, int], dict[str, FileStatus]] | None = None,
    ) -> tuple[ParcelInfo, ParcelGeometry | None, Any, Exception | None, Any]:
        """A parcel, its outline, its unit (read once per call) and the register comparison.

        Shared by compare_registers and build_assembly, which differ only in
        what they do with the result. ``plombe`` (a per-call cache keyed like
        ``units``) asks for the plomba detail of each unit, fetched once per
        unit, so the pending requests among the sale blockers are named.
        """
        parcel, geometry, _search = await self._load_parcel(ref)
        unit, unit_error = await asyncio.to_thread(self._unit_of, parcel, units)
        detail: dict[str, FileStatus] | None = None
        if plombe is not None and unit is not None:
            # Asked for: an empty map when the unit has no plomba, so the
            # answer says the detail was included with nothing to fetch.
            key = (str(unit.lr_unit_number), int(unit.main_book_id))
            if key not in plombe:
                plombe[key] = (
                    await asyncio.to_thread(self.client.get_plombe_details, unit)
                    if unit.has_pending_plombe()
                    else {}
                )
            detail = plombe[key]
        comparison = compare_registers(
            parcel,
            unit,
            gis_area_m2=geometry.povrsina_graficka if geometry is not None else None,
            lr_unit_error=str(unit_error) if unit_error else None,
            plombe_detail=detail,
        )
        return parcel, geometry, unit, unit_error, comparison

    def _unit_of(
        self, parcel: ParcelInfo, units: dict[tuple[str, int], Any]
    ) -> tuple[Any, Exception | None]:
        """The land-registry unit a parcel belongs to, read once per call.

        Returns ``(unit, None)``, ``(None, None)`` for a parcel that is not in
        the land registry, or ``(None, error)`` when the unit should exist but
        could not be read (ambiguous links, not found, refused ...).
        """
        try:
            ref = CadastralAPIClient._resolve_lr_unit_ref(parcel)
            if ref is None:
                return None, None
            if ref not in units:
                units[ref] = self.client.get_lr_unit_detailed(ref[0], ref[1])
            return units[ref], None
        except CadastralAPIError as e:
            return None, e

    #: Parcels one assembly analysis may cover: each costs a cadastre record and,
    #: usually, a land-registry unit (20 s or more for a large condominium).
    MAX_ASSEMBLY_PARCELS = 50

    #: What ``build_assembly`` can export next to its JSON.
    VALID_EXPORTS = ("parcels_csv", "persons_csv", "matrix_csv", "blockers_csv", "geojson")

    async def build_assembly(
        self,
        parcels: list[ParcelRef | dict[str, Any]],
        include_zoning: bool = False,
        weights: dict[str, float] | None = None,
        export: str | None = None,
        persons_offset: int = 0,
        persons_limit: int | None = 50,
        include_plombe_detail: bool = False,
        include_blockers: bool = True,
    ) -> dict[str, Any]:
        """
        Land-assembly analysis of a set of parcels: the persons x parcels
        matrix, the persons ranked by controlled area and grouped by surname,
        and the parcels ranked by ease of acquisition, with the weights shown.

        For every reference the cadastre record, the land-registry unit (read
        once per unit) and the register comparison are gathered; with
        ``include_zoning`` the building-areas screening as well (one WFS
        lookup per parcel). ``build_assembly`` in the SDK does the rest.

        Args:
            parcels: Up to ``MAX_ASSEMBLY_PARCELS`` parcel references.
            include_zoning: Read each parcel's zoning for the building-area factor.
            weights: Override any of the score's factor weights.
            export: "parcels_csv" | "persons_csv" | "matrix_csv" |
                "blockers_csv" | "geojson" to add that table as text (or a
                FeatureCollection) under ``export``.
            persons_offset: Skip this many ranked persons.
            persons_limit: Return at most this many (default 50; None for all).
            include_plombe_detail: Name each pending request among the sale
                blockers (one request per plomba, once per unit).
            include_blockers: Return the ``blockers`` table (every counted
                blocker of every parcel); off for a smaller response.

        Returns:
            ``totals``, ``parcels`` (easiest first, with ``score``,
            ``sale_verdict``, ``blocker_counts`` and ``blocker_kinds``),
            ``blockers`` (one row per parcel and blocker, the same ones the
            verdicts rest on),
            ``persons`` (a page of the ranking, with ``persons_page``; each
            with ``likely_deceased`` and ``address_abroad``, inferred),
            ``surname_groups`` (with the counts of those flags), ``matrix``
            (one cell per person and parcel), ``scores`` (the factors behind
            each score), ``weights``, ``notes``, ``generated_at``, ``failed``
            (references that could not be read, with ``error_type``),
            ``units_fetched`` and ``export`` when asked.
        """
        if not parcels:
            raise ValueError("Give at least one parcel reference.")
        if len(parcels) > self.MAX_ASSEMBLY_PARCELS:
            raise ValueError(
                f"An assembly analysis covers at most {self.MAX_ASSEMBLY_PARCELS} parcels per "
                f"call ({len(parcels)} given): each parcel costs a cadastre record and a "
                f"land-registry unit. Split the set and merge the persons by name, or use "
                f"find_parcels_in_area to narrow the area first."
            )
        if export is not None and export not in self.VALID_EXPORTS:
            raise ValueError(f"export must be one of {self.VALID_EXPORTS}, got {export!r}")
        if persons_limit is not None and persons_limit < 1:
            raise ValueError(f"persons_limit must be at least 1, got {persons_limit}")
        if persons_offset < 0:
            raise ValueError(f"persons_offset must not be negative, got {persons_offset}")
        used_weights = resolve_weights(weights)

        logger.info(f"Building assembly analysis for {len(parcels)} parcel(s)")
        items: list[AssemblyInput] = []
        failed: list[dict[str, Any]] = []
        units: dict[tuple[str, int], Any] = {}
        plombe: dict[tuple[str, int], dict[str, FileStatus]] | None = (
            {} if include_plombe_detail else None
        )
        geometries: dict[str, ParcelGeometry] = {}
        zoning_notes: list[str] = []
        for spec in parcels:
            try:
                ref = spec if isinstance(spec, ParcelRef) else ParcelRef.model_validate(spec)
            except ValueError as e:
                failed.append({"ref": spec, **error_fields(e)})
                continue
            try:
                parcel, geometry, unit, unit_error, comparison = await self._load_comparison(
                    ref, units, plombe
                )
            except Exception as e:  # noqa: BLE001 - recorded per item on purpose
                logger.error(f"Assembly input failed for {ref}: {e}")
                failed.append({"ref": ref.model_dump(exclude_none=True), **error_fields(e)})
                continue
            zoning = None
            if include_zoning:
                try:
                    zoning = await asyncio.to_thread(
                        self.client.get_parcel_zoning,
                        parcel.parcel_number,
                        parcel.cad_municipality_reg_num,
                    )
                except Exception as e:  # noqa: BLE001 - the factor is then not evaluated
                    logger.warning(f"Zoning failed for {parcel.parcel_number}: {e}")
                    zoning_notes.append(
                        f"zoning of {parcel.parcel_number} not read "
                        f"({error_kind(e)[0]}); its building-area factor is not evaluated"
                    )
            if geometry is not None:
                geometries[parcel.parcel_number] = geometry
            items.append(
                AssemblyInput(
                    parcel=parcel,
                    lr_unit=unit,
                    comparison=comparison,
                    zoning=zoning,
                    map_url=geometry.map_url() if geometry is not None else None,
                )
            )
        if not items:
            raise ValueError(
                "None of the parcels could be read: "
                + "; ".join(f"{f.get('ref')}: {f['error']}" for f in failed)
            )

        analysis = build_assembly(items, used_weights)
        persons_window = self._window(analysis.persons, persons_offset, persons_limit)
        response: dict[str, Any] = {
            "generated_at": analysis.generated_at,
            "weights": analysis.weights,
            "totals": analysis.totals.model_dump(mode="json"),
            "parcels": [p.model_dump(mode="json") for p in analysis.parcels],
            "persons": [p.model_dump(mode="json") for p in persons_window],
            "persons_page": self._page(
                persons_offset, persons_limit, len(analysis.persons), len(persons_window)
            ),
            "surname_groups": [g.model_dump(mode="json") for g in analysis.surname_groups],
            "matrix": [c.model_dump(mode="json") for c in analysis.matrix],
            "scores": [s.model_dump(mode="json") for s in analysis.scores],
            "blockers": (
                [b.model_dump(mode="json", exclude_none=True) for b in analysis.blockers]
                if include_blockers
                else None
            ),
            "blocker_count": len(analysis.blockers),
            "notes": analysis.notes + zoning_notes,
            "total": len(parcels),
            "successful": len(items),
            "failed": failed,
            "units_fetched": len(units),
            "zoning_requested": include_zoning,
        }
        if export == "parcels_csv":
            response["export"] = {"format": export, "text": parcels_csv(analysis)}
        elif export == "persons_csv":
            response["export"] = {"format": export, "text": persons_csv(analysis)}
        elif export == "matrix_csv":
            response["export"] = {"format": export, "text": matrix_csv(analysis)}
        elif export == "blockers_csv":
            response["export"] = {"format": export, "text": blockers_csv(analysis)}
        elif export == "geojson":
            response["export"] = {"format": export, **parcels_geojson(analysis, geometries)}
        size = len(json.dumps(response, ensure_ascii=False))
        if size > self.MAX_PARCEL_RESPONSE_CHARS:
            raise ResponseTooLargeError(
                f"The assembly analysis of {len(items)} parcels is {size:,} characters, too "
                f"large to return in one response. Analyse fewer parcels per call, pass a "
                f"persons_limit, set include_blockers=false, or ask for one export at a time."
            )
        return response

    #: Parcel rows the area tools return unless asked otherwise.
    DEFAULT_AREA_LIMIT = 50

    #: How a parcel relates to the query area.
    VALID_RELATIONS = ("intersects", "within")

    @staticmethod
    def _metric_point(value: Any, what: str) -> tuple[float, float]:
        """An ``[x, y]`` pair in EPSG:3765 metres, refusing longitude/latitude."""
        try:
            x, y = float(value[0]), float(value[1])
        except (TypeError, ValueError, IndexError):
            raise ValueError(f"{what} must be [x, y] in EPSG:3765 metres, got {value!r}") from None
        if len(value) != 2:
            raise ValueError(f"{what} must be [x, y] in EPSG:3765 metres, got {value!r}")
        if abs(x) <= 180 and abs(y) <= 90:
            raise ValueError(
                f"{what} ({x}, {y}) looks like longitude/latitude; the area tools take "
                f"EPSG:3765 (HTRS96/TM) metres, the coordinates get_parcel_geometry returns "
                f"(easting about 250000-800000, northing about 4600000-5200000)."
            )
        return x, y

    async def _parcel_index(self, municipality: str) -> tuple[str, ParcelIndex]:
        """The municipality's code and spatial index (built in a worker thread)."""
        muni_code = await self._municipality_code(municipality)
        try:
            index = await asyncio.to_thread(self.client.get_parcel_index, muni_code)
        except CadastralAPIError:
            raise
        except Exception as e:  # noqa: BLE001 - download, zip and parse errors alike
            logger.error(f"GIS index failed for {muni_code}: {e}", exc_info=True)
            raise ValueError(
                f"Could not load the GIS data of municipality '{municipality}' ({muni_code}): {e}"
            ) from e
        return muni_code, index

    def _gis_dataset(self, muni_code: str, index: ParcelIndex) -> dict[str, Any]:
        """Provenance of an answer read from the cached cadastral map."""
        cache = self.client.gis_cache
        downloaded_at = cache.downloaded_at(muni_code)
        return {
            "municipality_code": muni_code,
            "parcel_count": len(index),
            "crs": "EPSG:3765",
            "source": cache.get_source(muni_code),
            "downloaded_at": downloaded_at.isoformat() if downloaded_at is not None else None,
            "note": (
                "Outlines and graphical areas from the cadastral map (ATOM GML download), "
                "not a survey; parcel numbers are the cadastre's."
            ),
        }

    @staticmethod
    def _parcel_row(item: IndexedParcel, **extra: Any) -> dict[str, Any]:
        """A parcel of the index as the agent should see it."""
        return {
            "parcel_number": item.parcel_number,
            "area_m2": item.area_m2,
            "centroid": [round(item.centroid[0], 2), round(item.centroid[1], 2)],
            "bounds": [round(v, 2) for v in item.bounds],
            **extra,
            "map_url": item.geometry.map_url(),
        }

    async def find_parcels_in_area(
        self,
        municipality: str,
        bbox: list[float] | None = None,
        polygon: str | list[list[float]] | None = None,
        center: list[float] | None = None,
        radius_m: float | None = None,
        relation: str = "intersects",
        offset: int = 0,
        limit: int | None = DEFAULT_AREA_LIMIT,
        include_geojson: bool = False,
    ) -> dict[str, Any]:
        """
        The parcels of a municipality inside an area: a bounding box, a
        polygon, or a radius around a point (EPSG:3765 metres).

        Read from the cached cadastral map of the municipality (downloaded on
        first use), so no parcel number is needed to define a target area.

        Args:
            municipality: Municipality name or registration code.
            bbox: ``[min_x, min_y, max_x, max_y]``.
            polygon: WKT ``POLYGON((x y, ...))`` or a list of ``[x, y]`` vertices.
            center: ``[x, y]`` of the point, with ``radius_m``.
            radius_m: Radius in metres around ``center``.
            relation: ``"intersects"`` (default: the parcel touches the area)
                or ``"within"`` (lies wholly inside it); a radius query always
                measures the distance from the point to the parcel outline.
            offset: Skip this many parcels.
            limit: Return at most this many (default 50; None for all).
            include_geojson: Add a GeoJSON FeatureCollection of the page.

        Returns:
            ``municipality_code``, ``query`` (as understood), ``parcels`` (rows
            with parcel_number, area_m2, centroid, bounds, distance_m for a
            radius query, map_url), ``total`` and ``total_area_m2`` over
            every match, ``page``, ``dataset`` (the cached map's provenance)
            and, when asked, ``geojson``.
        """
        modes = [
            name for name, value in (("bbox", bbox), ("polygon", polygon), ("center", center))
            if value is not None
        ]
        if len(modes) != 1:
            raise ValueError(
                "Give exactly one area: bbox, polygon, or center with radius_m "
                f"(got {', '.join(modes) or 'none'})."
            )
        if (center is None) != (radius_m is None):
            raise ValueError("center and radius_m go together.")
        if relation not in self.VALID_RELATIONS:
            raise ValueError(f"relation must be one of {self.VALID_RELATIONS}, got {relation!r}")
        if limit is not None and limit < 1:
            raise ValueError(f"limit must be at least 1, got {limit}")
        if offset < 0:
            raise ValueError(f"offset must not be negative, got {offset}")

        # Each branch validates its area, records the query as understood and
        # binds the search to run once the index is loaded, so the geometry
        # values never cross branches; ``distances`` is filled by a radius query.
        wanted_relation: Relation = "within" if relation == "within" else "intersects"
        query: dict[str, Any]
        if bbox is not None:
            if len(bbox) != 4:
                raise ValueError(f"bbox must be [min_x, min_y, max_x, max_y], got {bbox!r}")
            low = self._metric_point(bbox[:2], "bbox corner")
            high = self._metric_point(bbox[2:], "bbox corner")
            if low[0] > high[0] or low[1] > high[1]:
                raise ValueError("bbox must be [min_x, min_y, max_x, max_y] with min <= max")
            bounds = (*low, *high)
            query = {"bbox": list(bounds), "relation": relation}

            def search(index: ParcelIndex) -> tuple[list[IndexedParcel], dict[str, float]]:
                return index.in_bbox(bounds, wanted_relation), {}

        elif polygon is not None:
            ring = parse_ring(polygon)
            self._metric_point(ring[0], "polygon vertex")
            query = {"polygon": [list(p) for p in ring], "relation": relation}

            def search(index: ParcelIndex) -> tuple[list[IndexedParcel], dict[str, float]]:
                return index.in_polygon(ring, wanted_relation), {}

        else:
            assert center is not None and radius_m is not None
            point = self._metric_point(center, "center")
            if radius_m <= 0:
                raise ValueError(f"radius_m must be positive, got {radius_m}")
            radius = float(radius_m)
            query = {"center": list(point), "radius_m": radius}

            def search(index: ParcelIndex) -> tuple[list[IndexedParcel], dict[str, float]]:
                radius_hits = index.within_radius(point[0], point[1], radius)
                return (
                    [hit.parcel for hit in radius_hits],
                    {hit.parcel.parcel_number: hit.distance_m for hit in radius_hits},
                )

        logger.info(f"Finding parcels in {municipality} by {modes[0]}")
        muni_code, index = await self._parcel_index(municipality)
        hits, distances = search(index)

        window = self._window(hits, offset, limit)
        rows = [
            self._parcel_row(
                item, **({"distance_m": distances[item.parcel_number]} if distances else {})
            )
            for item in window
        ]
        response: dict[str, Any] = {
            "municipality_code": muni_code,
            "query": query,
            "parcels": rows,
            "total": len(hits),
            "total_area_m2": ParcelIndex.total_area(hits),
            "page": self._page(offset, limit, len(hits), len(window)),
            "dataset": self._gis_dataset(muni_code, index),
        }
        if include_geojson:
            response["geojson"] = self._feature_collection(window)
        return response

    @staticmethod
    def _feature_collection(items: list[IndexedParcel]) -> dict[str, Any]:
        return {
            "type": "FeatureCollection",
            "features": [item.geometry.to_geojson() for item in items],
        }

    async def find_parcel_neighbours(
        self,
        parcel_number: str,
        municipality: str,
        tolerance_m: float = 0.10,
        offset: int = 0,
        limit: int | None = DEFAULT_AREA_LIMIT,
        include_geojson: bool = False,
    ) -> dict[str, Any]:
        """
        The parcels around one parcel: those sharing a boundary with it, and
        those touching it at a corner.

        Read from the cached cadastral map (downloaded on first use). A
        neighbour with ``touches_at_point`` true meets the parcel at a point
        only (a street corner, say); the others share ``shared_boundary_m``
        metres of boundary, longest first.

        Args:
            parcel_number: Cadastral parcel number (e.g., "103/2").
            municipality: Municipality name or registration code.
            tolerance_m: How far apart two outlines may be and still count as
                touching (default 0.10 m, for digitising gaps).
            offset: Skip this many neighbours.
            limit: Return at most this many (default 50; None for all).
            include_geojson: Add a GeoJSON FeatureCollection of the page.

        Returns:
            ``parcel`` (the seed parcel's row), ``neighbours`` (rows with
            shared_boundary_m and touches_at_point), ``total``,
            ``total_area_m2`` of every neighbour, ``page``, ``dataset`` and,
            when asked, ``geojson``.
        """
        if limit is not None and limit < 1:
            raise ValueError(f"limit must be at least 1, got {limit}")
        if offset < 0:
            raise ValueError(f"offset must not be negative, got {offset}")
        if tolerance_m < 0:
            raise ValueError(f"tolerance_m must not be negative, got {tolerance_m}")
        wanted = normalize_parcel_number(parcel_number)
        logger.info(f"Finding neighbours of {wanted} in {municipality}")
        muni_code, index = await self._parcel_index(municipality)
        seed = index.by_number(wanted)
        if seed is None:
            raise ValueError(
                f"Parcel '{parcel_number}' has no geometry in the GIS data for municipality "
                f"'{municipality}' ({muni_code}). Check the parcel number; if the cached GIS "
                f"data may be stale, refresh it with download_municipality_gis(force=true)."
            )
        neighbours = index.neighbours(wanted, tolerance_m)
        window = self._window(neighbours, offset, limit)
        response: dict[str, Any] = {
            "municipality_code": muni_code,
            "parcel": self._parcel_row(seed),
            "neighbours": [
                self._parcel_row(
                    n.parcel,
                    shared_boundary_m=n.shared_boundary_m,
                    touches_at_point=n.touches_at_point,
                )
                for n in window
            ],
            "total": len(neighbours),
            "total_area_m2": ParcelIndex.total_area(n.parcel for n in neighbours),
            "tolerance_m": tolerance_m,
            "page": self._page(offset, limit, len(neighbours), len(window)),
            "dataset": self._gis_dataset(muni_code, index),
        }
        if include_geojson:
            response["geojson"] = self._feature_collection([seed, *(n.parcel for n in window)])
        return response

    async def download_municipality_gis(
        self, municipality: str, force: bool = False
    ) -> dict[str, Any]:
        """
        Download (or refresh) the GIS data of a whole cadastral municipality.

        The ATOM feed serves one ZIP per municipality with the parcel
        boundaries in GML; this fetches it into the local cache that
        get_parcel_geometry and get_parcel_zoning read, and reports what was
        cached. The download runs in a worker thread.

        Args:
            municipality: Municipality name or registration code.
            force: Download again even when the municipality is cached.

        Returns:
            {"municipality_code", "download_url", "already_cached", "downloaded_at",
            "zip_path", "zip_size_bytes", "gml_path", "parcel_count", "source"}.
        """
        muni_code = await self._municipality_code(municipality)
        cache = self.client.gis_cache
        already_cached = cache.is_cached(muni_code) and not force
        try:
            logger.info(f"Downloading GIS data for municipality {muni_code} (force={force})")
            zip_path = await asyncio.to_thread(cache.download_municipality, muni_code, force)
            gml_path = await asyncio.to_thread(cache.get_parcel_data, muni_code, True)
            parcel_count = await asyncio.to_thread(lambda: GMLParser(gml_path).count_parcels())
            downloaded_at = cache.downloaded_at(muni_code)
        except Exception as e:  # noqa: BLE001 - HTTP, zip and parse errors alike
            logger.error(f"GIS download failed for {muni_code}: {e}", exc_info=True)
            raise ValueError(
                f"Could not download the GIS data of municipality '{municipality}' "
                f"({muni_code}): {e}"
            ) from e
        return {
            "municipality_code": muni_code,
            "download_url": f"{cache.base_url}/atom/ko-{muni_code}.zip",
            "already_cached": already_cached,
            "downloaded_at": downloaded_at.isoformat() if downloaded_at is not None else None,
            "zip_path": str(zip_path),
            "zip_size_bytes": zip_path.stat().st_size,
            "gml_path": str(gml_path),
            "parcel_count": parcel_count,
            "source": cache.get_source(muni_code),
        }

    async def find_main_book(
        self,
        search: str | None = None,
        office_id: str | int | None = None,
        institution_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Find land-registry main books (glavne knjige) by name, office or institution.

        The main book id is what ``get_lr_unit`` needs; searching a cadastral
        municipality name ("SAVAR") returns the book that holds its units.

        Returns:
            {"main_books": [{main_book_id, main_book_name, institution_id,
            court_name, ...}], "count": n}
        """
        try:
            logger.info(f"Finding main books (search={search}, office={office_id})")
            books = await asyncio.to_thread(
                self.client.find_main_book, search, office_id, institution_name
            )
            return {
                "main_books": [search_record(book) for book in books],
                "count": len(books),
            }
        except CadastralAPIError as e:
            logger.error(f"Main book search failed: {e}", exc_info=True)
            raise ValueError("Could not search land-registry main books.") from e

    async def find_book_of_dc(
        self,
        search: str | None = None,
        office_id: str | int | None = None,
        institution_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Find books of deposited contracts (knjige položenih ugovora, KPU).

        Returns:
            {"books_of_dc": [{book_id, book_name, office_id, office_name, ...}], "count": n}
        """
        try:
            logger.info(f"Finding books of deposited contracts (search={search})")
            books = await asyncio.to_thread(
                self.client.find_book_of_dc, search, office_id, institution_name
            )
            return {
                "books_of_dc": [search_record(book) for book in books],
                "count": len(books),
            }
        except CadastralAPIError as e:
            logger.error(f"Books-of-DC search failed: {e}", exc_info=True)
            raise ValueError("Could not search books of deposited contracts.") from e

    async def get_possession_sheet(
        self,
        sheet_number: str,
        municipality: str,
        offset: int = 0,
        limit: int | None = None,
        possessor_name: str | None = None,
    ) -> dict[str, Any]:
        """
        A possession sheet (posjedovni list) by number: its possessors and
        every parcel on it.

        Three requests: the municipality's internal id, the sheet with its
        possessors, and the parcel search that lists the sheet's parcels.
        Possessors are paged like get_parcel's; the parcels come whole.

        Args:
            sheet_number: Possession sheet number (exact).
            municipality: Municipality name or registration code.
            offset: Skip this many possessor records.
            limit: Return at most this many (None for all).
            possessor_name: Keep only the possessors whose name contains every
                word of this text (case and diacritics ignored).

        Returns:
            ``sheet`` (id, number, municipality, is_condominium, total ownership),
            ``possessors_in_land_registry`` (a harmonized sheet lists no
            possessors; ``owners`` then carries the unit's registered owners,
            ``possessor_name`` filters them and ``matching_owners`` counts the
            matches; the sheet's missing id and municipality are filled from
            the parcel records, ``backfilled_from_parcels`` says which),
            ``lr_unit``, ``possessors`` (a page), ``total_possessors``,
            ``distinct_possessors``,
            ``page``, ``parcels`` (number, id, area, land use, building parcel,
            harmonized, land-registry reference, inline owners when harmonized),
            ``parcel_count``, ``total_area_m2``, ``parcels_complete`` (False
            when the list is as long as the longest ever observed, so a
            server cap cannot be ruled out) and ``provenance`` of both calls.
        """
        if limit is not None and limit < 1:
            raise ValueError(f"limit must be at least 1, got {limit}")
        if offset < 0:
            raise ValueError(f"offset must not be negative, got {offset}")
        possessor_filter = self._possessor_filter(possessor_name, None)
        number = str(sheet_number).strip()
        if not number:
            raise ValueError("sheet_number must not be blank")
        logger.info(f"Reading possession sheet {number} in {municipality}")
        try:
            result = await asyncio.to_thread(
                self.client.get_possession_sheet_parcels, number, municipality
            )
        except CadastralAPIError as e:
            if e.error_type is ErrorType.POSSESSION_SHEET_NOT_FOUND:
                raise ValueError(
                    f"No possession sheet numbered '{number}' in municipality "
                    f"'{municipality}'. The number is matched exactly; find_possession_sheet "
                    f"lists the sheets whose number begins with it."
                ) from e
            if e.error_type is ErrorType.MUNICIPALITY_NOT_FOUND:
                raise ValueError(f"Municipality '{municipality}' not found") from e
            raise ValueError(
                f"Could not read possession sheet '{number}' in {municipality}: {e}"
            ) from e

        sheet = result.sheet
        sheet_dump = sheet.model_dump(mode="json")
        sheet_dump.pop("provenance", None)
        if result.backfilled_from_parcels:
            sheet_dump["backfilled_from_parcels"] = list(result.backfilled_from_parcels)
        possessors = sheet_dump.pop("possessors") or []
        if possessor_filter:
            possessors = [p for p in possessors if self._possessor_matches(p, possessor_filter)]
        window = self._window(possessors, offset, limit)
        parcels = [
            {
                "parcel_id": p.parcel_id,
                "parcel_number": p.parcel_number,
                "parcel_number_display": p.parcel_number_display,
                "area_m2": p.area_numeric,
                "address": p.address,
                "land_use": p.land_use_summary,
                "is_building_parcel": p.is_building_parcel,
                "is_harmonized": p.is_harmonized,
                "lr_unit": (
                    {"lr_unit_number": u.lr_unit_number, "main_book_id": u.main_book_id}
                    if (u := p.resolved_lr_unit()) is not None
                    else None
                ),
                "inline_owners": len(p.lr_unit.owner_rows()) if p.lr_unit is not None else None,
            }
            for p in result.parcels
        ]
        lr_ref = result.lr_unit
        response: dict[str, Any] = {
            "sheet": sheet_dump,
            "possessors_in_land_registry": result.possessors_in_land_registry,
            "lr_unit": (
                {"lr_unit_number": lr_ref.lr_unit_number, "main_book_id": lr_ref.main_book_id}
                if lr_ref is not None
                else None
            ),
            "possessors": window,
            "total_possessors": len(sheet.possessors),
            "distinct_possessors": count_distinct_persons(
                (p.name, None) for p in sheet.possessors
            ),
            "page": self._page(offset, limit, len(possessors), len(window)),
            "parcels": parcels,
            "parcel_count": len(parcels),
            "total_area_m2": result.total_area_m2,
            "parcels_complete": not result.maybe_truncated,
            "provenance": {
                "sheet": sheet.provenance.as_dict() if sheet.provenance else None,
                "parcels": result.parcels_provenance.as_dict(),
            },
        }
        if result.possessors_in_land_registry:
            # A harmonized sheet: the cadastre lists nobody and names the unit;
            # the registered owners are the possessors, and the parcel search
            # already inlined sheet B, so no unit is read.
            owners = result.owner_rows()
            if possessor_filter:
                owners = [o for o in owners if self._possessor_matches(o, possessor_filter)]
            response["owners"] = owners
            response["total_owners"] = len(owners)
            response["distinct_owners"] = count_distinct_persons(
                (o.get("name"), o.get("tax_number")) for o in owners
            )
            response["owners_note"] = (
                "This sheet is harmonized with the land registry: the cadastre records no "
                "possessors of its own and refers to the land-registry unit, whose registered "
                "owners (register land_registry) are listed under owners, read from sheet B as "
                "the parcel search inlines it, tax numbers (OIB) included where the registry "
                "has them. get_lr_unit gives their entries, shares in full and the encumbrances."
            )
            if possessor_filter:
                response["possessor_filter"] = possessor_filter
                response["filter_applied_to"] = "owners"
                response["matching_owners"] = len(owners)
        elif possessor_filter:
            response["possessor_filter"] = possessor_filter
            response["filter_applied_to"] = "possessors"
            response["matching_possessors"] = len(possessors)
        if result.maybe_truncated:
            response["note"] = (
                f"{len(parcels)} parcels is the most the parcel search has ever returned for "
                f"one sheet; a server-side cap of that size is not ruled out, so the list may "
                f"be incomplete."
            )
        size = len(json.dumps(response, ensure_ascii=False))
        if size > self.MAX_PARCEL_RESPONSE_CHARS:
            raise ResponseTooLargeError(
                f"Possession sheet {number} is {size:,} characters ({len(window)} of "
                f"{len(possessors)} possessor records, {len(parcels)} parcels), too large to "
                f"return in one response. Pass a smaller limit and page with offset, or "
                f"possessor_name to pick the records you need."
            )
        return response

    async def find_possession_sheet(self, sheet_number: str, municipality: str) -> dict[str, Any]:
        """
        Find cadastre possession sheets (posjedovni listovi) by sheet number.

        Returns:
            {"possession_sheets": [{possession_sheet_id, sheet_number, ...}],
            "municipality_code": code, "count": n}
        """
        try:
            logger.info(f"Finding possession sheet {sheet_number} in {municipality}")
            muni_code = await self._municipality_code(municipality)
            sheets = await asyncio.to_thread(
                self.client.find_possession_sheet, sheet_number, muni_code
            )
            return {
                "possession_sheets": [search_record(sheet) for sheet in sheets],
                "municipality_code": muni_code,
                "count": len(sheets),
            }
        except CadastralAPIError as e:
            logger.error(f"Possession sheet search failed: {e}", exc_info=True)
            raise ValueError(
                f"Could not search possession sheets for '{sheet_number}' in {municipality}."
            ) from e

    def _geometry_for(self, parcel_number: str, muni_code: str) -> ParcelGeometry | None:
        """
        Best-effort parcel outline from the cached municipality GIS data.

        Downloaded on first use. Any failure (download, parse, parcel not in
        the GML) is logged and yields None so that the calling tool still
        returns its main result: the map link and the graphical area it
        serves are extras.
        """
        try:
            return self.client.get_parcel_geometry(parcel_number, muni_code)
        except Exception as e:  # noqa: BLE001 - the geometry is optional
            logger.warning(f"No GIS geometry for {parcel_number} in {muni_code}: {e}")
            return None

    async def _municipality_code(self, name_or_code: str) -> str:
        """``_resolve_municipality`` in a worker thread, for the async handlers."""
        return await asyncio.to_thread(self._resolve_municipality, name_or_code)

    def _resolve_municipality(self, name_or_code: str) -> str:
        """Municipality name or code -> registration code (see the SDK resolver).

        Raises:
            ValueError: the municipality is unknown or the name is ambiguous
        """
        try:
            return self.client.resolve_municipality_reg_num(name_or_code)
        except CadastralAPIError as e:
            if e.error_type != ErrorType.MUNICIPALITY_NOT_FOUND:
                raise
            if e.details.get("reason") == "municipality_ambiguous":
                raise ValueError(
                    f"Municipality '{name_or_code}' is ambiguous: {e.details.get('candidates')}"
                ) from e
            raise ValueError(f"Municipality '{name_or_code}' not found") from e
