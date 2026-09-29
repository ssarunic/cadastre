"""Croatian Cadastral System (Ureena zemlja) API Client."""

from .analysis import (
    AreaCheck,
    AssemblyAnalysis,
    AssemblyInput,
    RegisterComparison,
    build_assembly,
    check_area,
    compare_registers,
    count_distinct_persons,
    infer_party_type,
    person_key,
    same_person,
)
from .cache import CacheStats, MemoryCache, NullCache, ResponseCache, TieredCache
from .client import CadastralAPIClient
from .exceptions import CadastralAPIError, ErrorType
from .gis import GISCache, GMLParser, ParcelIndex
from .models import (
    BookOfDCSearchResult,
    CadastralOffice,
    Coordinate,
    FileStatus,
    LandRegistryUnit,
    LandRegistryUnitDetailed,
    LRUnitType,
    MainBookSearchResult,
    MunicipalitySearchResult,
    ParcelGeometry,
    ParcelInfo,
    ParcelLink,
    ParcelPart,
    ParcelSearchResult,
    ParcelZoning,
    Party,
    PlanGeneration,
    PlanningZone,
    Plumb,
    PossessionSheet,
    PossessionSheetSearchResult,
    Possessor,
    Provenance,
    SearchedParcel,
    ZoneKind,
    ZoneMatch,
    ZoningStatus,
    build_map_url,
)
from .planning import PlanningWFSClient
from .utils import display_parcel_number, normalize_parcel_number

__version__ = "0.3.0"

__all__ = [
    # Client
    "CadastralAPIClient",
    # Response cache
    "CacheStats",
    "MemoryCache",
    "NullCache",
    "ResponseCache",
    "TieredCache",
    # Exceptions
    "CadastralAPIError",
    "ErrorType",
    # GIS
    "GISCache",
    "GMLParser",
    "ParcelIndex",
    # Spatial plans
    "PlanningWFSClient",
    "ParcelZoning",
    "PlanGeneration",
    "PlanningZone",
    "ZoneKind",
    "ZoneMatch",
    "ZoningStatus",
    # Models
    "BookOfDCSearchResult",
    "CadastralOffice",
    "Coordinate",
    "FileStatus",
    "LandRegistryUnit",
    "LandRegistryUnitDetailed",
    "LRUnitType",
    "MainBookSearchResult",
    "MunicipalitySearchResult",
    "ParcelGeometry",
    "build_map_url",
    "ParcelInfo",
    "ParcelLink",
    "ParcelPart",
    "ParcelSearchResult",
    "Party",
    "Plumb",
    "Possessor",
    "PossessionSheet",
    "PossessionSheetSearchResult",
    "Provenance",
    "SearchedParcel",
    # Analysis (pure functions over the models)
    "AreaCheck",
    "AssemblyAnalysis",
    "AssemblyInput",
    "RegisterComparison",
    "build_assembly",
    "check_area",
    "compare_registers",
    "count_distinct_persons",
    "infer_party_type",
    "person_key",
    "same_person",
    # Helpers
    "display_parcel_number",
    "normalize_parcel_number",
]
