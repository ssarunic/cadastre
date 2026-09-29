"""Main MCP server implementation using the MCP Python SDK (MCPServer)."""

import functools
import json
import logging
import sys
from collections.abc import Callable
from typing import Annotated, Any, Literal

from cadastral_api import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError
from mcp.server.auth.provider import OAuthAuthorizationServerProvider
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ResourceError, ToolError
from pydantic import Field

from .config import config
from .prompts import CadastralPrompts
from .resources import CadastralResources
from .tools import CadastralTools, LRUnitRef, ParcelRef, error_kind

# Configure logging to stderr (CRITICAL: never log to stdout in MCP servers)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


Handler = Callable[..., Any]

#: Sent to the client in the ``initialize`` response; clients that support it
#: put it in the model's system prompt, so it says once what every tool
#: description would otherwise repeat.
SERVER_INSTRUCTIONS = """\
Croatian cadastre (katastar) and land registry (zemljišne knjige, ZK) lookups.
Demonstration project: unless configured otherwise the data comes from a local
mock server whose records are redacted copies of the public shapes; say so
when an answer is presented as official.

Two registers, never to be confused: the cadastre lists POSSESSORS
(posjednici, posjedovni list); the land registry lists the registered OWNERS
(vlasnici, vlastovnica / B-list) and encumbrances (teretovnica / C-list). For
"vlasnik", "tko je vlasnik", "prema zemljišnim knjigama" use get_lr_unit; for
"posjednik" use get_parcel. compare_registers says whether the two agree.

Every tool takes the cadastral municipality (katastarska općina, k.o.) by
name or code, so start with get_parcel or get_lr_unit directly; find_parcel
is for checking which numbers exist, resolve_municipality for confirming a
name. Building parcels are written "35/1.ZGR". Lists are paged with offset
and limit (`page.truncated`, `page.next_offset`); pass a limit for large
condominiums. Every record carries `provenance` (register, source_url,
retrieved_at); pass it on with any fact you forward, and treat area_check
mismatches and `exact_match: false` as findings, not hits. Every unit carries
`sale_blockers` (what is registered against it that bears on a sale, with a
verdict that is a screening of the register's text, not a legal opinion) and
its owners carry `flags` (likely_deceased, address_abroad, public_body), all
marked inferred: report them as estimates.
"""


def _anticipated(error_class: type[Exception]) -> Callable[[Handler], Handler]:
    """Turn a handler's ``ValueError`` into the SDK's anticipated failure.

    The handlers raise ``ValueError`` with a message written for the agent
    ("No parcels found matching ...", "Could not match parcel ... against the
    building areas: ..."). The MCP SDK treats any exception other than
    ``ToolError`` / ``ResourceError`` as a crash and withholds its message from
    the client, so the agent saw only "Error executing tool <name>". Wrapping
    the handlers hands the message over as the SDK expects.

    The SDK's error carries text only, so the machine-readable kind of the
    failure (``error_kind``: parcel_not_found, access_denied, rate_limit,
    invalid_request ...) is appended to the message as ``[error_type=...]``;
    the list tools put the same kind in each failed entry's ``error_type``.
    """

    def decorate(func: Handler) -> Handler:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except (ValueError, CadastralAPIError) as e:
                kind, _details = error_kind(e)
                raise error_class(f"{e} [error_type={kind}]") from e

        return wrapper

    return decorate


anticipated_tool = _anticipated(ToolError)
anticipated_resource = _anticipated(ResourceError)


