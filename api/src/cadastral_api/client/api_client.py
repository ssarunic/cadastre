"""HTTP client for Croatian Cadastral API with rate limiting and error handling.

⚠️ DEMO/EDUCATIONAL PROJECT ONLY ⚠️

This client demonstrates how a cadastral API integration could work.
It is configured to use a MOCK SERVER by default for safe testing and learning.

BEFORE USING ANOTHER SERVER:
- Verify that you have the rights to use that server and its data (terms of
  service, data protection); real cadastral data is personal data
- You do so at your own risk; see docs/legal.md
- Do not bypass authorization, rate limits or access restrictions

The author is available to advise the Croatian government on official AI and API
implementation if requested.

See README.md and CLAUDE.md for complete disclaimer.
"""

import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, TypeVar

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from ..cache import Fetched, Inflight, ResponseCache
from ..cache import from_config as cache_from_config
from ..cache import policy as cache_policy
from ..exceptions import CadastralAPIError, ErrorType
from ..gis import GISCache, GMLParser, ParcelIndex
from ..models import (
    BookOfDCSearchResult,
    CadastralOffice,
    FileStatus,
    LandRegistryUnit,
    LandRegistryUnitDetailed,
    MainBookSearchResult,
    MunicipalitySearchResult,
    ParcelInfo,
    ParcelSearchResult,
    PossessionSheet,
    PossessionSheetSearchData,
    PossessionSheetSearchResult,
    SearchedParcel,
)
from ..models.gis_entities import ParcelGeometry
from ..models.planning_entities import ParcelZoning
from ..models.provenance import Provenance, Register, now_utc_iso
from ..planning import PlanningWFSClient, validate_min_overlap
from ..rate_limiter import RateLimiter
from ..utils import is_building_parcel_number, normalize_parcel_number, parse_file_number

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

UnknownFieldsPolicy = Literal["warn", "ignore", "error"]
UNKNOWN_FIELDS_POLICIES: tuple[str, ...] = ("warn", "ignore", "error")

# Unknown key paths already reported by this process (logged once each).
_REPORTED_UNKNOWN_FIELDS: set[str] = set()

M = TypeVar("M", bound=BaseModel)
T = TypeVar("T")


class _Record(Protocol):
    """A parsed record the client stamps with its provenance."""

    provenance: Provenance | None


R = TypeVar("R", bound=_Record)

# Cache backend failures already logged by this process (logged once each).
_REPORTED_CACHE_FAILURES: set[str] = set()


def _backfill_sheet(sheet: PossessionSheet, parcels: list[SearchedParcel]) -> list[str]:
    """Fill the fields a harmonized stub lacks from the sheet's parcel records; names them."""
    filled: list[str] = []
    if not parcels:
        return filled
    if sheet.possession_sheet_id is None and sheet.possession_sheet_number is not None:
        wanted = str(sheet.possession_sheet_number).strip()
        for parcel in parcels:
            for part in parcel.parcel_parts:
                if part.possession_sheet_id and str(part.possession_sheet_number) == wanted:
                    sheet.possession_sheet_id = part.possession_sheet_id
                    filled.append("possession_sheet_id")
                    break
            if sheet.possession_sheet_id is not None:
                break
    first = parcels[0]
    if sheet.cad_municipality_reg_num is None and first.cad_municipality_reg_num:
        sheet.cad_municipality_reg_num = first.cad_municipality_reg_num
        filled.append("cad_municipality_reg_num")
    if sheet.cad_municipality_name is None and first.cad_municipality_name:
        sheet.cad_municipality_name = first.cad_municipality_name
        filled.append("cad_municipality_name")
    return filled


@dataclass(frozen=True)
class PossessionSheetParcels:
    """A possession sheet and the parcels on it (``get_possession_sheet_parcels``)."""

    sheet: PossessionSheet
    parcels: list[SearchedParcel]
    #: Provenance of the parcel list (the sheet carries its own).
    parcels_provenance: Provenance
    #: True when the list is as long as the longest ever observed, so a
    #: server-side cap cannot be ruled out.
    maybe_truncated: bool
    #: Sheet fields the stub of a harmonized sheet lacked and the parcel
    #: records supplied (``possession_sheet_id``, ``cad_municipality_reg_num``,
    #: ``cad_municipality_name``); empty for a full sheet.
    backfilled_from_parcels: tuple[str, ...] = ()

    @property
    def total_area_m2(self) -> int:
        return sum(p.area_numeric or 0 for p in self.parcels)

    @property
    def possessors_in_land_registry(self) -> bool:
        """A harmonized sheet: the cadastre lists no possessors, the unit's owners are they."""
        return self.sheet.possessors_in_land_registry

    @property
    def lr_unit(self) -> LandRegistryUnit | None:
        """The land-registry unit the sheet's parcels refer to (the first parcel's)."""
        for parcel in self.parcels:
            unit = parcel.resolved_lr_unit()
            if unit is not None:
                return unit
        return None

    def owner_rows(self) -> list[dict[str, Any]]:
        """The registered owners the parcel search inlined (harmonized parcels), unit read once.

        Rows in the canonical owner shape of ``OwnershipSheetB.owner_rows``;
        empty when no parcel carries an inline unit with sheet B.
        """
        seen: set[tuple[str, int]] = set()
        rows: list[dict[str, Any]] = []
        for parcel in self.parcels:
            unit = parcel.lr_unit
            if unit is None or unit.ownership_sheet_b is None:
                continue
            key = (unit.lr_unit_number, unit.main_book_id)
            if key in seen:
                continue
            seen.add(key)
            rows.extend(unit.owner_rows())
        return rows


