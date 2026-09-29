"""Client for the building-areas WFS (građevinska područja) with mirror rotation.

The Ministry publishes the layer on four GeoServer mirrors behind a proxy that
answers ``502 Proxy Error`` for minutes at a time on any one of them, so the
client takes a list of base URLs and moves to the next one on a gateway error,
a connection error or a timeout. The default is the mock server's imitation
of the service, ``<CADASTRAL_API_BASE_URL>/planning/wfs``; set
``CADASTRAL_PLANNING_WFS_URLS`` (comma-separated) to use other servers, after
verifying that you have the right to (see docs/legal.md).

Endpoint details: specs/spatial-planning-api-specification.md, section 3.
"""

from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from ..exceptions import CadastralAPIError, ErrorType
from ..gis.geometry_ops import overlap_fraction, ring_area, sample_points
from ..models.gis_entities import ParcelGeometry
from ..models.planning_entities import (
    DETACHED_FEATURE_TYPE,
    SETTLEMENT_FEATURE_TYPE,
    ParcelZoning,
    PlanningDataset,
    PlanningZone,
    ZoneKind,
    ZoneMatch,
    ZoningStatus,
)
from ..rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

#: Path under the API base URL where the mock server imitates the WFS.
DEFAULT_WFS_PATH = "/planning/wfs"
#: Name of the layer as the Ministry's geoportal labels it.
DATASET_NAME = "Građevinska područja (MPGI)"
#: The service publishes no machine-readable date; the catalogues disagree.
DATASET_STATE_NOTE = (
    "No machine-readable date is published. The ISPU geoportal labels the layer "
    "'rujan 2024'; the NIPP service record says plans in force in September 2016 and the "
    "NIPP dataset record September 2020."
)
#: HTTP statuses that mean "this mirror is down, try the next one".
GATEWAY_STATUSES = frozenset({502, 503, 504})

FEATURE_TYPES: dict[ZoneKind, str] = {
    ZoneKind.SETTLEMENT: SETTLEMENT_FEATURE_TYPE,
    ZoneKind.DETACHED: DETACHED_FEATURE_TYPE,
}


def _cql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def validate_min_overlap(min_overlap: float) -> float:
    """Check a threshold share before any work is done with it.

    Raises:
        ValueError: not a finite number between 0 and 1
    """
    if isinstance(min_overlap, bool) or not isinstance(min_overlap, (int, float)):
        raise ValueError(f"min_overlap must be a number between 0 and 1, got {min_overlap!r}")
    if not math.isfinite(min_overlap):
        raise ValueError(
            f"min_overlap must be a finite number between 0 and 1, got {min_overlap!r}"
        )
    if not 0.0 <= min_overlap <= 1.0:
        raise ValueError(f"min_overlap must be between 0 and 1, got {min_overlap!r}")
    return float(min_overlap)


@dataclass(frozen=True)
class FetchProvenance:
    """Which endpoint answered one request, and when (ISO 8601, UTC)."""

    url: str
    retrieved_at: str