def create_mcp_server(
    *,
    auth: AuthSettings | None = None,
    auth_server_provider: OAuthAuthorizationServerProvider[Any, Any, Any] | None = None,
) -> MCPServer:
    """
    Create and configure the Cadastral MCP server.

    Args:
        auth: The SDK's auth settings, with ``auth_server_provider``, when the
            HTTP transport requires a key (``cadastral_mcp.auth``); stdio
            never authenticates.

    Returns:
        Configured MCPServer server instance
    """
    # Initialize the MCP server
    mcp = MCPServer(
        name=config.server_name,
        version=config.server_version,
        instructions=SERVER_INSTRUCTIONS,
        auth=auth,
        auth_server_provider=auth_server_provider,
    )

    # Initialize cadastral API client (shared across all requests)
    # Note: In production, consider using dependency injection or lifespan context
    # Unknown server fields are kept in ``source_fields`` and never reported
    # here: the MCP transport has no place for warnings (stdout is JSON-RPC).
    client = CadastralAPIClient(
        base_url=config.api_base_url,
        timeout=config.api_timeout,
        rate_limit=config.api_rate_limit,
        cache_dir=str(config.cache_dir),
        unknown_fields="ignore",
        cache=config.cache,
    )

    # Initialize handlers
    resources_handler = CadastralResources(client)
    tools_handler = CadastralTools(client)
    prompts_handler = CadastralPrompts(client)

    logger.info(f"Initializing {config.server_name} v{config.server_version}")
    logger.info(f"API Base URL: {config.api_base_url}")
    logger.info(f"Cache Directory: {config.cache_dir}")
    logger.info(f"Response cache: {config.cache or 'memory (default)'}")

    # ========================================================================
    # RESOURCES - Read-only contextual data
    # ========================================================================

    @mcp.resource("cadastral://parcel/{parcel_id}")
    @anticipated_resource
    async def get_parcel_resource(parcel_id: str) -> str:
        """Get full parcel details by ID."""
        logger.info(f"Resource request: cadastral://parcel/{parcel_id}")

        result = await resources_handler.get_parcel_resource(parcel_id)
        return json.dumps(result, indent=2)

    @mcp.resource("cadastral://municipality/{code}")
    @anticipated_resource
    async def get_municipality_resource(code: str) -> str:
        """Get municipality information by code."""
        logger.info(f"Resource request: cadastral://municipality/{code}")

        result = await resources_handler.get_municipality_resource(code)
        return json.dumps(result, indent=2)

    @mcp.resource("cadastral://office/{office_code}")
    @anticipated_resource
    async def get_office_resource(office_code: str) -> str:
        """Get cadastral office information by code."""
        logger.info(f"Resource request: cadastral://office/{office_code}")

        result = await resources_handler.get_office_resource(office_code)
        return json.dumps(result, indent=2)

    # ========================================================================
    # TOOLS - AI-invoked actions
    # ========================================================================

    @mcp.tool()
    @anticipated_tool
    async def find_parcel(
        parcel_number: Annotated[
            str,
            Field(
                description=(
                    'Cadastral parcel number, e.g. "103/2"; a building parcel as "35/1.ZGR", '
                    '"35/1 ZGR" or "*35/1"'
                )
            ),
        ],
        municipality: Annotated[
            str,
            Field(
                description=(
                    'Cadastral municipality (katastarska općina, k.o.) by name, e.g. "SAVAR", or '
                    'registration code, e.g. "334979"'
                )
            ),
        ],
        max_matches: Annotated[
            int,
            Field(
                description=(
                    "Above 0, also return the complete search response under `matches`: every "
                    "record the server matched (parcel_id, parcel_number, is_building_parcel), up"
                    " to this many, with `matches_total` and `matches_truncated`. Use it to list "
                    'what exists ("which parcels start with 103"). With it a search from which no'
                    " single parcel can be chosen is not an error: `success` is false, "
                    "`parcel_id` null, `match_note` says why and `matches` still holds the "
                    "records"
                )
            ),
        ] = 0,
    ) -> dict[str, Any]:
        """
        Find a cadastral parcel (čestica / katastarska čestica, k.č.) and return
        basic information.

        Use for a single parcel in the Croatian/Serbian cadastre (katastar) by
        parcel number within a cadastral municipality (katastarska općina, k.o.).
        Aggregates the 3-step API workflow: resolve municipality, find parcel, return info.

        Use it to learn whether a number exists, to get a ``parcel_id`` or to
        list matches. For the parcel's record itself (area, land use,
        possessors, land-registry reference) call get_parcel directly with
        parcel_number + municipality: it does this search on its own.

        Also returns ``map_url``, a link to the interactive map (karta) centred
        on the parcel, when the municipality's GIS data is available (downloaded
        once, then cached).

        Returns:
            Dictionary with parcel search results including parcel_id.

            The search matches on a substring, so a number that does not exist
            can still come back as a longer one ("973" -> 973/1). Check
            ``exact_match``: when it is False the parcel returned is NOT the one
            asked for, and ``match_note`` plus ``other_matches`` say what was
            found, and whether the number returned begins with the requested one
            or merely contains it. Report that to the user instead of treating
            it as a hit.
        """
        logger.info(f"Tool invoked: find_parcel({parcel_number}, {municipality})")
        return await tools_handler.search_parcel(parcel_number, municipality, max_matches)

    @mcp.tool()
    @anticipated_tool
    async def get_parcel(
        parcels: Annotated[
            list[ParcelRef],
            Field(
                description=(
                    'One or more parcel references, each {"parcel_id": ...} (from find_parcel) or'
                    ' {"parcel_number": ..., "municipality": ...}; one entry per reference comes '
                    "back, in order"
                )
            ),
        ],
        source: Annotated[
            Literal["cadastre", "land_registry", "none"],
            Field(
                description=(
                    'Register to return people from: "cadastre" (default) includes the '
                    'possession-sheet possessors; "land_registry" omits them and returns the '
                    "land-registry unit reference plus a hint to fetch the registered owners with"
                    ' get_lr_unit (use for "vlasnik", "prema zemljišnim knjigama"); "none" '
                    "returns parcel metadata only"
                )
            ),
        ] = "cadastre",
        offset: Annotated[
            int,
            Field(
                description=(
                    "Skip this many possessor records of each parcel (counted across its "
                    'possession sheets, in sheet order); source="cadastre" only'
                )
            ),
        ] = 0,
        limit: Annotated[
            int | None,
            Field(
                description=(
                    "Return at most this many possessor records per parcel (null for all); "
                    'source="cadastre" only'
                )
            ),
        ] = None,
        possessor_name: Annotated[
            str | None,
            Field(
                description=(
                    "Keep only possessors whose name contains every word of this text (case and "
                    'diacritics ignored, words in any order); source="cadastre" only'
                )
            ),
        ] = None,
        condominium_unit: Annotated[
            str | None,
            Field(
                description=(
                    'Keep only the possessors of this condominium unit number ("E-16", "E16" and '
                    '"16" agree); source="cadastre" only'
                )
            ),
        ] = None,
        refresh: Annotated[
            bool,
            Field(
                description="Fetch the record again, ignoring the copy of the last 30 min"
            ),
        ] = False,
    ) -> dict[str, Any]:
        """
        Get the detailed cadastre (katastar) record of one or more parcels
        (čestice): area, land use, possession sheet, land-registry reference.

        Pass one reference for a single parcel and several for a list
        ("parcels 103/2, 45 and 396/1 in SAVAR"); the result has one entry per
        reference, in order, and a failed parcel does not stop the others.
        A reference is ``{"parcel_id": ...}`` (from find_parcel) or
        ``{"parcel_number": ..., "municipality": ...}`` (katastarska općina,
        K.O., by name or code). The parcel search is done here; find_parcel
        first is only needed to check which numbers exist.

        ⚠️ Register matters: cadastre POSSESSORS (posjedovni list) are often NOT
        the registered land-registry OWNERS (vlasnici / vlastovnica / B-list).
        Choose the register explicitly via ``source``:
        - source="cadastre" (default): include possession-sheet possessors.
        - source="land_registry": omit possessors; return the land-registry unit
          reference + a hint to fetch true owners via get_lr_unit (use this for
          "vlasnik", "prema zemljišnim knjigama").
        - source="none": parcel metadata only.

        Every person record carries a ``register`` field ("cadastre" |
        "land_registry") so the two can never be confused.

        Each successful entry also carries ``map_url``, the interactive map
        (karta) centred on the parcel, when the municipality's GIS data is
        available (downloaded once, then cached).

        A parcel under a large condominium (etažno vlasništvo) carries hundreds
        of possessors on one possession sheet. With source="cadastre" page
        through them with ``limit`` and ``offset``: each entry has a ``page``
        block and ``total_possessors``; when ``page.truncated`` is true call
        again with ``offset=page.next_offset``. An entry too large to return
        in one response is recorded as that parcel's error naming a smaller
        limit; do not retry it without one. On such a sheet each possessor's
        ``ownership`` is the share of their own unit and
        ``condominium_share_ownership`` the share of the parcel; the sheet's
        ``total_ownership`` sums the latter. A person holding two units is two
        records: ``total_possessors`` counts records, ``distinct_possessors``
        the different names. To find one person or one unit on such a sheet
        pass ``possessor_name`` (every word must occur in the name; case and
        diacritics ignored) or ``condominium_unit`` (the unit number, "E-16"
        or "16") instead of paging through it.

        Returns:
            Dictionary with ``results`` (status, ref, register, data, map_url
            per entry; with source="cadastre" also total_possessors,
            possessors_truncated and a page block), ``total``, ``successful``,
            ``failed`` and the resolved ``source``. Each successful entry of
            a parcel that is in the land registry includes the unit reference
            under ``data.lr_unit``, which get_lr_unit accepts for ownership
            shares and encumbrances; ``data.lr_reference_shape`` says whether
            the cadastre linked it directly ("direct") or only through parcel
            links ("linked", the unit is then promoted from
            ``lr_units_from_parcel_links``), or not at all ("none").

            Every successful entry carries ``provenance`` (``register``,
            ``source_url``, ``retrieved_at`` in UTC: which register answered,
            from where and when; pass it on with any fact you forward) and
            ``area_check``, which compares the cadastre area with the
            graphical area of the cadastral map and, when the cadastre record
            carries it, the land register's area, flagging ``mismatch`` above
            5 %. A failed entry carries ``error_type`` (parcel_not_found,
            municipality_not_found, access_denied, rate_limit, timeout,
            response_too_large, invalid_request ...) and ``error_details``, so
            an empty answer is never read as an empty parcel.
        """
        logger.info(
            f"Tool invoked: get_parcel({len(parcels)} parcels, source={source}, "
            f"offset={offset}, limit={limit}, possessor_name={possessor_name!r}, "
            f"condominium_unit={condominium_unit!r})"
        )
        return await tools_handler.get_parcel(
            list(parcels),
            source=source,
            offset=offset,
            limit=limit,
            possessor_name=possessor_name,
            condominium_unit=condominium_unit,
            refresh=refresh,
        )

    @mcp.tool()
    @anticipated_tool
    async def resolve_municipality(
        name_or_code: Annotated[
            str,
            Field(
                description=(
                    'Municipality name, e.g. "SAVAR", or registration code, e.g. "334979"'
                )
            ),
        ],
    ) -> dict[str, Any]:
        """
        Resolve a cadastral municipality (katastarska općina, k.o.) name to its
        registration number and complete search record.

        Every other tool accepts the municipality name directly, so this is
        only needed to confirm a name or to show its code and office. To
        enumerate (every municipality of an office, every match of a partial
        name) use list_municipalities.

        Returns:
            Dictionary with ``code`` (registration number), ``name``,
            ``full_name`` (with the cadastral office), ``municipality_id``,
            ``office_id`` and ``department_id``. A name that matches several
            municipalities returns the first with the rest under
            ``other_matches``; use list_municipalities to see them all.
        """
        logger.info(f"Tool invoked: resolve_municipality({name_or_code})")
        return await tools_handler.resolve_municipality(name_or_code)

    @mcp.tool()
    @anticipated_tool
    async def list_municipalities(
        search: Annotated[
            str | None,
            Field(
                description=(
                    "Name or code to match (substring, case-insensitive)"
                )
            ),
        ] = None,
        office_id: Annotated[
            str | int | None,
            Field(
                description=(
                    "Cadastral office id (`id` from list_cadastral_offices)"
                )
            ),
        ] = None,
        department_id: Annotated[
            str | int | None,
            Field(
                description=(
                    "Department id within the office"
                )
            ),
        ] = None,
        offset: Annotated[
            int,
            Field(
                description=(
                    "Skip this many records"
                )
            ),
        ] = 0,
        limit: Annotated[
            int | None,
            Field(
                description=(
                    "Return at most this many records (default 200; null for all)"
                )
            ),
        ] = 200,
    ) -> dict[str, Any]:
        """
        List cadastral municipalities (katastarske općine, k.o.), filtered by
        name, cadastral office (područni ured za katastar) or department.

        Use it for "which cadastral municipalities belong to the Zadar office"
        or to see every municipality a name matches. Without filters it lists
        all municipalities in the country, paged.

        Returns:
            Dictionary with ``municipalities`` (code, name, full_name,
            municipality_id, office_id, department_id each), ``total`` and a
            ``page`` block (offset, limit, total, returned, truncated,
            next_offset).
        """
        logger.info(
            f"Tool invoked: list_municipalities({search}, office={office_id}, "
            f"department={department_id})"
        )
        return await tools_handler.list_municipalities(
            search, office_id, department_id, offset, limit
        )

    @mcp.tool()
    @anticipated_tool
    async def get_parcel_geometry(
        parcel_number: Annotated[
            str,
            Field(
                description=(
                    'Cadastral parcel number, e.g. "103/2"; a building parcel as "35/1.ZGR", '
                    '"35/1 ZGR" or "*35/1"'
                )
            ),
        ],
        municipality: Annotated[
            str,
            Field(
                description=(
                    'Cadastral municipality (katastarska općina, k.o.) by name, e.g. "SAVAR", or '
                    'registration code, e.g. "334979"'
                )
            ),
        ],
        format: Annotated[
            Literal["geojson", "wkt", "dict"],
            Field(
                description=(
                    'Output format: "geojson" (default, map_url in properties), "dict" '
                    '(coordinates, area, centroid, bounds, map_url) or "wkt" (the bare polygon '
                    "text)"
                )
            ),
        ] = "geojson",
        zoom: Annotated[
            int,
            Field(
                description=(
                    "Zoom level of the map link (default 19 fits one parcel; 20 for very small "
                    "parcels)"
                )
            ),
        ] = 19,
    ) -> dict[str, Any] | str:
        """
        Get a parcel's boundary geometry (granice čestice) as GeoJSON/WKT, with
        a link to the interactive map (karta) centred on the parcel.

        For mapping cadastral parcels (katastarska čestica) - coordinates,
        outline, area. Downloads and caches GML data if needed, then extracts geometry.

        Returns:
            Geometry data in requested format. "geojson" (in properties) and
            "dict" carry ``map_url``; "wkt" is the bare polygon.
        """
        logger.info(
            f"Tool invoked: get_parcel_geometry({parcel_number}, {municipality}, "
            f"{format}, zoom={zoom})"
        )
        return await tools_handler.get_parcel_geometry(parcel_number, municipality, format, zoom)

    @mcp.tool()
    @anticipated_tool
    async def get_parcel_zoning(
        parcel_number: Annotated[
            str,
            Field(
                description=(
                    'Cadastral parcel number, e.g. "103/2"; a building parcel as "35/1.ZGR", '
                    '"35/1 ZGR" or "*35/1"'
                )
            ),
        ],
        municipality: Annotated[
            str,
            Field(
                description=(
                    'Cadastral municipality (katastarska općina, k.o.) by name, e.g. "SAVAR", or '
                    'registration code, e.g. "334979"'
                )
            ),
        ],
        include_geometry: Annotated[
            bool,
            Field(
                description=(
                    "Include the zone polygons (EPSG:3765) in the response"
                )
            ),
        ] = False,
        min_overlap: Annotated[
            float,
            Field(
                description=(
                    "Drop zones covering a smaller share of the parcel than this (default 0.02)"
                )
            ),
        ] = 0.02,
    ) -> dict[str, Any]:
        """
        Screening of a parcel against the spatial plans (prostorni planovi):
        is it inside a settlement building area (građevinsko područje
        naselja), in a detached zone outside a settlement (for example a T2
        tourist settlement or T3 camp), touching one below the threshold, or
        outside every building area (namjena prostora, građevinska područja,
        turistička zona).

        It does NOT answer "može li se graditi": ``buildability`` is always
        ``"unknown"``, because plan provisions, plot size, access,
        infrastructure and protection regimes are not evaluated. Matches the
        parcel boundary against the nationwide building-areas layer derived
        from the plans in force and reports every zone covering the parcel
        with the share it covers. The layer is an interpretation of the plans,
        not the plans themselves: always pass the ``disclaimer`` on.

        Returns:
            ``status``, ``buildability`` ("unknown"), ``matches`` (zone
            designation code and text, zone name, plan name and id, generation
            of the code list, overlap), ``below_threshold``, ``plans``,
            ``dataset`` with ``disclaimer``, ``source_url`` and ``retrieved_at``,
            ``summary``, ``generation_note``.
        """
        logger.info(
            f"Tool invoked: get_parcel_zoning({parcel_number}, {municipality}, "
            f"include_geometry={include_geometry}, min_overlap={min_overlap})"
        )
        return await tools_handler.get_parcel_zoning(
            parcel_number, municipality, include_geometry, min_overlap
        )

    @mcp.tool()
    @anticipated_tool
    async def list_cadastral_offices(
        filter_name: Annotated[
            str | None,
            Field(
                description=(
                    "Keep only offices whose name contains this text (case-insensitive)"
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """
        List cadastral offices (katastarski uredi / područni uredi), optionally
        filtered by name.

        Returns:
            Dictionary with ``offices`` (``id``, ``name``, ``code``, address
            fields as the server gives them) and ``count``. The ``id`` is the
            ``office_id`` filter of list_municipalities.
        """
        logger.info(f"Tool invoked: list_cadastral_offices(filter={filter_name})")
        return await tools_handler.list_cadastral_offices(filter_name)

    @mcp.tool()
    @anticipated_tool
    async def get_lr_unit(
        units: Annotated[
            list[LRUnitRef],
            Field(
                description=(
                    'One or more unit references, each {"lr_unit_number", "main_book_id"} (as '
                    'get_parcel returns under data.lr_unit), {"lr_unit_number", "main_book_name"}'
                    ' or {"parcel_number", "municipality"}; one entry per reference comes back, '
                    "in order"
                )
            ),
        ],
        detail: Annotated[
            Literal["summary", "ownership", "shares", "parcels", "encumbrances", "full"],
            Field(
                description=(
                    '"ownership" (default): B-list owners with structured shares plus a summary, '
                    'no geometry or C-sheet, fits in context. "summary": counts only. "shares": '
                    "sheet B as the register holds it (vlastovnica: raw shares with sub-shares, "
                    'entries and status). "parcels": sheet A (posjedovnica: the parcels of the '
                    'unit, with A2 entries). "encumbrances": sheet C (teretovnica: entry groups '
                    'with amounts and beneficiaries). "full": every sheet at once. Each level is '
                    "paged on its own"
                )
            ),
        ] = "ownership",
        owners_limit: Annotated[
            int | None,
            Field(
                description=(
                    'Synonym of `limit` for "ownership" and "full", kept for older callers; '
                    "`limit` wins when both are given"
                )
            ),
        ] = None,
        include_plombe_detail: Annotated[
            bool,
            Field(
                description=(
                    "Resolve what each pending plomba (zaprimljeni neriješeni prijedlog za upis) "
                    "actually is: request type, processing status and dates, as a `plombe_detail`"
                    " map (file_number -> detail) per unit. One extra request per plomba"
                )
            ),
        ] = False,
        historical_overview: Annotated[
            bool,
            Field(
                description=(
                    "Also return the historical overview (povijesni pregled): deleted entries and"
                    " shares whose status is not active. Off by default, so owners are the "
                    "current ones"
                )
            ),
        ] = False,
        offset: Annotated[
            int,
            Field(
                description=(
                    "Skip this many items of the list the level pages: owner records for "
                    '"ownership", top-level shares for "shares" and "full", parcels for '
                    '"parcels", entry groups for "encumbrances"'
                )
            ),
        ] = 0,
        limit: Annotated[
            int | None,
            Field(
                description=(
                    "Return at most this many of them (null for all). Every unit carries a `page`"
                    " block (offset, limit, total, returned, truncated, next_offset); when "
                    '`truncated` is true call again with offset=next_offset. In "shares" and '
                    '"full" the shares outside the window are dropped whole (`shares_omitted`). A'
                    " response too large to return is reported as that unit's error naming the "
                    "smaller options, so pass a limit whenever a unit may have many co-owners or "
                    "encumbrances"
                )
            ),
        ] = None,
        owner_name: Annotated[
            str | None,
            Field(
                description=(
                    "Keep only the owners whose name contains every word of this text (case and "
                    'diacritics ignored, words in any order; "sarunic" finds "ŠARUNIĆ SAŠA"). '
                    'Applies to "ownership" (owner rows), "shares" and "full" (the shares holding'
                    " such an owner, kept whole with their co-owners); the other levels refuse "
                    "it. `matching_owners` / `matching_shares` count the matches, `total_owners` "
                    "/ `total_shares` still describe the whole sheet"
                )
            ),
        ] = None,
        condominium_unit: Annotated[
            str | None,
            Field(
                description=(
                    'Narrow `sale_blockers` to one condominium unit ("E-16" or "16"); unit-wide '
                    "blockers still count. Owner rows are not filtered by it (use owner_name)"
                )
            ),
        ] = None,
        refresh: Annotated[
            bool,
            Field(
                description=(
                    "Fetch the unit again, ignoring the copy of the last 30 min; paging never "
                    "needs it"
                )
            ),
        ] = False,
    ) -> dict[str, Any]:
        """
        Get one or more land registry units (zemljišnoknjižni uložak, zemljišne
        knjige, ZK, gruntovnica): registered owners (vlasnici) and their shares.

        Sheet A (posjedovnica) lists the parcels, sheet B (vlastovnica) the
        owners with shares, sheet C (teretovnica) the encumbrances. Use this
        for "vlasnik" / "tko je vlasnik" / "prema zemljišnim knjigama"
        questions: it returns registered owners, not cadastre possessors.
        Each reference names a unit in one of three ways:
        - ``{"parcel_number": "279/6", "municipality": "SAVAR"}``: the unit the
          parcel belongs to, resolved through parcel links when the parcel has
          no direct unit (the entry reports ``lr_unit_derived_from_links``);
        - ``{"lr_unit_number": "769", "main_book_id": 21277}``: the direct
          reference (as returned by get_parcel under ``data.lr_unit``);
        - ``{"lr_unit_number": "769", "main_book_name": "SAVAR"}``: with the
          main book (glavna knjiga) name instead of its id.

        The result has one entry per reference, in order; a unit that several
        references resolve to is fetched once (the later entries say
        ``duplicate`` and point at the entry with the data), and a failed
        reference does not stop the others.

        Each owner row carries ``entry``, the registration entry (upis) that put
        the owner on the share (order number, receipt date, Z-broj, action
        type); ``share_entries`` lists the annotations (zabilježbe) on
        individual shares. To find one person ("is X an owner", "which flat
        does X own") pass ``owner_name``: only the matching owners (or the
        shares holding one) come back in one call; ``matching_owners`` is 0
        when the name is not on the sheet.

        Every unit carries ``sale_blockers``: what is registered against it
        that bears on a sale (plombe, mortgages, enforcement, disputes,
        prohibitions, pre-emption, servitudes, public bodies as co-owners),
        each with a kind, a severity, the share or flat it attaches to and
        its basis; ``verdict`` (clear | conditional | blocked) follows the
        ``rule`` shown and is a screening of the register's text, not a
        legal opinion; read ``other_annotation`` entries yourself. The
        blockers themselves come with "ownership" and "encumbrances", the
        other levels carry the verdict and counts. Each "ownership" row
        carries inferred ``flags`` (likely_deceased, address_abroad,
        public_body) with their basis.

        Returns:
            Dictionary with ``results`` (status, ref, lr_unit_number,
            main_book_id, data | error per entry) and the counts ``total``,
            ``unique``, ``successful``, ``failed``, ``duplicates`` and
            ``condominiums_found``. Each reference has exactly one status
            (success, error or duplicate), so successful + failed + duplicates
            = total; do not expect successful + failed alone to add up when
            references share a unit. ``data`` is shaped per ``detail``; owners
            carry a structured ``share`` ({num, den, decimal}) and a
            ``register`` tag. Every level names the unit and carries
            ``provenance`` (register, ``source_url``, ``retrieved_at``);
            "summary", "ownership", "shares" and "full" also carry
            ``distinct_owners``, the number of different people among the
            owner records (one person on two shares is two records and one
            owner), for judging fragmentation before reading names. A failed
            entry carries ``error_type`` and ``error_details`` (see
            get_parcel).
        """
        logger.info(
            f"Tool invoked: get_lr_unit({len(units)} refs, detail={detail}, "
            f"owner_name={owner_name!r})"
        )
        return await tools_handler.get_lr_unit(
            list(units),
            detail,
            owners_limit,
            include_plombe_detail,
            historical_overview=historical_overview,
            offset=offset,
            limit=limit,
            owner_name=owner_name,
            condominium_unit=condominium_unit,
            refresh=refresh,
        )

    @mcp.tool()
    @anticipated_tool
    async def find_main_book(
        search: Annotated[
            str | None,
            Field(
                description=(
                    'Book name to search, e.g. "SAVAR"; empty lists every book'
                )
            ),
        ] = None,
        office_id: Annotated[
            str | int | None,
            Field(
                description=(
                    'Land-registry office (zemljišnoknjižni odjel) id, e.g. "284"'
                )
            ),
        ] = None,
        institution_name: Annotated[
            str | None,
            Field(
                description=(
                    "Keep only books of the institution (court) with this name"
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """
        Find land-registry main books (glavna knjiga, glavne knjige zemljišne
        knjige) by name, land-registry office or institution.

        Use this to get the ``main_book_id`` that get_lr_unit needs when only
        the cadastral municipality (katastarska općina) name is known: searching
        "SAVAR" returns main book 21277 of the Zadar court (institution 284).

        Returns:
            Dictionary with ``main_books`` (main_book_id, main_book_name,
            institution_id, court_name) and ``count``
        """
        logger.info(f"Tool invoked: find_main_book({search}, office={office_id})")
        return await tools_handler.find_main_book(search, office_id, institution_name)

    @mcp.tool()
    @anticipated_tool
    async def find_book_of_dc(
        search: Annotated[
            str | None,
            Field(
                description=(
                    'Book name to search, e.g. "ZADAR"; empty lists every book'
                )
            ),
        ] = None,
        office_id: Annotated[
            str | int | None,
            Field(
                description=(
                    "Land-registry office id"
                )
            ),
        ] = None,
        institution_name: Annotated[
            str | None,
            Field(
                description=(
                    "Keep only books of the institution (court) with this name"
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """
        Find books of deposited contracts (knjiga položenih ugovora, KPU) of the
        land registry (zemljišne knjige), by name, office or institution.

        A KPU book holds flats sold before their building had a land-registry
        unit. Whether its id can be used as a main book id for get_lr_unit is
        not verified; the tool returns the search records only.

        Returns:
            Dictionary with ``books_of_dc`` (book_id, book_name, office_id,
            office_name) and ``count``
        """
        logger.info(f"Tool invoked: find_book_of_dc({search}, office={office_id})")
        return await tools_handler.find_book_of_dc(search, office_id, institution_name)

    @mcp.tool()
    @anticipated_tool
    async def get_possession_sheet(
        sheet_number: Annotated[
            str,
            Field(
                description='Possession sheet (posjedovni list) number, matched exactly, e.g. "363"'
            ),
        ],
        municipality: Annotated[
            str,
            Field(
                description=(
                    'Cadastral municipality (katastarska općina, k.o.) by name, e.g. "SAVAR", or '
                    'registration code, e.g. "334979"'
                )
            ),
        ],
        offset: Annotated[
            int, Field(description="Skip this many possessor records (paging)")
        ] = 0,
        limit: Annotated[
            int | None,
            Field(
                description=(
                    "Return at most this many possessor records (null for all); the page block "
                    "says where to continue"
                )
            ),
        ] = None,
        possessor_name: Annotated[
            str | None,
            Field(
                description=(
                    "Keep only the possessors whose name contains every word of this text (case "
                    "and diacritics ignored, words in any order)"
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """
        A cadastre possession sheet (posjedovni list) by number in a cadastral
        municipality: its possessors (posjednici) and every parcel (čestica)
        on it, with areas and land use. For "which parcels are on posjedovni
        list N" and "who is on it" in one call.

        Reads the sheet and the parcel search behind the cadastre's web form
        (three requests). The number is matched exactly; find_possession_sheet
        lists the sheets whose number begins with a text. Possessors are
        cadastre possessors, not land-registry owners: each parcel row carries
        the land-registry unit reference for get_lr_unit. A sheet harmonized
        with the land registry lists no possessors of its own
        (``possessors_in_land_registry`` true): its registered owners come
        back under ``owners`` (register land_registry, read from the sheet B
        the parcel search inlines, OIB included where the registry has it)
        with ``owners_note``, ``possessor_name`` then filters the owners
        (``matching_owners``; ``filter_applied_to`` names the list), and
        ``lr_unit`` names the unit for get_lr_unit. The stub's missing sheet
        id and municipality are filled from the parcel records
        (``sheet.backfilled_from_parcels``).

        Returns:
            ``sheet`` (possession_sheet_id, possession_sheet_number,
            municipality id, code and name, is_condominium, total_ownership),
            ``possessors``, ``total_possessors``, ``distinct_possessors``,
            ``page``, ``parcels`` (parcel_id, parcel_number, area_m2, address,
            land_use, is_building_parcel, is_harmonized, lr_unit,
            inline_owners), ``parcel_count``, ``total_area_m2``,
            ``parcels_complete`` (False, with a ``note``, when the list is as
            long as the longest the search has ever returned, so a cap is not
            ruled out) and ``provenance`` of the sheet and of the parcel list.
        """
        logger.info(
            f"Tool invoked: get_possession_sheet({sheet_number}, {municipality}, "
            f"offset={offset}, limit={limit}, possessor_name={possessor_name!r})"
        )
        return await tools_handler.get_possession_sheet(
            sheet_number, municipality, offset=offset, limit=limit, possessor_name=possessor_name
        )

    @mcp.tool()
    @anticipated_tool
    async def find_possession_sheet(
        sheet_number: Annotated[
            str,
            Field(
                description=(
                    'Possession sheet number (prefix match, e.g. "363")'
                )
            ),
        ],
        municipality: Annotated[
            str,
            Field(
                description=(
                    'Cadastral municipality (katastarska općina, k.o.) by name, e.g. "SAVAR", or '
                    'registration code, e.g. "334979"'
                )
            ),
        ],
    ) -> dict[str, Any]:
        """
        Find cadastre possession sheets (posjedovni list, posjedovni listovi) by
        sheet number in a cadastral municipality (katastar, katastarska općina).

        The records carry the possession sheet id and the sheet number, for
        every sheet whose number begins with the text, at most 50 of them.
        The search index lags the change log: a sheet touched recently can be
        missing here while get_possession_sheet finds it by number, so an
        empty answer is a hint, not proof that the sheet does not exist. For a
        sheet's possessors (posjednici) and parcels call get_possession_sheet
        with the exact number.

        Returns:
            Dictionary with ``possession_sheets`` (possession_sheet_id,
            sheet_number), ``municipality_code`` and ``count``
        """
        logger.info(f"Tool invoked: find_possession_sheet({sheet_number}, {municipality})")
        return await tools_handler.find_possession_sheet(sheet_number, municipality)

    @mcp.tool()
    @anticipated_tool
    async def get_file_status(
        file_number: Annotated[
            str,
            Field(
                description=(
                    'File number as written on the unit, e.g. "Z-12564/2026"'
                )
            ),
        ],
        institution_id: Annotated[
            int,
            Field(
                description=(
                    "Land-registry office id: `institution_id` of the unit from get_lr_unit, or "
                    "of the book from find_main_book"
                )
            ),
        ],
    ) -> dict[str, Any]:
        """
        Processing status of one land-registry file (spis, plomba, zaprimljeni
        prijedlog) by its number, e.g. "Z-12564/2026": what the request is
        (uknjižba, nasljeđivanje, hipoteka ...), where it is in processing, and
        its dates.

        A unit's pending plombe carry only the file number; get_lr_unit with
        include_plombe_detail resolves them all at once. Use this tool when you
        already hold a file number and the office that processes it.

        Returns:
            Dictionary with ``found`` and, when found, ``status`` (file id,
            application content, status description, registration number,
            resolution type, dates); otherwise a ``message``.
        """
        logger.info(f"Tool invoked: get_file_status({file_number}, {institution_id})")
        return await tools_handler.get_file_status(file_number, institution_id)

    @mcp.tool()
    @anticipated_tool
    async def compare_registers(
        parcels: Annotated[
            list[ParcelRef],
            Field(
                description=(
                    'One or more parcel references, each {"parcel_id": ...} (from find_parcel) or'
                    ' {"parcel_number": ..., "municipality": ...}; one entry per reference comes '
                    "back, in order"
                )
            ),
        ],
        include_plombe_detail: Annotated[
            bool,
            Field(
                description=(
                    "Name each pending plomba among the sale blockers (one request per plomba,"
                    " once per unit)"
                )
            ),
        ] = False,
    ) -> dict[str, Any]:
        """
        Are the cadastre possessors (posjednici, posjedovni list) of a parcel
        the same people as its registered owners (vlasnici, vlastovnica /
        B-list)? One call per parcel set, for "is the person using the land
        the person I sign with" (posjednik vs vlasnik, usklađenost katastra i
        zemljišne knjige).

        The cadastre record and the parcel's unit are read (a shared unit
        once) and the two lists of people matched by tax number or folded
        name (case and diacritics ignored); a match on the name alone (a
        relative written differently, "AUGUSTIN, BOŽO" against "AUGUSTIN POK.
        BOŽE", or the words in another order with nothing corroborating it)
        is ``fuzzy``. Each pair says how it was found: ``via`` (tax_number,
        name, name_reordered, name_loose, tax_number_extension: another share
        of an owner already matched, ``extended_from``). Party types are
        inferred and labelled so.

        Returns:
            ``results`` with one entry per reference: ``status``, ``ref``,
            ``parcel_number``, ``municipality_code``, ``lr_unit``,
            ``provenance`` of both registers, ``map_url`` and ``data`` with
            ``relationship`` (same | overlapping | disjoint | cadastre_only |
            no_owners | no_possessors | land_registry_unavailable),
            ``summary`` (plain language), ``matched`` (pairs with ``fuzzy``,
            ``via``, ``extended_from``, ``shares_agree``), ``possessors_only``,
            ``owners_only``, ``possessors`` and ``owners`` (name, share,
            ``party_type_inferred``), ``distinct_possessors``,
            ``distinct_owners``, ``distinct_people``, ``party_types``,
            ``public_body_owner_share``, ``area_check`` (cadastre, sheet A and
            graphical areas), ``sale_blockers`` (the unit's blockers plus
            ``owner_not_possessor`` and ``fuzzy_owner_match``, with a
            verdict; see get_lr_unit), ``owner_flag_counts`` (owners flagged
            likely_deceased, address_abroad, public_body; each owner carries
            ``flags``) and ``notes``. Then ``total``, ``successful``,
            ``failed``, ``units_fetched``, ``relationships`` (count per
            relationship) and ``people`` (distinct possessors, owners and
            people across the whole set). A failed entry carries
            ``error_type``; an entry whose unit could not be read carries
            ``land_registry_error`` and still lists the possessors.
        """
        logger.info(f"Tool invoked: compare_registers({len(parcels)} parcels)")
        return await tools_handler.compare_registers(
            list(parcels), include_plombe_detail=include_plombe_detail
        )

    @mcp.tool()
    @anticipated_tool
    async def build_assembly(
        parcels: Annotated[
            list[ParcelRef],
            Field(
                description=(
                    "Up to 50 parcel references, as for get_parcel"
                )
            ),
        ],
        include_zoning: Annotated[
            bool,
            Field(
                description=(
                    "Read each parcel's building-areas zoning as well (one WFS lookup per parcel;"
                    " slower)"
                )
            ),
        ] = False,
        weights: Annotated[
            dict[str, float] | None,
            Field(
                description=(
                    'Override any factor weight, e.g. {"in_building_area": 0.4}; factors: '
                    "single_owner, owner_is_possessor, no_encumbrances, no_pending_plombe, "
                    "in_building_area"
                )
            ),
        ] = None,
        export: Annotated[
            Literal["parcels_csv", "persons_csv", "matrix_csv", "blockers_csv", "geojson"]
            | None,
            Field(
                description=(
                    '"parcels_csv", "persons_csv", "matrix_csv" or "blockers_csv" put CSV text '
                    "under export.text;"
                    ' "geojson" puts a FeatureCollection of the parcels that have an outline '
                    "under export (scores in the properties, parcels without an outline under "
                    "export.skipped)"
                )
            ),
        ] = None,
        persons_offset: Annotated[
            int,
            Field(
                description=(
                    "Skip this many ranked persons"
                )
            ),
        ] = 0,
        persons_limit: Annotated[
            int | None,
            Field(
                description=(
                    "Return at most this many ranked persons (default 50; null for all)"
                )
            ),
        ] = 50,
        include_plombe_detail: Annotated[
            bool,
            Field(
                description="Name each pending plomba among the sale blockers (one request each)"
            ),
        ] = False,
        include_blockers: Annotated[
            bool,
            Field(description="Return the blockers table (one row per parcel and blocker)"),
        ] = True,
    ) -> dict[str, Any]:
        """
        Land-assembly analysis (okrupnjavanje zemljišta, due diligence) of a
        set of parcels: who owns or possesses what (the persons x parcels
        matrix), the persons ranked by the area they control and grouped by
        surname, and the parcels ranked by how easy they look to acquire,
        with the weights shown so the rule can be questioned and changed.

        Reads each parcel's cadastre record, its land-registry unit (shared
        units once) and the register comparison; with include_zoning also
        its building-areas screening. At most 50 parcels per call. The score
        is a weighted share of yes/no factors: single_owner,
        owner_is_possessor, no_encumbrances, no_pending_plombe,
        in_building_area (only with include_zoning); a factor that could not
        be evaluated is left out rather than counted against the parcel, and
        each parcel's ``factors`` and ``notes`` say which. Party types are
        inferred from names. Controlled areas use cadastre areas.

        Returns:
            ``totals`` (areas by land use, relationship, zoning and verdict;
            distinct people, owners, possessors; party types; parcels with
            encumbrances, plombe, in a building area; persons likely deceased
            or abroad), ``parcels`` (easiest first: relationship, owners and
            possessors, sale_verdict, blocker_counts, blocker_kinds, zoning,
            area_mismatch, score, map_url, provenance), ``persons`` (a page
            of the ranking with areas, party_type_inferred, likely_deceased,
            address_abroad) with ``persons_page``, ``surname_groups`` (with
            the estate and abroad counts per family), ``matrix``,
            ``blockers`` (one row per parcel and counted blocker: the list
            the verdicts rest on), ``scores``, ``weights``, ``notes``,
            ``failed`` (references not read, with error_type),
            ``units_fetched`` and ``export`` when asked.
        """
        logger.info(
            f"Tool invoked: build_assembly({len(parcels)} parcels, zoning={include_zoning}, "
            f"export={export})"
        )
        return await tools_handler.build_assembly(
            list(parcels),
            include_zoning=include_zoning,
            weights=weights,
            export=export,
            persons_offset=persons_offset,
            persons_limit=persons_limit,
            include_plombe_detail=include_plombe_detail,
            include_blockers=include_blockers,
        )

    @mcp.tool()
    @anticipated_tool
    async def find_parcels_in_area(
        municipality: Annotated[
            str,
            Field(
                description=(
                    'Cadastral municipality (katastarska općina, k.o.) by name, e.g. "SAVAR", or '
                    'registration code, e.g. "334979"'
                )
            ),
        ],
        bbox: Annotated[
            list[float] | None,
            Field(
                description=(
                    "[min_x, min_y, max_x, max_y] in EPSG:3765 metres"
                )
            ),
        ] = None,
        polygon: Annotated[
            str | list[list[float]] | None,
            Field(
                description=(
                    'WKT "POLYGON((x y, x y, ...))" or a list of [x, y] vertices, EPSG:3765'
                )
            ),
        ] = None,
        center: Annotated[
            list[float] | None,
            Field(
                description=(
                    "[x, y] of a point in EPSG:3765, together with radius_m"
                )
            ),
        ] = None,
        radius_m: Annotated[
            float | None,
            Field(
                description=(
                    "Radius in metres around center"
                )
            ),
        ] = None,
        relation: Annotated[
            Literal["intersects", "within"],
            Field(
                description=(
                    '"intersects" (default): the parcel touches the area; "within": the parcel '
                    "lies wholly inside it"
                )
            ),
        ] = "intersects",
        offset: Annotated[
            int,
            Field(
                description=(
                    "Skip this many parcels"
                )
            ),
        ] = 0,
        limit: Annotated[
            int | None,
            Field(
                description=(
                    "Return at most this many parcels (default 50; null for all)"
                )
            ),
        ] = 50,
        include_geojson: Annotated[
            bool,
            Field(
                description=(
                    "Also return the page as a GeoJSON FeatureCollection"
                )
            ),
        ] = False,
    ) -> dict[str, Any]:
        """
        Find the parcels (čestice) of a cadastral municipality inside an area:
        a bounding box, a polygon, or a radius around a point, so that a
        target area can be defined without knowing any parcel number
        (čestice unutar područja, u krugu od N metara).

        Reads the cached cadastral map of the municipality (downloaded on
        first use, refreshed with download_municipality_gis). Coordinates are
        EPSG:3765 (HTRS96/TM) metres, the system get_parcel_geometry returns;
        longitude/latitude is refused with a hint. Gives parcel numbers,
        graphical areas, centroids and map links; use get_parcel /
        get_lr_unit on the numbers for the registers' records.

        Returns:
            ``municipality_code``, ``query`` (as understood), ``parcels`` (each
            with parcel_number, area_m2, centroid, bounds, distance_m for a
            radius query, map_url), ``total`` and ``total_area_m2`` over every
            match, a ``page`` block (offset, limit, total, returned, truncated,
            next_offset), ``dataset`` (parcel_count of the municipality, crs,
            source, downloaded_at, note) and ``geojson`` when asked.
        """
        logger.info(
            f"Tool invoked: find_parcels_in_area({municipality}, bbox={bbox}, "
            f"polygon={'yes' if polygon else None}, center={center}, radius_m={radius_m})"
        )
        return await tools_handler.find_parcels_in_area(
            municipality,
            bbox=bbox,
            polygon=polygon,
            center=center,
            radius_m=radius_m,
            relation=relation,
            offset=offset,
            limit=limit,
            include_geojson=include_geojson,
        )

    @mcp.tool()
    @anticipated_tool
    async def find_parcel_neighbours(
        parcel_number: Annotated[
            str,
            Field(
                description=(
                    'Cadastral parcel number, e.g. "103/2"; a building parcel as "35/1.ZGR", '
                    '"35/1 ZGR" or "*35/1"'
                )
            ),
        ],
        municipality: Annotated[
            str,
            Field(
                description=(
                    'Cadastral municipality (katastarska općina, k.o.) by name, e.g. "SAVAR", or '
                    'registration code, e.g. "334979"'
                )
            ),
        ],
        tolerance_m: Annotated[
            float,
            Field(
                description=(
                    "Gap two outlines may have and still count as touching, in metres (default "
                    "0.10)"
                )
            ),
        ] = 0.10,
        offset: Annotated[
            int,
            Field(
                description=(
                    "Skip this many neighbours"
                )
            ),
        ] = 0,
        limit: Annotated[
            int | None,
            Field(
                description=(
                    "Return at most this many neighbours (default 50; null for all)"
                )
            ),
        ] = 50,
        include_geojson: Annotated[
            bool,
            Field(
                description=(
                    "Also return the seed parcel and the page as GeoJSON"
                )
            ),
        ] = False,
    ) -> dict[str, Any]:
        """
        The neighbours of a parcel (susjedne čestice): the parcels sharing a
        boundary with it, longest common boundary first, and those touching
        it at a corner only (``touches_at_point``). For walking outward from
        a seed parcel when assembling land.

        Reads the cached cadastral map of the municipality (downloaded on
        first use). Two outlines within ``tolerance_m`` of each other count
        as touching. Gives parcel numbers, graphical areas and map links; use
        get_parcel / get_lr_unit on the numbers for the registers' records.

        Returns:
            ``parcel`` (the seed's row), ``neighbours`` (rows with
            shared_boundary_m and touches_at_point), ``total``,
            ``total_area_m2`` of every neighbour, ``page``, ``dataset`` and
            ``geojson`` when asked.
        """
        logger.info(
            f"Tool invoked: find_parcel_neighbours({parcel_number}, {municipality}, "
            f"tolerance_m={tolerance_m})"
        )
        return await tools_handler.find_parcel_neighbours(
            parcel_number,
            municipality,
            tolerance_m=tolerance_m,
            offset=offset,
            limit=limit,
            include_geojson=include_geojson,
        )

    @mcp.tool()
    @anticipated_tool
    async def download_municipality_gis(
        municipality: Annotated[
            str,
            Field(
                description=(
                    'Cadastral municipality (katastarska općina, k.o.) by name, e.g. "SAVAR", or '
                    'registration code, e.g. "334979"'
                )
            ),
        ],
        force: Annotated[
            bool,
            Field(
                description=(
                    "Download again even when the municipality is already cached"
                )
            ),
        ] = False,
    ) -> dict[str, Any]:
        """
        Download the GIS data (parcel boundaries, GML) of a whole cadastral
        municipality (katastarska općina) into the local cache, or refresh it.

        get_parcel_geometry and get_parcel_zoning do this on demand for the
        parcel they need; call this to fetch a municipality ahead of many
        lookups, to refresh stale data (``force=true``), or to learn how many
        parcels the municipality has.

        Returns:
            Dictionary with ``municipality_code``, ``download_url``,
            ``already_cached``, ``downloaded_at`` (when the cached ZIP was
            downloaded, ISO 8601 UTC: the age of the data every geometry and
            zoning answer for this municipality rests on), ``zip_path``,
            ``zip_size_bytes``, ``gml_path``, ``parcel_count`` and ``source``
            (the server the cache came from).
        """
        logger.info(f"Tool invoked: download_municipality_gis({municipality}, force={force})")
        return await tools_handler.download_municipality_gis(municipality, force)

    # ========================================================================
    # PROMPTS - User-selected templates
    # ========================================================================

    @mcp.prompt()
    async def explain_ownership_structure(parcel_id: str) -> str:
        """
        Explain the cadastre possession structure of one parcel (posjednici,
        posjedovni list): who is listed, with what shares, whether it is
        co-possession. Reads the parcel record and returns an analysis
        request with the data filled in. parcel_id comes from find_parcel or
        get_parcel. Cadastre possessors only; for the registered owners
        (vlasnici) use the get_lr_unit tool.
        """
        logger.info(f"Prompt invoked: explain_ownership_structure({parcel_id})")
        return await prompts_handler.explain_ownership_structure(parcel_id)

    @mcp.prompt()
    async def property_report(parcel_id: str) -> str:
        """
        Property report of one parcel: summary, land-use breakdown,
        possession structure, development considerations. Reads the parcel
        record (area, land use parts, building right, possession sheets) and
        returns a report request with the data filled in. parcel_id comes
        from find_parcel or get_parcel.
        """
        logger.info(f"Prompt invoked: property_report({parcel_id})")
        return await prompts_handler.property_report(parcel_id)

    @mcp.prompt()
    async def compare_parcels(parcel_ids: list[str]) -> str:
        """
        Compare two or more parcels side by side: size, land use, building
        right, number of possessors. Reads each parcel record and returns a
        comparison request with the data filled in; a parcel that cannot be
        read is noted, not fatal. At least two parcel_ids (from find_parcel or
        get_parcel).
        """
        logger.info(f"Prompt invoked: compare_parcels({len(parcel_ids)} parcels)")
        return await prompts_handler.compare_parcels(parcel_ids)

    @mcp.prompt()
    async def land_use_summary(parcel_id: str) -> str:
        """
        Land-use distribution of one parcel (način uporabe: oranica, pašnjak,
        šuma ...): each part with its area and share of the whole. Reads the
        parcel record and returns an analysis request with the breakdown
        filled in. parcel_id comes from find_parcel or get_parcel.
        """
        logger.info(f"Prompt invoked: land_use_summary({parcel_id})")
        return await prompts_handler.land_use_summary(parcel_id)

    @mcp.prompt()
    async def due_diligence_report(
        parcels: str, municipality: str, language: str = "hr", format: str = "markdown"
    ) -> str:
        """
        Due-diligence screening report of a set of parcels for a reader who
        did not run the tool (an investor's email to a lawyer): calls
        build_assembly on the parcels (comma-separated parcel numbers, or
        parcel_id values from find_parcel) and renders the result with a fixed
        section order, Croatian register terms with the English gloss,
        provenance on every fact and the screening and inference notices.
        language "hr" or "en"; format "markdown" or "html" (one self-contained
        file).
        """
        logger.info(f"Prompt invoked: due_diligence_report({parcels!r}, {municipality!r})")
        return prompts_handler.due_diligence_report(parcels, municipality, language, format)

    logger.info("MCP server initialized successfully")
    logger.info(
        "Available tools: find_parcel, get_parcel, resolve_municipality, "
        "list_municipalities, get_parcel_geometry, get_parcel_zoning, "
        "compare_registers, build_assembly, find_parcels_in_area, find_parcel_neighbours, "
        "list_cadastral_offices, get_lr_unit, get_file_status, find_main_book, "
        "find_book_of_dc, find_possession_sheet, get_possession_sheet, "
        "download_municipality_gis"
    )
    logger.info("Available prompts: explain_ownership_structure, property_report, "
                "compare_parcels, land_use_summary, due_diligence_report")
    logger.info("Available resources: cadastral://parcel/{id}, cadastral://municipality/{code}, "
                "cadastral://office/{code}")

    return mcp