class CadastralAPIClient:
    """
    Client for Croatian Cadastral System API (Uređena zemlja).

    Provides methods to search for parcels and retrieve detailed information
    with automatic rate limiting and retry logic.
    """

    # Default to localhost test server (production API requires authorization)
    BASE_URL = os.getenv("CADASTRAL_API_BASE_URL", "http://localhost:8000")
    DEFAULT_TIMEOUT = float(os.getenv("CADASTRAL_API_TIMEOUT", "10.0"))
    #: Read timeout of the two endpoints that return a whole record at once
    #: (``/lr/lr-unit``, ``/cad/parcel-info``). A large condominium is
    #: thousands of shares or possessors that the server assembles on every
    #: request, unpaged and uncached: 20-25 s before the first byte for a
    #: unit of 2,900 owners. The connect timeout stays at ``timeout`` so a
    #: server that is down is still reported quickly.
    LONG_READ_TIMEOUT = 120.0
    DEFAULT_RATE_LIMIT = float(os.getenv("CADASTRAL_API_RATE_LIMIT", "0.375"))
    DEFAULT_UNKNOWN_FIELDS = os.getenv("CADASTRAL_API_UNKNOWN_FIELDS", "warn")
    MAX_RETRIES = 3

    def __init__(
        self,
        base_url: str | None = None,
        rate_limit: float | None = None,
        timeout: float | None = None,
        cache_dir: Path | str | None = None,
        unknown_fields: UnknownFieldsPolicy | None = None,
        planning_wfs_urls: list[str] | str | None = None,
        long_timeout: float | None = None,
        cache: ResponseCache | str | None = None,
    ) -> None:
        """
        Initialize the API client.

        Args:
            base_url: API base URL (default: from CADASTRAL_API_BASE_URL env or http://localhost:8000)
            rate_limit: Minimum seconds between requests
                (default: from CADASTRAL_API_RATE_LIMIT env or 0.375)
            timeout: Request timeout in seconds (default: from CADASTRAL_API_TIMEOUT env or 10.0)
            long_timeout: Read timeout in seconds for the endpoints that
                return a whole land-registry unit or parcel record, which a
                large condominium makes slow on the server side (default:
                ``LONG_READ_TIMEOUT``, 120 s, or ``timeout`` when that is
                larger). Connecting still has ``timeout``.
            cache_dir: Directory for GIS data cache (default: ~/.cadastral_api_cache)
            unknown_fields: What to do when a response carries a key no model
                declares (it is kept in ``source_fields`` either way):
                ``"warn"`` logs each new key path once per process (default),
                ``"ignore"`` stays silent, ``"error"`` raises
                ``CadastralAPIError(INVALID_RESPONSE, reason="unknown_fields")``.
            planning_wfs_urls: Endpoint(s) of the spatial-plan building-areas
                WFS, tried in order (default: ``CADASTRAL_PLANNING_WFS_URLS``
                or ``<base_url>/planning/wfs``, the mock server's imitation).
            cache: Where upstream responses are kept between calls: a
                ``ResponseCache`` backend, ``"memory"`` (in this process,
                the default) or ``"off"``; None reads ``CADASTRAL_CACHE``.
                Every response is kept for the lifetime of its data class
                (30 min for records that name people, longer for reference
                lists); ``refresh=True`` on a record method reads past it.

        Environment Variables:
            CADASTRAL_API_BASE_URL: API base URL (default: http://localhost:8000)
            CADASTRAL_API_RATE_LIMIT: Rate limit in seconds (default: 0.375)
            CADASTRAL_API_TIMEOUT: Request timeout in seconds (default: 10.0)
            CADASTRAL_API_UNKNOWN_FIELDS: warn | ignore | error (default: warn)
            CADASTRAL_PLANNING_WFS_URLS: comma-separated building-areas WFS mirrors
            CADASTRAL_CACHE: memory | off (default: memory)
            CADASTRAL_CACHE_MEMORY_MB: byte budget of the memory cache (default: 64)

        Note:
            Before pointing the client at any server other than the included
            mock, verify that you have the rights to use that server; see
            docs/legal.md. Use is at your own risk.
        """
        self.base_url = base_url or self.BASE_URL
        self.rate_limit = rate_limit if rate_limit is not None else self.DEFAULT_RATE_LIMIT
        self.timeout = timeout if timeout is not None else self.DEFAULT_TIMEOUT
        self.long_timeout = (
            long_timeout if long_timeout is not None
            else max(self.timeout, self.LONG_READ_TIMEOUT)
        )
        policy = unknown_fields or self.DEFAULT_UNKNOWN_FIELDS
        if policy not in UNKNOWN_FIELDS_POLICIES:
            raise ValueError(
                f"unknown_fields must be one of {UNKNOWN_FIELDS_POLICIES}, got {policy!r}"
            )
        self.unknown_fields: UnknownFieldsPolicy = policy  # type: ignore[assignment]
        self._limiter = RateLimiter(self.rate_limit)
        # Per-file parsers and indexes, built once; the lock keeps two
        # threads asking for the same municipality from both parsing it.
        self._gml_parsers: dict[Path, tuple[int, GMLParser]] = {}
        self._parcel_indexes: dict[Path, tuple[int, ParcelIndex]] = {}
        self._gis_lock = threading.Lock()

        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
        }

        self.client = httpx.Client(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout,
            follow_redirects=True,
        )

        # Initialize GIS cache
        self.gis_cache = GISCache(cache_dir, base_url=self.base_url)

        # Spatial-plan building areas (mirrors rotate on gateway errors)
        self.planning = PlanningWFSClient(
            planning_wfs_urls,
            timeout=self.timeout,
            rate_limit=self.rate_limit,
            api_base_url=self.base_url,
        )

        # Upstream responses kept between calls, and the per-key locks that
        # make concurrent identical requests one fetch.
        self.cache: ResponseCache = cache_from_config(cache)
        self._inflight = Inflight()

    def __enter__(self) -> "CadastralAPIClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit - close HTTP client."""
        self.close()

    def close(self) -> None:
        """Close the HTTP clients."""
        self.client.close()
        self.planning.close()

    def _wait_for_rate_limit(self) -> None:
        """Wait for this request's slot: one upstream request per ``rate_limit``.

        Shared by every thread using this client (see ``RateLimiter``), so
        concurrent callers queue one interval apart instead of bursting.
        """
        self._limiter.wait()

    def _request(
        self,
        endpoint: str,
        params: dict[str, str] | None = None,
        *,
        json_body: dict | None = None,
        read_timeout: float | None = None,
        retry_count: int = 0,
    ) -> dict:
        """
        Make an HTTP request with rate limiting and retry logic.

        A GET request, or a POST request when ``json_body`` is given (the few
        endpoints that take a JSON body, e.g. ``/lr/file-status``).

        Args:
            endpoint: API endpoint path
            params: Query parameters
            json_body: JSON request body; makes the request a POST
            read_timeout: Wait this long for the response body (the time to
                the first byte included) instead of ``timeout``; connecting
                keeps ``timeout``. For the endpoints whose response the
                server is slow to assemble (``long_timeout``).
            retry_count: Current retry attempt number

        Returns:
            JSON response as dictionary

        Raises:
            CadastralAPIError: Any API error occurred
        """
        self._wait_for_rate_limit()
        timeout: float | httpx.Timeout = self.timeout
        if read_timeout is not None:
            timeout = httpx.Timeout(self.timeout, read=read_timeout)

        def retry() -> dict:
            return self._request(
                endpoint,
                params,
                json_body=json_body,
                read_timeout=read_timeout,
                retry_count=retry_count + 1,
            )

        try:
            if json_body is not None:
                response = self.client.post(endpoint, json=json_body, timeout=timeout)
            else:
                response = self.client.get(endpoint, params=params, timeout=timeout)

            # Handle rate limiting
            if response.status_code == 429:
                if retry_count < self.MAX_RETRIES:
                    time.sleep(2 ** retry_count)  # Exponential backoff
                    return retry()
                raise CadastralAPIError(
                    error_type=ErrorType.RATE_LIMIT,
                    details={"retry_count": retry_count, "max_retries": self.MAX_RETRIES},
                )

            # Handle server errors with retry
            if 500 <= response.status_code < 600:
                if retry_count < self.MAX_RETRIES:
                    time.sleep(1.5 ** retry_count)
                    return retry()
                raise CadastralAPIError(
                    error_type=ErrorType.SERVER_ERROR,
                    details={
                        "status_code": response.status_code,
                        "response_text": response.text,
                        "retry_count": retry_count,
                    },
                )

            # The server refused: the data needs an authorisation this client
            # does not have. Named apart from transport failures so that a
            # refusal is never read as an empty parcel or a network problem.
            if response.status_code in (401, 403):
                raise CadastralAPIError(
                    error_type=ErrorType.ACCESS_DENIED,
                    details={"endpoint": endpoint, "status_code": response.status_code},
                )
            if response.status_code >= 400:
                raise CadastralAPIError(
                    error_type=ErrorType.HTTP_ERROR,
                    details={
                        "endpoint": endpoint,
                        "status_code": response.status_code,
                        "response_text": response.text[:500],
                    },
                )

            return response.json()

        except httpx.TimeoutException as e:
            raise CadastralAPIError(
                error_type=ErrorType.TIMEOUT,
                details={
                    "timeout_seconds": read_timeout if read_timeout is not None else self.timeout,
                    "endpoint": endpoint,
                },
                cause=e,
            ) from e
        except httpx.ConnectError as e:
            raise CadastralAPIError(
                error_type=ErrorType.CONNECTION,
                details={"endpoint": endpoint},
                cause=e,
            ) from e
        except httpx.HTTPError as e:
            raise CadastralAPIError(
                error_type=ErrorType.CONNECTION,
                details={"endpoint": endpoint},
                cause=e,
            ) from e
        except ValueError as e:
            raise CadastralAPIError(
                error_type=ErrorType.INVALID_RESPONSE,
                details={"endpoint": endpoint},
                cause=e,
            ) from e

    # ------------------------------------------------------------------
    # Response cache
    # ------------------------------------------------------------------

    def _fetch(
        self,
        parse: Callable[[Any], T],
        endpoint: str,
        params: dict[str, str] | None = None,
        *,
        json_body: dict[str, Any] | None = None,
        read_timeout: float | None = None,
        use_cache: bool = True,
    ) -> tuple[T, Fetched]:
        """``_request`` through the response cache, parsed.

        ``parse`` turns a body into the result, raising ``CadastralAPIError``
        on an empty or invalid one. An endpoint with a data class
        (:mod:`cadastral_api.cache.policy`) is looked up first: a stored body
        that parses is returned with the time it was fetched, without
        touching the rate limiter. A stored body the current models reject
        (``INVALID_RESPONSE``: a model changed since the entry was written)
        is deleted and treated as a miss, so a hit never raises where a miss
        would not have. A miss holds the key's in-flight lock while the
        request runs, so that two threads asking for the same record make
        one fetch, and stores the body once ``parse`` has accepted it, for
        the class lifetime; an error or an empty answer is never stored.
        ``use_cache=False`` skips the lookup but still stores the fresh
        response, replacing the old entry.
        """
        data_class = cache_policy.data_class_of(endpoint)
        if data_class is None:
            body = self._request(endpoint, params, json_body=json_body, read_timeout=read_timeout)
            return parse(body), Fetched(body, now_utc_iso(), from_cache=False)
        method = "POST" if json_body is not None else "GET"
        key = cache_policy.cache_key(self.base_url, method, endpoint, params, json_body)
        with self._inflight(key):
            if use_cache:
                hit = self._read_cache(key)
                if hit is not None:
                    try:
                        return parse(hit.body), Fetched(hit.body, hit.fetched_at, from_cache=True)
                    except CadastralAPIError as e:
                        if e.error_type is not ErrorType.INVALID_RESPONSE:
                            raise
                        logger.warning(
                            "Cached response for %s no longer parses (%s); fetching it again",
                            endpoint,
                            e.details.get("reason"),
                        )
                        self._delete_cache(key)
            body = self._request(endpoint, params, json_body=json_body, read_timeout=read_timeout)
            fetched_at = now_utc_iso()
            result = parse(body)
            if body:  # an empty answer is a "not found", never cached
                self._write_cache(key, endpoint, data_class, body, fetched_at)
            return result, Fetched(body, fetched_at, from_cache=False)

    def _fetch_record(
        self,
        parse: Callable[[Any], R],
        endpoint: str,
        params: dict[str, str],
        register: Register,
        *,
        read_timeout: float | None = None,
        refresh: bool = False,
    ) -> R:
        """``_fetch`` for a record that carries provenance: fetched, parsed and stamped.

        ``refresh`` reads past a cached copy. The provenance names the
        register, the URL and when the upstream sent the record (the original
        fetch when it came from the cache).
        """
        record, fetched = self._fetch(
            parse, endpoint, params, read_timeout=read_timeout, use_cache=not refresh
        )
        record.provenance = self._provenance(
            register, endpoint, params, fetched_at=fetched.fetched_at
        )
        return record

    def _read_cache(self, key: str) -> cache_policy.Envelope | None:
        """The decoded entry under ``key``, or None (a backend failure is a miss)."""
        try:
            raw = self.cache.get(key)
        except Exception as e:  # noqa: BLE001 - the cache is optional by contract
            self._cache_failed("get", e)
            return None
        if raw is None:
            return None
        envelope = cache_policy.decode(raw)
        if envelope is None:
            self._delete_cache(key)
        return envelope

    def _write_cache(
        self,
        key: str,
        endpoint: str,
        data_class: cache_policy.ClassPolicy,
        body: Any,
        fetched_at: str,
    ) -> None:
        try:
            self.cache.set(
                key,
                cache_policy.encode(
                    body, fetched_at=fetched_at, endpoint=endpoint, data_class=data_class.name
                ),
                data_class.lifetime,
            )
        except Exception as e:  # noqa: BLE001
            self._cache_failed("set", e)

    def _delete_cache(self, key: str) -> None:
        try:
            self.cache.delete(key)
        except Exception as e:  # noqa: BLE001
            self._cache_failed("delete", e)

    @staticmethod
    def _cache_failed(operation: str, error: Exception) -> None:
        """Log a backend failure once per operation; the client carries on without the entry."""
        marker = f"{operation}:{type(error).__name__}"
        if marker not in _REPORTED_CACHE_FAILURES:
            _REPORTED_CACHE_FAILURES.add(marker)
            logger.warning("Response cache %s failed (%s); continuing without it", operation, error)

    def _provenance(
        self,
        register: Register,
        endpoint: str,
        params: dict[str, str] | None = None,
        *,
        fetched_at: str | None = None,
    ) -> Provenance:
        """The provenance of a record: its register, the exact URL, and when the upstream sent it.

        ``fetched_at`` is the time of the upstream fetch (the original one
        for a record served from the cache); without it, now.
        """
        url = self.client.build_request("GET", endpoint, params=params).url
        return Provenance(
            register=register, source_url=str(url), retrieved_at=fetched_at or now_utc_iso()
        )

    # ------------------------------------------------------------------
    # Response validation
    # ------------------------------------------------------------------

    def _parse(
        self, model: type[M], data: Any, endpoint: str, details: dict[str, Any] | None = None
    ) -> M:
        """Validate one server object into ``model`` and apply the unknown-fields policy."""
        try:
            instance = model.model_validate(data)
        except ValidationError as e:
            raise CadastralAPIError(
                error_type=ErrorType.INVALID_RESPONSE,
                details={"endpoint": endpoint, **(details or {}), "reason": "validation_failed"},
                cause=e,
            ) from e
        self._check_unknown_fields(instance, endpoint, details)
        return instance

    def _parse_list(
        self, model: type[M], data: Any, endpoint: str, details: dict[str, Any] | None = None
    ) -> list[M]:
        """Validate a list response; the unknown-fields policy applies to every item."""
        if not isinstance(data, list):
            raise CadastralAPIError(
                error_type=ErrorType.INVALID_RESPONSE,
                details={"endpoint": endpoint, **(details or {}), "reason": "not_a_list"},
            )
        return [self._parse(model, item, endpoint, details) for item in data]

    def _check_unknown_fields(
        self, instance: BaseModel, endpoint: str, details: dict[str, Any] | None
    ) -> None:
        if self.unknown_fields == "ignore":
            return
        unknown = sorted(_unknown_field_paths(instance, endpoint))
        if not unknown:
            return
        if self.unknown_fields == "error":
            raise CadastralAPIError(
                error_type=ErrorType.INVALID_RESPONSE,
                details={
                    "endpoint": endpoint,
                    **(details or {}),
                    "reason": "unknown_fields",
                    "unknown_fields": ", ".join(unknown),
                },
            )
        for path in unknown:
            if path not in _REPORTED_UNKNOWN_FIELDS:
                _REPORTED_UNKNOWN_FIELDS.add(path)
                logger.warning(
                    "Server sent a field no model declares: %s (kept in source_fields)", path
                )

    def list_cadastral_offices(self) -> list[CadastralOffice]:
        """
        List all cadastral offices (Područni uredi za katastar) in Croatia.

        Returns:
            List of CadastralOffice objects (21 offices total)

        Raises:
            CadastralAPIError: Any API error occurred

        Note:
            Returns complete list of all cadastral offices without pagination.
            Office IDs match the institutionId field in parcel information responses.
        """
        endpoint = "/search-cad-parcels/offices"

        def parse(body: Any) -> list[CadastralOffice]:
            if not body:
                raise CadastralAPIError(
                    error_type=ErrorType.INVALID_RESPONSE,
                    details={"endpoint": endpoint, "reason": "empty_response"},
                )
            return self._parse_list(CadastralOffice, body, endpoint)

        offices, _ = self._fetch(parse, endpoint)
        return offices

    def find_municipality(
        self,
        search_term: str | None = None,
        office_id: str | int | None = None,
        department_id: str | int | None = None,
    ) -> list[MunicipalitySearchResult]:
        """
        Find municipalities by name, code, or filter by cadastral office/department.

        Args:
            search_term: Municipality name (e.g., "SAVAR") or code (e.g., "334979")
            office_id: Filter by cadastral office ID (e.g., "114" for Zadar)
            department_id: Filter by department ID (e.g., "116")

        Returns:
            List of MunicipalitySearchResult objects

        Raises:
            CadastralAPIError: Any API error occurred

        Examples:
            # Find by name
            municipalities = client.find_municipality("SAVAR")

            # Filter by office (162 municipalities in Zadar office)
            municipalities = client.find_municipality(office_id="114")

            # Filter by office and department (66 municipalities)
            municipalities = client.find_municipality(office_id="114", department_id="116")

            # Combine search with filters
            municipalities = client.find_municipality("SAVAR", office_id="114")

        Note:
            - All parameters are optional but at least one should be provided
            - Partial name searches return multiple results (e.g., "LUKA" returns 16 municipalities)
            - office_id corresponds to institutionId from cadastral offices
        """
        endpoint = "/search-cad-parcels/municipalities"
        params: dict[str, str] = {}

        if search_term:
            params["search"] = str(search_term)
        if office_id:
            params["officeId"] = str(office_id)
        if department_id:
            params["departmentId"] = str(department_id)

        def parse(body: Any) -> list[MunicipalitySearchResult]:
            if not body:
                raise CadastralAPIError(
                    error_type=ErrorType.MUNICIPALITY_NOT_FOUND,
                    details={
                        "search_term": search_term,
                        "office_id": office_id,
                        "department_id": department_id,
                    },
                )
            return self._parse_list(MunicipalitySearchResult, body, endpoint)

        municipalities, _ = self._fetch(parse, endpoint, params if params else None)
        return municipalities

    def find_parcel(
        self, parcel_number: str, municipality_reg_num: str
    ) -> list[ParcelSearchResult]:
        """
        Find parcel IDs by parcel number and municipality.

        Args:
            parcel_number: Parcel number (e.g., "103/2", "114"). Building parcels
                may be written as "35/1.ZGR", "35/1 ZGR", "zgr. 35/1" or "*35/1";
                every form is sent as the API spelling "*35/1".
            municipality_reg_num: Municipality registration number (e.g., "334979")

        Returns:
            List of ParcelSearchResult objects

        Raises:
            CadastralAPIError: Any API error occurred

        Note:
            The server matches on the prefix: "114" returns 114, 1140/1, etc.;
            "1072/1" returns 1072/1, 1072/10, 1072/11, ... A leading asterisk acts
            as a wildcard ("*35/1" also returns 135/1).
        """
        endpoint = "/search-cad-parcels/parcel-numbers"
        params = {
            "search": normalize_parcel_number(str(parcel_number)),
            "municipalityRegNum": municipality_reg_num,
        }

        def parse(body: Any) -> list[ParcelSearchResult]:
            if not body:
                raise CadastralAPIError(
                    error_type=ErrorType.PARCEL_NOT_FOUND,
                    details={
                        "parcel_number": parcel_number,
                        "municipality_reg_num": municipality_reg_num,
                    },
                )
            return self._parse_list(ParcelSearchResult, body, endpoint)

        results, _ = self._fetch(parse, endpoint, params)
        return results

    def find_possession_sheet(
        self, sheet_number: str, municipality_reg_num: str
    ) -> list[PossessionSheetSearchResult]:
        """
        Find possession sheets (posjedovni listovi) by sheet number.

        ``GET /search-cad-parcels/possession-sheet-numbers``. The records carry
        the ``possessionSheetId`` that parcel-info ``possessionSheets[]`` use and
        the sheet number; no endpoint returns a sheet by id, so this search is
        all the API offers (open question OQ4 of the coverage specification).

        Args:
            sheet_number: Possession sheet number (prefix match, e.g. "363")
            municipality_reg_num: Municipality registration number (e.g., "334979")

        Returns:
            List of PossessionSheetSearchResult objects (empty when nothing matches)
        """
        endpoint = "/search-cad-parcels/possession-sheet-numbers"
        params = {"search": str(sheet_number), "municipalityRegNum": municipality_reg_num}
        sheets, _ = self._fetch(
            lambda body: self._parse_list(PossessionSheetSearchResult, body or [], endpoint),
            endpoint,
            params,
        )
        return sheets

    def find_main_book(
        self,
        search: str | None = None,
        office_id: str | int | None = None,
        institution_name: str | None = None,
    ) -> list[MainBookSearchResult]:
        """
        Find land-registry main books (glavne knjige) by name, office or institution.

        ``GET /search-lr-parcels/main-books``. This is the link from a
        municipality name to the ``main_book_id`` that ``get_lr_unit_detailed``
        needs: searching "SAVAR" returns main book 21277 of the Zadar court
        (institution 284).

        Args:
            search: Book name to search for (e.g., "SAVAR"); empty returns every book
            office_id: Filter by land-registry office (institution) id, e.g. "284"
            institution_name: Filter by institution name

        Returns:
            List of MainBookSearchResult objects (empty when nothing matches)
        """
        endpoint = "/search-lr-parcels/main-books"
        params = {
            "search": search or "",
            "officeId": "" if office_id is None else str(office_id),
            "institutionName": institution_name or "",
        }
        books, _ = self._fetch(
            lambda body: self._parse_list(MainBookSearchResult, body or [], endpoint),
            endpoint,
            params,
        )
        return books

    def find_book_of_dc(
        self,
        search: str | None = None,
        office_id: str | int | None = None,
        institution_name: str | None = None,
    ) -> list[BookOfDCSearchResult]:
        """
        Find books of deposited contracts (knjige položenih ugovora, KPU).

        ``GET /search-lr-parcels/books-of-dc``. Same parameters as
        :meth:`find_main_book`. Whether a book id can be passed to the lr-unit
        endpoint as ``mainBookId`` is unverified (OQ5), so this returns the
        search records only.

        Args:
            search: Book name to search for (e.g., "ZADAR")
            office_id: Filter by land-registry office id
            institution_name: Filter by institution name

        Returns:
            List of BookOfDCSearchResult objects (empty when nothing matches)
        """
        endpoint = "/search-lr-parcels/books-of-dc"
        params = {
            "search": search or "",
            "officeId": "" if office_id is None else str(office_id),
            "institutionName": institution_name or "",
        }
        books, _ = self._fetch(
            lambda body: self._parse_list(BookOfDCSearchResult, body or [], endpoint),
            endpoint,
            params,
        )
        return books

    def resolve_municipality_reg_num(self, name_or_code: str | int) -> str:
        """Municipality name or registration number -> registration number.

        A string of digits is taken as the number as it is. A name is looked
        up with :meth:`find_municipality`; the municipality whose name matches
        exactly (case-insensitively) is chosen, otherwise the only match.

        Raises:
            CadastralAPIError: ``MUNICIPALITY_NOT_FOUND`` with reason
                ``municipality_not_found`` when nothing matches, or
                ``municipality_ambiguous`` (with the candidates) when several
                municipalities match and none of them exactly.
        """
        text = str(name_or_code).strip()
        if text.isdigit():
            return text
        try:
            results = self.find_municipality(text)
        except CadastralAPIError as e:
            if e.error_type != ErrorType.MUNICIPALITY_NOT_FOUND:
                raise
            # find_municipality reports an empty answer without a reason;
            # callers of the resolver get the same contract for both outcomes.
            raise CadastralAPIError(
                error_type=ErrorType.MUNICIPALITY_NOT_FOUND,
                details={"search_term": text, "reason": "municipality_not_found"},
                cause=e.cause,
            ) from e
        wanted = text.casefold()
        exact = [m for m in results if m.municipality_name.strip().casefold() == wanted]
        if len(exact) == 1:
            return exact[0].municipality_reg_num
        if len(results) == 1:
            return results[0].municipality_reg_num
        raise CadastralAPIError(
            error_type=ErrorType.MUNICIPALITY_NOT_FOUND,
            details={
                "search_term": text,
                "reason": "municipality_ambiguous",
                "candidates": ", ".join(
                    f"{m.municipality_reg_num} {m.municipality_name}" for m in (exact or results)
                ),
            },
        )

    def resolve_municipality_id(self, name_or_code: str | int) -> int:
        """Municipality name or registration number -> internal id (``cadMunicipalityId``).

        The possession-sheet endpoints take the internal id, which the
        municipality search returns as ``key1``; the registration number is
        resolved first (:meth:`resolve_municipality_reg_num`) and its record
        looked up.

        Raises:
            CadastralAPIError: ``MUNICIPALITY_NOT_FOUND`` (see the resolver)
        """
        reg_num = self.resolve_municipality_reg_num(name_or_code)
        results = self.find_municipality(reg_num)
        for municipality in results:
            if municipality.municipality_reg_num == reg_num:
                return municipality.municipality_id
        raise CadastralAPIError(
            error_type=ErrorType.MUNICIPALITY_NOT_FOUND,
            details={"search_term": str(name_or_code), "reason": "municipality_not_found"},
        )

    def resolve_main_book_id(self, main_book_name: str) -> int:
        """
        Resolve a main book name ("SAVAR") to its id through :meth:`find_main_book`.

        Raises:
            CadastralAPIError: ``LR_UNIT_NOT_FOUND`` with reason
                ``main_book_not_found`` when no book matches the name exactly, or
                ``main_book_ambiguous`` (with the candidates) when several do.
        """
        books = self.find_main_book(main_book_name)
        wanted = main_book_name.strip().casefold()
        exact = [b for b in books if b.main_book_name.strip().casefold() == wanted]
        if len(exact) == 1:
            return exact[0].main_book_id
        if not exact:
            raise CadastralAPIError(
                error_type=ErrorType.LR_UNIT_NOT_FOUND,
                details={
                    "main_book_name": main_book_name,
                    "reason": "main_book_not_found",
                    "candidates": ", ".join(b.main_book_name for b in books) or None,
                },
            )
        raise CadastralAPIError(
            error_type=ErrorType.LR_UNIT_NOT_FOUND,
            details={
                "main_book_name": main_book_name,
                "reason": "main_book_ambiguous",
                "candidates": ", ".join(
                    f"{b.main_book_name} ({b.main_book_id}, {b.court_name})" for b in exact
                ),
            },
        )

    def get_parcel_info(self, parcel_id: str | int, *, refresh: bool = False) -> ParcelInfo:
        """
        Get complete parcel information including ownership data.

        Args:
            parcel_id: Parcel ID obtained from search_parcel()
            refresh: Read the record from the server again even if the cache
                holds a copy from the last 30 minutes

        Returns:
            ParcelInfo object with complete parcel details

        Raises:
            CadastralAPIError: Any API error occurred
        """
        endpoint = "/cad/parcel-info"
        params = {"parcelId": str(parcel_id)}

        def parse(body: Any) -> ParcelInfo:
            if not body:
                raise CadastralAPIError(
                    error_type=ErrorType.INVALID_RESPONSE,
                    details={
                        "endpoint": endpoint,
                        "parcel_id": str(parcel_id),
                        "reason": "empty_response",
                    },
                )
            return self._parse(ParcelInfo, body, endpoint, {"parcel_id": str(parcel_id)})

        # A parcel under a large condominium is thousands of possessors that
        # the server assembles on every request: wait for it.
        return self._fetch_record(
            parse, endpoint, params, "cadastre", read_timeout=self.long_timeout, refresh=refresh
        )

    # ------------------------------------------------------------------
    # Possession sheets (posjedovni listovi)
    # ------------------------------------------------------------------

    def get_possession_sheet(
        self, possession_sheet_id: str | int, *, refresh: bool = False
    ) -> PossessionSheet:
        """A possession sheet with its possessors, by the id the searches and parcel records carry.

        ``GET /cad/possession-sheet?possessionSheetId=``: one sheet in the
        shape of parcel-info's ``possessionSheets[]``, possessors included,
        without the sheet's parcels (see :meth:`search_parcels`).
        ``refresh`` reads past a cached copy.

        Raises:
            CadastralAPIError: ``POSSESSION_SHEET_NOT_FOUND`` on an empty answer
        """
        endpoint = "/cad/possession-sheet"
        params = {"possessionSheetId": str(possession_sheet_id)}

        def parse(body: Any) -> PossessionSheet:
            if not body:
                raise CadastralAPIError(
                    error_type=ErrorType.POSSESSION_SHEET_NOT_FOUND,
                    details={
                        "possession_sheet_id": str(possession_sheet_id),
                        "reason": "empty_response",
                    },
                )
            return self._parse(PossessionSheet, body, endpoint, dict(params))

        return self._fetch_record(parse, endpoint, params, "cadastre", refresh=refresh)

    def get_possession_sheet_by_number(
        self, sheet_number: str, cad_municipality_id: str | int, *, refresh: bool = False
    ) -> PossessionSheet:
        """A possession sheet with its possessors, by number and internal municipality id.

        ``GET /cad/possession-sheet-by-number``; the same answer as
        :meth:`get_possession_sheet`. The municipality is the internal
        ``cadMunicipalityId`` (:meth:`resolve_municipality_id`), not the
        registration number. The number is matched exactly. ``refresh``
        reads past a cached copy.

        Raises:
            CadastralAPIError: ``POSSESSION_SHEET_NOT_FOUND`` on an empty answer
        """
        endpoint = "/cad/possession-sheet-by-number"
        params = {
            "possessionSheetNumber": str(sheet_number).strip(),
            "cadMunicipalityId": str(cad_municipality_id),
        }

        def parse(body: Any) -> PossessionSheet:
            if not body:
                raise CadastralAPIError(
                    error_type=ErrorType.POSSESSION_SHEET_NOT_FOUND,
                    details={
                        "sheet_number": str(sheet_number),
                        "cad_municipality_id": str(cad_municipality_id),
                        "reason": "empty_response",
                    },
                )
            return self._parse(PossessionSheet, body, endpoint, dict(params))

        return self._fetch_record(parse, endpoint, params, "cadastre", refresh=refresh)

    def lookup_possession_sheet_number(
        self, possession_sheet_id: str | int
    ) -> PossessionSheetSearchData:
        """A sheet id -> its number and municipality registration number.

        ``GET /cad/cad-parcels-search-data?possessionSheetId=``.

        Raises:
            CadastralAPIError: ``POSSESSION_SHEET_NOT_FOUND`` on an empty answer
        """
        endpoint = "/cad/cad-parcels-search-data"
        params = {"possessionSheetId": str(possession_sheet_id)}

        def parse(body: Any) -> PossessionSheetSearchData:
            if not body:
                raise CadastralAPIError(
                    error_type=ErrorType.POSSESSION_SHEET_NOT_FOUND,
                    details={
                        "possession_sheet_id": str(possession_sheet_id),
                        "reason": "empty_response",
                    },
                )
            return self._parse(PossessionSheetSearchData, body, endpoint, dict(params))

        data, _ = self._fetch(parse, endpoint, params)
        return data

    #: Records ``search_parcels`` has been seen to return at most; a longer sheet
    #: has not been observed, so a cap at this size is not ruled out.
    SEARCH_PARCELS_OBSERVED_MAX = 30

    def search_parcels(
        self,
        *,
        cad_municipality_id: str | int | None = None,
        possession_sheet_number: str | None = None,
        parcel_number: str | None = None,
        parcel_id: str | int | None = None,
    ) -> list[SearchedParcel]:
        """The parcel search behind the web form: by possession sheet, exact number or id.

        ``POST /cad/search-parcels`` with the four keys the form always sends
        (empty strings for the unused ones). Returns full parcel records
        (:class:`SearchedParcel`), one per parcel, sorted by number:

        - ``cad_municipality_id`` + ``possession_sheet_number``: every parcel
          on the sheet (the one thing no other endpoint offers);
        - ``cad_municipality_id`` + ``parcel_number``: that parcel, matched
          exactly (no prefix search, unlike :meth:`find_parcel`);
        - ``parcel_id`` alone: that parcel.

        An empty list means nothing matched; the server answers a bad query
        the same way. No paging parameter is honoured; the longest sheet seen
        returned ``SEARCH_PARCELS_OBSERVED_MAX`` records, so a cap at that
        size is possible and a caller should say so when it gets exactly
        that many.
        """
        if not (parcel_id or (cad_municipality_id and (possession_sheet_number or parcel_number))):
            raise ValueError(
                "search_parcels needs parcel_id, or cad_municipality_id with "
                "possession_sheet_number or parcel_number"
            )
        endpoint = "/cad/search-parcels"
        body = {
            "parcelId": str(parcel_id) if parcel_id else "",
            "cadMunicipalityId": str(cad_municipality_id) if cad_municipality_id else "",
            "parcelNumber": normalize_parcel_number(parcel_number) if parcel_number else "",
            "possessionSheetNumber": str(possession_sheet_number).strip()
            if possession_sheet_number
            else "",
        }
        def parse(data: Any) -> list[SearchedParcel]:
            return self._parse_list(SearchedParcel, data, endpoint, body) if data else []

        records, fetched = self._fetch(parse, endpoint, json_body=body)
        if not records:
            return []
        provenance = self._provenance("cadastre", endpoint, fetched_at=fetched.fetched_at)
        for record in records:
            if record.possession_sheet is not None:
                record.possession_sheet.provenance = provenance
        return records

    def get_possession_sheet_parcels(
        self, sheet_number: str, municipality: str | int, *, refresh: bool = False
    ) -> "PossessionSheetParcels":
        """A possession sheet by number in a municipality, with every parcel on it.

        Resolves the municipality (name or registration number) to its
        internal id, reads the sheet (:meth:`get_possession_sheet_by_number`)
        and its parcels (:meth:`search_parcels`): three requests. ``refresh``
        reads the sheet past a cached copy; the other two may be cached.

        Raises:
            CadastralAPIError: ``MUNICIPALITY_NOT_FOUND``,
                ``POSSESSION_SHEET_NOT_FOUND``
        """
        municipality_id = self.resolve_municipality_id(municipality)
        sheet = self.get_possession_sheet_by_number(
            sheet_number, municipality_id, refresh=refresh
        )
        parcels = self.search_parcels(
            cad_municipality_id=municipality_id, possession_sheet_number=sheet_number
        )
        return PossessionSheetParcels(
            sheet=sheet,
            parcels=parcels,
            parcels_provenance=self._provenance("cadastre", "/cad/search-parcels"),
            maybe_truncated=len(parcels) >= self.SEARCH_PARCELS_OBSERVED_MAX,
            backfilled_from_parcels=tuple(_backfill_sheet(sheet, parcels)),
        )

    def get_parcel_by_number(
        self,
        parcel_number: str,
        municipality_reg_num: str,
        exact_match: bool = True,
        *,
        refresh: bool = False,
    ) -> ParcelInfo | None:
        """
        Convenience method to find and retrieve parcel info in one call.

        Args:
            parcel_number: Parcel number (e.g., "103/2"); building parcels in any
                spelling ("35/1.ZGR", "zgr. 35/1", "*35/1")
            municipality_reg_num: Municipality registration number
            exact_match: If True, only return exact parcel number match
            refresh: Read the parcel record from the server again (the
                number search may still come from the cache)

        Returns:
            ParcelInfo object if found, None otherwise

        Raises:
            CadastralAPIError: Any API error occurred; ``PARCEL_NOT_FOUND`` with
                reason ``only_building_parcel_exists`` when the caller asked for
                a land parcel ("35/1") and only the building parcel ("*35/1")
                exists, so the two are never confused.
        """
        wanted = normalize_parcel_number(parcel_number)
        search_results = self.find_parcel(wanted, municipality_reg_num)

        if not search_results:
            return None

        # Find exact match if requested
        if exact_match:
            for result in search_results:
                if result.parcel_number == wanted:
                    return self.get_parcel_info(result.parcel_id, refresh=refresh)
            candidates = [r.parcel_number for r in search_results]
            if not is_building_parcel_number(wanted) and f"*{wanted}" in candidates:
                raise CadastralAPIError(
                    error_type=ErrorType.PARCEL_NOT_FOUND,
                    details={
                        "parcel_number": parcel_number,
                        "municipality_reg_num": municipality_reg_num,
                        "reason": "only_building_parcel_exists",
                        "candidates": ", ".join(candidates),
                    },
                )
            return None

        # Return first result
        return self.get_parcel_info(search_results[0].parcel_id, refresh=refresh)

    def get_parcel_geometry(
        self, parcel_number: str, municipality_reg_num: str
    ) -> ParcelGeometry | None:
        """
        Get parcel geometry (boundary coordinates) from GIS data.

        Downloads municipality GIS data (if not cached), extracts GML file,
        and returns parcel geometry with boundary coordinates.

        Args:
            parcel_number: Parcel number (e.g., "103/2", "114")
            municipality_reg_num: Municipality registration number (e.g., "334979")

        Returns:
            ParcelGeometry object with coordinates, or None if not found

        Example:
            geometry = client.get_parcel_geometry("103/2", "334979")
            if geometry:
                print(f"Parcel: {geometry.broj_cestice}")
                print(f"Area: {geometry.povrsina_graficka} m²")
                print(f"Vertices: {geometry.coordinate_count}")
                print(f"Bounds: {geometry.bounds}")

                # Export to WKT
                wkt = geometry.to_wkt()

                # Get coordinates for mapping
                coords = geometry.to_geojson_coords()

        Note:
            - First call downloads and caches municipality GIS data (~200KB-several MB)
            - Subsequent calls use cached data (fast)
            - Coordinates are in EPSG:3765 (HTRS96/TM) projection
            - Use gis_cache.clear_municipality() to clear cache for a municipality
        """
        # Download and cache GIS data
        gml_path = self.gis_cache.get_parcel_data(municipality_reg_num, auto_download=True)
        return self._gml_parser(gml_path).get_parcel_by_number(parcel_number)

    def _gml_parser(self, gml_path: Path) -> GMLParser:
        """The parser of a municipality's GML file, parsed once per client.

        A list of parcels in one municipality then costs one parse of the
        file instead of one per parcel; a file downloaded again (new mtime)
        gets a new parser.
        """
        mtime = gml_path.stat().st_mtime_ns
        with self._gis_lock:
            cached = self._gml_parsers.get(gml_path)
            if cached is None or cached[0] != mtime:
                cached = self._gml_parsers[gml_path] = (mtime, GMLParser(gml_path))
        return cached[1]

    def get_parcel_index(self, municipality_reg_num: str) -> ParcelIndex:
        """The spatial index of a municipality's parcels, built once per client.

        Downloads and caches the municipality's GIS data if needed (like
        ``get_parcel_geometry``), then loads every parcel outline into a
        ``ParcelIndex`` for area, radius and neighbour queries. The index is
        kept per GML file and rebuilt when the file changes (a new download).

        Example:
            index = client.get_parcel_index("334979")
            inside = index.in_polygon([(x1, y1), (x2, y2), (x3, y3)])
            around = index.neighbours("103/2")
        """
        gml_path = self.gis_cache.get_parcel_data(municipality_reg_num, auto_download=True)
        mtime = gml_path.stat().st_mtime_ns
        parser = self._gml_parser(gml_path)
        with self._gis_lock:
            cached = self._parcel_indexes.get(gml_path)
            if cached is None or cached[0] != mtime:
                index = ParcelIndex(parser.get_all_parcels())
                cached = self._parcel_indexes[gml_path] = (mtime, index)
        return cached[1]

    def get_parcel_zoning(
        self,
        parcel_number: str,
        municipality_reg_num: str,
        min_overlap: float = 0.02,
    ) -> ParcelZoning | None:
        """
        Screening of a parcel against the spatial plans' building areas.

        Takes the parcel outline from the cadastral GIS data (downloaded and
        cached as for ``get_parcel_geometry``), asks the building-areas WFS for
        every zone that intersects it, and estimates how much of the parcel
        each zone covers. It says where the parcel lies with respect to the
        building areas, not whether anything may be built there
        (``buildability`` is always ``"unknown"``).

        Args:
            parcel_number: Parcel number (e.g., "103/2"); any spelling of a
                building parcel is accepted
            municipality_reg_num: Municipality registration number (e.g., "334979")
            min_overlap: Zones covering a smaller share of the parcel are
                listed under ``below_threshold`` instead of ``matches``
                (default 0.02, i.e. 2 %); must be between 0 and 1

        Returns:
            ParcelZoning (status, matches with overlap, below-threshold zones,
            plans, dataset and disclaimer), or None when the parcel has no
            geometry

        Raises:
            ValueError: ``min_overlap`` is not a finite number between 0 and 1

        Example:
            zoning = client.get_parcel_zoning("103/2", "334979")
            if zoning:
                print(zoning.status)  # inside_settlement, detached_zone,
                                      # touches_below_threshold or outside
                for match in zoning.matches:
                    print(match.zone.label(), f"{match.overlap_fraction:.0%}")
                print(zoning.dataset.disclaimer)

        Note:
            The building areas are an interpretation of the plans by the county
            institutes, not the plans themselves (see ``dataset.disclaimer``);
            the generation field of every zone says which code list its
            designation code belongs to.
        """
        # Reject a bad threshold before any download or request is made.
        min_overlap = validate_min_overlap(min_overlap)
        geometry = self.get_parcel_geometry(
            normalize_parcel_number(parcel_number), municipality_reg_num
        )
        if geometry is None:
            return None
        return self.planning.zoning_for_geometry(geometry, min_overlap=min_overlap)

    def get_lr_unit_detailed(
        self,
        lr_unit_number: str,
        main_book_id: int | None = None,
        historical_overview: bool = False,
        *,
        main_book_name: str | None = None,
        refresh: bool = False,
    ) -> LandRegistryUnitDetailed:
        """
        Get detailed land registry unit information including all sheets (A, B, C).

        This method retrieves complete information about a land registry unit
        (zemljišnoknjižni uložak), including:
        - Sheet A: List of all cadastral parcels in the unit
        - Sheet B: Ownership information with co-owners and shares
        - Sheet C: Encumbrances (mortgages, liens, easements, etc.)

        Args:
            lr_unit_number: Land registry unit number (e.g., "769")
            main_book_id: Main book ID (e.g., 21277 for SAVAR). May be omitted
                when ``main_book_name`` is given.
            historical_overview: Include historical data (default: False)
            main_book_name: Main book name (e.g., "SAVAR"), resolved to its id
                through the main-book search (:meth:`resolve_main_book_id`)
                when ``main_book_id`` is not given.
            refresh: Read the unit from the server again even if the cache
                holds a copy from the last 30 minutes.

        Returns:
            LandRegistryUnitDetailed object with complete unit information

        Raises:
            CadastralAPIError: Any API error occurred; ``LR_UNIT_NOT_FOUND`` with
                reason ``main_book_ambiguous`` when the name matches several books.
            ValueError: Neither ``main_book_id`` nor ``main_book_name`` was given.

        Example:
            # Get LR unit details
            lr_unit = client.get_lr_unit_detailed("769", 21277)
            lr_unit = client.get_lr_unit_detailed("769", main_book_name="SAVAR")

            # Access ownership information
            owners = lr_unit.get_all_owners()
            for owner in owners:
                print(f"Owner: {owner.name}, OIB: {owner.tax_number}")

            # Check for encumbrances
            if lr_unit.has_sheet_c_entries():
                print("Unit has encumbrances (mortgages, liens, etc.)")

            # Get summary
            summary = lr_unit.summary()
            print(f"Total parcels: {summary['total_parcels']}")
            print(f"Total area: {summary['total_area_m2']} m²")

        Note:
            ⚠️ Demo project: verify your rights before using any server other than the mock.
            The API response is returned as a list with typically one element.
        """
        if main_book_id is None:
            if not main_book_name:
                raise ValueError("get_lr_unit_detailed needs main_book_id or main_book_name")
            main_book_id = self.resolve_main_book_id(main_book_name)

        endpoint = "/lr/lr-unit"
        params = {
            "lrUnitNumber": str(lr_unit_number),
            "mainBookId": str(main_book_id),
            "historicalOverview": str(historical_overview).lower(),
        }

        def parse(body: Any) -> LandRegistryUnitDetailed:
            if not body:
                raise CadastralAPIError(
                    error_type=ErrorType.LR_UNIT_NOT_FOUND,
                    details={
                        "lr_unit_number": lr_unit_number,
                        "main_book_id": main_book_id,
                        "reason": "empty_response",
                    },
                )
            # API returns a list, typically with one element (an empty list
            # was rejected above as an empty response)
            if isinstance(body, list):
                body = body[0]
            return self._parse(
                LandRegistryUnitDetailed,
                body,
                endpoint,
                {"lr_unit_number": lr_unit_number, "main_book_id": main_book_id},
            )

        # A unit of thousands of shares takes the server 20 s or more to
        # assemble (unpaged, uncached upstream): wait for it.
        return self._fetch_record(
            parse,
            endpoint,
            params,
            "land_registry",
            read_timeout=self.long_timeout,
            refresh=refresh,
        )

    def get_lr_unit_from_parcel(
        self,
        parcel_number: str,
        municipality: str | int,
        historical_overview: bool = False,
        *,
        refresh: bool = False,
    ) -> LandRegistryUnitDetailed:
        """
        Convenience method to get LR unit details by first looking up parcel.

        This method performs a two-step process:
        1. Searches for the parcel to get its lr_unit information
        2. Retrieves detailed LR unit information using the found unit number and main book ID

        Args:
            parcel_number: Parcel number (e.g., "103/2", "279/6")
            municipality: Municipality name (e.g., "SAVAR") or registration number (e.g., "334979")
            historical_overview: Include historical data (default: False)
            refresh: Read the parcel record and the unit from the server
                again; the municipality and parcel-number lookups may still
                come from the cache

        Returns:
            LandRegistryUnitDetailed object with complete unit information

        Raises:
            CadastralAPIError: Any API error occurred (parcel not found, LR unit not found, etc.)

        Example:
            # Get LR unit details for a specific parcel
            lr_unit = client.get_lr_unit_from_parcel("279/6", "SAVAR")

            # See all parcels in the same LR unit
            all_parcels = lr_unit.get_all_parcels()
            for parcel in all_parcels:
                print(f"Parcel: {parcel.parcel_number}, Area: {parcel.area_numeric} m²")

            # Get all co-owners
            owners = lr_unit.get_all_owners()
            print(f"Number of co-owners: {len(owners)}")

        Note:
            ⚠️ Demo project: verify your rights before using any server other than the mock.
            This is a convenience wrapper that combines parcel lookup with LR unit retrieval.
        """
        parcel_number = normalize_parcel_number(parcel_number)
        municipality = str(municipality)
        municipality_reg_num = self.resolve_municipality_reg_num(municipality)

        # Get parcel info to extract LR unit details
        parcel_info = self.get_parcel_by_number(
            parcel_number, municipality_reg_num, refresh=refresh
        )

        if not parcel_info:
            raise CadastralAPIError(
                error_type=ErrorType.PARCEL_NOT_FOUND,
                details={
                    "parcel_number": parcel_number,
                    "municipality": municipality,
                },
            )

        # Resolve the LR unit reference, falling back to parcel links when the
        # parcel has no direct lr_unit (a common case - the unit is still
        # reachable via lr_units_from_parcel_links / parcel_links).
        ref = self._resolve_lr_unit_ref(parcel_info)
        if ref is None:
            # Building parcels never carry a land-registry reference: the
            # building is registered on its land parcel.
            raise CadastralAPIError(
                error_type=ErrorType.LR_UNIT_NOT_FOUND,
                details={
                    "parcel_number": parcel_number,
                    "municipality": municipality,
                    "reason": "parcel_not_in_land_registry",
                    "is_building_parcel": parcel_info.is_building_parcel or None,
                },
            )
        lr_unit_number, main_book_id = ref
        derived_from_links = parcel_info.lr_unit is None

        # Get detailed LR unit information
        lr_unit = self.get_lr_unit_detailed(
            lr_unit_number=lr_unit_number,
            main_book_id=main_book_id,
            historical_overview=historical_overview,
            refresh=refresh,
        )
        lr_unit.lr_unit_derived_from_links = derived_from_links
        lr_unit.cadastre_harmonized = parcel_info.is_harmonized
        return lr_unit

    @staticmethod
    def _resolve_lr_unit_ref(parcel_info: ParcelInfo) -> tuple[str, int] | None:
        """Resolve an (lr_unit_number, main_book_id) reference from a parcel.

        Prefers the direct ``lr_unit``; otherwise falls back to the units
        carried by parcel links. Returns None when the parcel is not in the
        land registry at all, and raises ``LR_UNIT_NOT_FOUND`` with reason
        ``lr_unit_ambiguous`` when the links name different units.
        """
        unit = parcel_info.resolved_lr_unit()
        if unit is None:
            return None
        if parcel_info.lr_unit is None:
            # Without a direct unit, links that disagree must not be resolved
            # by taking the first one.
            refs = {(c.lr_unit_number, c.main_book_id) for c in parcel_info.lr_unit_candidates()}
            if len(refs) > 1:
                raise CadastralAPIError(
                    error_type=ErrorType.LR_UNIT_NOT_FOUND,
                    details={
                        "parcel_number": parcel_info.parcel_number,
                        "reason": "lr_unit_ambiguous",
                        "candidates": ", ".join(f"{n}/{b}" for n, b in sorted(refs)),
                    },
                )
        return unit.lr_unit_number, unit.main_book_id

    def get_file_status(
        self, file_number: str, institution_id: int
    ) -> FileStatus | None:
        """Get the processing status (detail) of a single land-registry file.

        A unit's ``activePlumbs`` only carry the bare file number (e.g.
        ``"Z-12564/2026"``). This resolves that number to its full status -
        what the request is, its processing stage, and key dates - via
        ``POST /lr/file-status``.

        The endpoint wants the number split into parts plus the owning
        institution; the institution comes from the unit
        (``lr_unit.institution_id``). Without it the endpoint returns an empty
        body, which is treated as "no detail available" (``None``).

        Args:
            file_number: Rendered file number, e.g. ``"Z-12564/2026"``.
            institution_id: Owning land-registry office ID (e.g. 284 for Zadar).

        Returns:
            A :class:`FileStatus`, or ``None`` when the number cannot be parsed
            or the endpoint has no record for it.

        Raises:
            CadastralAPIError: A transport/server error occurred.

        Note:
            ⚠️ Demo project: verify your rights before using any server other than the mock.
        """
        parts = parse_file_number(file_number)
        if parts is None:
            return None
        code, order_number, year = parts

        def parse(body: Any) -> FileStatus | None:
            # The endpoint answers an unknown file with an empty object, not a 404.
            if not body:
                return None
            return self._parse(FileStatus, body, "/lr/file-status", {"file_number": file_number})

        status, _ = self._fetch(
            parse,
            "/lr/file-status",
            json_body={
                "lrFileCode": code,
                "lrFileOrderNumber": order_number,
                "lrFileYear": year,
                "institutionId": institution_id,
            },
        )
        return status

    def get_plombe_details(
        self, lr_unit: LandRegistryUnitDetailed
    ) -> dict[str, FileStatus]:
        """Resolve detail for each pending plomba on a land-registry unit.

        Iterates the unit's ``active_plumbs`` and fetches each one's status,
        using the unit's own ``institution_id``. Cadastre plombe
        (``cad_plumb=True``) are skipped - ``/lr/file-status`` is a
        land-registry endpoint and does not resolve them. Plombe with no
        retrievable record are likewise omitted.

        Each extra plomba costs one rate-limited request, so this is opt-in at
        the call sites (CLI ``--plombe-detail`` / MCP ``include_plombe_detail``).

        Args:
            lr_unit: The unit whose pending plombe should be detailed.

        Returns:
            Mapping of ``file_number`` -> :class:`FileStatus` for the
            land-registry plombe that resolved. Consumers iterate
            ``lr_unit.active_plumbs`` and look up by ``file_number`` so that
            skipped/unresolved plombe remain visible as "detail unavailable".
        """
        details: dict[str, FileStatus] = {}
        for plumb in lr_unit.active_plumbs:
            if plumb.cad_plumb:
                continue
            status = self.get_file_status(plumb.file_number, lr_unit.institution_id)
            if status is not None:
                details[plumb.file_number] = status
        return details


def _unknown_field_paths(instance: BaseModel, prefix: str) -> set[str]:
    """Key paths (``endpoint.field.subfield[].key``) of every undeclared server key."""
    paths: set[str] = set()
    extra = getattr(instance, "source_fields", None)
    if extra is None:
        extra = dict(instance.model_extra or {})
    for key in extra:
        paths.add(f"{prefix}.{key}")
    for name in type(instance).model_fields:
        value = getattr(instance, name, None)
        if isinstance(value, BaseModel):
            paths |= _unknown_field_paths(value, f"{prefix}.{name}")
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, BaseModel):
                    paths |= _unknown_field_paths(item, f"{prefix}.{name}[]")
    return paths