class PlanningWFSClient:
    """Read zones from the building-areas WFS (GeoServer, WFS 2.0, GeoJSON output)."""

    DEFAULT_TIMEOUT = float(os.getenv("CADASTRAL_API_TIMEOUT", "10.0"))
    DEFAULT_RATE_LIMIT = float(os.getenv("CADASTRAL_API_RATE_LIMIT", "0.375"))

    def __init__(
        self,
        base_urls: list[str] | str | None = None,
        timeout: float | None = None,
        rate_limit: float | None = None,
        api_base_url: str | None = None,
    ) -> None:
        """
        Args:
            base_urls: WFS endpoint(s). A list, a comma-separated string, or
                None for ``CADASTRAL_PLANNING_WFS_URLS`` and, failing that,
                ``<api_base_url>/planning/wfs`` (the mock server).
            timeout: Request timeout in seconds (``CADASTRAL_API_TIMEOUT``).
            rate_limit: Minimum seconds between requests (``CADASTRAL_API_RATE_LIMIT``).
            api_base_url: API base URL the default endpoint is derived from.
        """
        self.base_urls = self._resolve_urls(base_urls, api_base_url)
        self.timeout = timeout if timeout is not None else self.DEFAULT_TIMEOUT
        self.rate_limit = rate_limit if rate_limit is not None else self.DEFAULT_RATE_LIMIT
        self._limiter = RateLimiter(self.rate_limit)
        self.client = httpx.Client(
            headers={"Accept": "application/json, */*"},
            timeout=self.timeout,
            follow_redirects=True,
        )

    @staticmethod
    def _resolve_urls(base_urls: list[str] | str | None, api_base_url: str | None) -> list[str]:
        if base_urls is None:
            base_urls = os.getenv("CADASTRAL_PLANNING_WFS_URLS") or None
        if base_urls is None:
            api = (api_base_url or os.getenv("CADASTRAL_API_BASE_URL") or "http://localhost:8000")
            return [api.rstrip("/") + DEFAULT_WFS_PATH]
        if isinstance(base_urls, str):
            base_urls = [part.strip() for part in base_urls.split(",")]
        urls = [url.rstrip("/") for url in base_urls if url and url.strip()]
        if not urls:
            raise ValueError("at least one WFS base URL is required")
        return urls

    def __enter__(self) -> PlanningWFSClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    def _wait_for_rate_limit(self) -> None:
        """One request per ``rate_limit`` across every thread using this client."""
        self._limiter.wait()

    def _get(self, params: dict[str, str]) -> tuple[httpx.Response, FetchProvenance]:
        """GET the same request from each mirror in turn until one answers.

        Returns the response and the provenance of that one response; nothing
        is remembered on the client, so concurrent callers cannot see each
        other's mirrors or timestamps.
        """
        failures: list[str] = []
        for url in self.base_urls:
            self._wait_for_rate_limit()
            try:
                response = self.client.get(url, params=params)
            except httpx.TimeoutException as exc:
                failures.append(f"{url}: timeout")
                logger.warning("planning WFS mirror timed out: %s (%s)", url, exc)
                continue
            except httpx.HTTPError as exc:
                failures.append(f"{url}: {type(exc).__name__}")
                logger.warning("planning WFS mirror unreachable: %s (%s)", url, exc)
                continue
            if response.status_code in GATEWAY_STATUSES:
                failures.append(f"{url}: HTTP {response.status_code}")
                logger.warning("planning WFS mirror returned %s: %s", response.status_code, url)
                continue
            if response.status_code == 400:
                raise CadastralAPIError(
                    error_type=ErrorType.INVALID_RESPONSE,
                    details={
                        "endpoint": url,
                        "reason": "wfs_exception",
                        "text": response.text[:500],
                    },
                )
            if response.status_code >= 500:
                raise CadastralAPIError(
                    error_type=ErrorType.SERVER_ERROR,
                    details={"endpoint": url, "status_code": response.status_code},
                )
            if response.status_code >= 400:
                raise CadastralAPIError(
                    error_type=ErrorType.CONNECTION,
                    details={"endpoint": url, "status_code": response.status_code},
                )
            retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            return response, FetchProvenance(url=url, retrieved_at=retrieved_at)
        raise CadastralAPIError(
            error_type=ErrorType.CONNECTION,
            details={"reason": "all_mirrors_failed", "mirrors": "; ".join(failures)},
        )

    def get_feature(
        self,
        type_name: str,
        *,
        cql_filter: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        count: int | None = None,
        start_index: int | None = None,
        property_names: list[str] | None = None,
        srs_name: str | None = None,
    ) -> dict[str, Any]:
        """Raw WFS 2.0 GetFeature as a GeoJSON FeatureCollection dictionary."""
        document, _ = self.get_feature_with_provenance(
            type_name,
            cql_filter=cql_filter,
            bbox=bbox,
            count=count,
            start_index=start_index,
            property_names=property_names,
            srs_name=srs_name,
        )
        return document

    def get_feature_with_provenance(
        self,
        type_name: str,
        *,
        cql_filter: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        count: int | None = None,
        start_index: int | None = None,
        property_names: list[str] | None = None,
        srs_name: str | None = None,
    ) -> tuple[dict[str, Any], FetchProvenance]:
        """GetFeature plus the endpoint and time of the response it came from."""
        params: dict[str, str] = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": type_name,
            "outputFormat": "application/json",
        }
        if cql_filter:
            params["cql_filter"] = cql_filter
        if bbox is not None:
            params["bbox"] = ",".join(f"{v}" for v in bbox) + ",EPSG:3765"
        if count is not None:
            params["count"] = str(count)
        if start_index is not None:
            params["startIndex"] = str(start_index)
        if property_names:
            params["propertyName"] = ",".join(property_names)
        if srs_name:
            params["srsName"] = srs_name
        response, provenance = self._get(params)
        try:
            document = response.json()
        except ValueError as exc:
            raise CadastralAPIError(
                error_type=ErrorType.INVALID_RESPONSE,
                details={"endpoint": str(response.url), "reason": "not_json"},
                cause=exc,
            ) from exc
        if not isinstance(document, dict) or "features" not in document:
            raise CadastralAPIError(
                error_type=ErrorType.INVALID_RESPONSE,
                details={"endpoint": str(response.url), "reason": "not_a_feature_collection"},
            )
        return document, provenance

    # ------------------------------------------------------------------
    # Zones
    # ------------------------------------------------------------------

    def _zones(self, kind: ZoneKind, document: dict[str, Any]) -> list[PlanningZone]:
        return [PlanningZone.from_feature(f, kind) for f in document.get("features") or []]

    def zones_intersecting(
        self, wkt: str, kinds: list[ZoneKind] | None = None
    ) -> list[PlanningZone]:
        """Zones whose geometry intersects a WKT polygon in EPSG:3765."""
        zones, _ = self.zones_intersecting_with_provenance(wkt, kinds)
        return zones

    def zones_intersecting_with_provenance(
        self, wkt: str, kinds: list[ZoneKind] | None = None
    ) -> tuple[list[PlanningZone], list[FetchProvenance]]:
        """Intersecting zones plus the provenance of every request made."""
        zones: list[PlanningZone] = []
        provenance: list[FetchProvenance] = []
        for kind in kinds or list(ZoneKind):
            document, fetched = self.get_feature_with_provenance(
                FEATURE_TYPES[kind], cql_filter=f"INTERSECTS(geom, {wkt})"
            )
            zones.extend(self._zones(kind, document))
            provenance.append(fetched)
        return zones, provenance

    def zones_in_bbox(
        self, bbox: tuple[float, float, float, float], kinds: list[ZoneKind] | None = None
    ) -> list[PlanningZone]:
        """Zones whose geometry intersects a bounding box in EPSG:3765."""
        zones: list[PlanningZone] = []
        for kind in kinds or list(ZoneKind):
            zones.extend(self._zones(kind, self.get_feature(FEATURE_TYPES[kind], bbox=bbox)))
        return zones

    def find_zones(
        self,
        *,
        municipality_code: str | None = None,
        designation_code: str | None = None,
        kind: ZoneKind = ZoneKind.DETACHED,
        count: int = 100,
        start_index: int = 0,
    ) -> list[PlanningZone]:
        """Zones by attribute: JLS code (``jls_mb``) and/or designation code (``ozn_namjen``)."""
        clauses = []
        if municipality_code:
            clauses.append(f"jls_mb={_cql_literal(municipality_code)}")
        if designation_code:
            clauses.append(f"ozn_namjen={_cql_literal(designation_code)}")
        document = self.get_feature(
            FEATURE_TYPES[kind],
            cql_filter=" AND ".join(clauses) or None,
            count=count,
            start_index=start_index,
        )
        return self._zones(kind, document)

    def dataset(self, provenance: list[FetchProvenance] | None = None) -> PlanningDataset:
        """Provenance record built from the responses one operation used.

        ``source_url`` names the mirror that answered; when the responses of
        one operation came from different mirrors they are joined with "; ".
        ``retrieved_at`` is the time of the latest response. Without
        provenance (nothing fetched yet) the configured first mirror is named
        and ``retrieved_at`` is None.
        """
        if not provenance:
            return PlanningDataset(
                name=DATASET_NAME,
                state=None,
                state_note=DATASET_STATE_NOTE,
                source_url=self.base_urls[0],
                retrieved_at=None,
            )
        urls: list[str] = []
        for fetched in provenance:
            if fetched.url not in urls:
                urls.append(fetched.url)
        return PlanningDataset(
            name=DATASET_NAME,
            state=None,
            state_note=DATASET_STATE_NOTE,
            source_url="; ".join(urls),
            retrieved_at=max(fetched.retrieved_at for fetched in provenance),
        )

    def zoning_for_geometry(
        self, geometry: ParcelGeometry, min_overlap: float = 0.02, grid: int = 40
    ) -> ParcelZoning:
        """Match a parcel outline against the building areas.

        ``min_overlap`` is validated before any request is sent.
        """
        min_overlap = validate_min_overlap(min_overlap)
        zones, provenance = self.zones_intersecting_with_provenance(geometry.to_wkt())
        return match_parcel(
            geometry, zones, self.dataset(provenance), min_overlap=min_overlap, grid=grid
        )


def match_parcel(
    geometry: ParcelGeometry,
    zones: list[PlanningZone],
    dataset: PlanningDataset,
    min_overlap: float = 0.02,
    grid: int = 40,
) -> ParcelZoning:
    """Compute overlap fractions and the status of a parcel against candidate zones.

    ``zones`` are the zones the service reported as intersecting the parcel.
    Those covering less than ``min_overlap`` of it (or none of its interior)
    go to ``below_threshold`` instead of ``matches``, because plan boundaries
    are drawn at 1:5000 and rarely coincide with parcel lines; they are kept
    so that a boundary case is never reported as ``outside``. Matches are
    sorted by overlap, largest first; the status follows the largest match.

    Raises:
        ValueError: ``min_overlap`` is not a finite number between 0 and 1
    """
    min_overlap = validate_min_overlap(min_overlap)
    ring = [(c.x, c.y) for c in geometry.coordinates]
    samples = sample_points(ring, grid)
    parcel_area = geometry.povrsina_graficka or ring_area(ring)
    matches: list[ZoneMatch] = []
    below: list[ZoneMatch] = []
    for zone in zones:
        fraction = overlap_fraction(ring, zone.rings, grid, samples=samples)
        match = ZoneMatch(
            zone=zone,
            overlap_fraction=round(fraction, 3),
            overlap_m2=round(fraction * parcel_area, 1) if parcel_area else None,
        )
        # A zone counts only when it covers some of the parcel's interior and
        # at least the threshold share; a boundary-only contact never counts.
        if fraction > 0.0 and fraction >= min_overlap:
            matches.append(match)
        else:
            below.append(match)
    matches.sort(key=lambda m: m.overlap_fraction, reverse=True)
    below.sort(key=lambda m: m.overlap_fraction, reverse=True)
    if matches:
        if matches[0].zone.zone_kind is ZoneKind.SETTLEMENT:
            status = ZoningStatus.INSIDE_SETTLEMENT
        else:
            status = ZoningStatus.DETACHED_ZONE
    elif below:
        status = ZoningStatus.TOUCHES_BELOW_THRESHOLD
    else:
        status = ZoningStatus.OUTSIDE
    # Plans to read next: those of the matches first, then of the boundary
    # cases, which exist precisely to point at the plan to inspect.
    plans: list[str] = []
    for match in [*matches, *below]:
        if match.zone.plan_name and match.zone.plan_name not in plans:
            plans.append(match.zone.plan_name)
    return ParcelZoning(
        parcel_number=geometry.broj_cestice,
        municipality_code=geometry.maticni_broj_ko,
        parcel_area_m2=parcel_area,
        status=status,
        in_building_area=bool(matches),
        matches=matches,
        below_threshold=below,
        intersecting_zones=len(zones),
        min_overlap=min_overlap,
        plans=plans,
        dataset=dataset,
    )
