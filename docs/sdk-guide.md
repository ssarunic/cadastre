# Python SDK Guide

The `cadastral_api` package is the foundation the CLI and the MCP server are built
on. It gives you a rate-limited HTTP client, Pydantic V2 models for every response,
and GIS helpers for parcel geometry. Everything here runs against the included
mock server; see [legal.md](legal.md).

## Installation

```bash
pip install -e ./api
```

Requires Python 3.12 or newer.

## Configuration

The client reads a `.env` file and these environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `CADASTRAL_API_BASE_URL` | `http://localhost:8000` | Upstream address, the mock server by default |
| `CADASTRAL_API_TIMEOUT` | `10.0` | Request timeout in seconds (connecting, and the response of every search); a land-registry unit or parcel record is waited for up to 120 s, see `long_timeout` below |
| `CADASTRAL_API_RATE_LIMIT` | `0.375` | Minimum seconds between upstream requests |
| `CADASTRAL_CACHE_DIR` | `~/.cadastral_api_cache` | Where downloaded GML files are kept |
| `CADASTRAL_CACHE` | `memory` | Response cache backend: `memory` (in this process) or `off`; see Caching below |
| `CADASTRAL_CACHE_MEMORY_MB` | `64` | Byte budget of the memory response cache |

All of them can be overridden per client:

```python
from cadastral_api import CadastralAPIClient

client = CadastralAPIClient(
    base_url="http://localhost:8000",
    timeout=10.0,
    rate_limit=0.375,
    cache_dir="./gis_cache",
)
```

`long_timeout` (default 120 s, or `timeout` when that is larger) is the read
timeout of the two endpoints that return a whole record at once,
`get_lr_unit_detailed` and `get_parcel_info`: the server assembles a large
condominium's unit (thousands of shares) on every request, unpaged and
uncached, and takes 20 s or more before the first byte. Connecting keeps
`timeout`, so a server that is down is still reported after 10 s. A timeout
error names the timeout that applied in `details["timeout_seconds"]`.

Use the client as a context manager so the HTTP connection is closed.

### Caching

Every response the upstream sends is kept in the client for the lifetime of
its data class and served from there on the next identical request, without
touching the rate limiter: reference lists (offices, municipalities, main
books) for 24 hours, number-to-id searches for 6 hours, parcel records,
possession sheets and land-registry units for 30 minutes, file statuses for
5 minutes. The 30 minutes on the classes that name people is a policy, not
a setting: configuration can turn the cache off but never lengthen it. The
default backend is the memory of the process (`CADASTRAL_CACHE=memory`,
64 MB by default), so a CLI run starts empty and the MCP server keeps a
record between the pages an agent asks for; `CADASTRAL_CACHE=off` disables
it. Errors and empty answers are never stored. The disk and Redis layers of
[specs/response-cache-specification.md](../specs/response-cache-specification.md)
are not in this version yet.

```python
from cadastral_api import CadastralAPIClient, MemoryCache

with CadastralAPIClient(cache="memory") as client:     # or "off", or a backend
    unit = client.get_lr_unit_detailed("769", 21277)     # fetched
    unit = client.get_lr_unit_detailed("769", 21277)     # served from the cache
    print(unit.provenance.retrieved_at)                  # when the upstream sent it
    unit = client.get_lr_unit_detailed("769", 21277, refresh=True)   # fetched again
    print(client.cache.stats())    # CacheStats(backend='memory', entries=1, bytes=..., hits=1, misses=1)
    client.cache.clear()

with CadastralAPIClient(cache=MemoryCache(max_bytes=8 * 1024 * 1024)) as client:
    ...
```

`refresh=True` on `get_parcel_info`, `get_possession_sheet`,
`get_possession_sheet_by_number`, `get_lr_unit_detailed`,
`get_lr_unit_from_parcel` and `get_possession_sheet_parcels` reads the record
from the server again and replaces the cached copy; on the composed methods it
refreshes the records that name people (the parcel record, the unit, the
sheet), while the municipality, parcel-number and main-book lookups may still
come from the cache. `provenance.retrieved_at` on a record is the time of the
upstream fetch, the original one when the record came from the cache. A cached
body that the current models reject (a model changed since it was stored) is
dropped and fetched again; a cache hit never raises where a fetch would not.

## The three-step lookup

The upstream API needs a municipality code before it can find a parcel, and a
parcel id before it can return details. The SDK exposes each step and also
shortcuts across them.

```python
from cadastral_api import CadastralAPIClient

with CadastralAPIClient() as client:
    # 1. Municipality name to registration number
    municipalities = client.find_municipality("SAVAR")
    code = municipalities[0].municipality_reg_num          # "334979"

    # 2. Parcel number to parcel id
    results = client.find_parcel("103/2", code)
    parcel_id = results[0].parcel_id

    # 3. Full details
    parcel = client.get_parcel_info(parcel_id)
    print(parcel.parcel_number, parcel.area_numeric, "m²")
    print(parcel.total_possessors, "possessors")
    for land_type, area in parcel.land_use_summary.items():
        print(f"  {land_type}: {area} m²")

    # Steps 2 and 3 in one call
    parcel = client.get_parcel_by_number("103/2", code)
```

`find_municipality` also accepts `office_id` and `department_id` to list the
municipalities of one cadastral office. `find_parcel` matches partially: "114"
returns 114, 1140/1, and so on.

## Land registry units

A land registry unit (zemljišnoknjižni uložak) holds the legal record: sheet A
lists parcels, sheet B owners, sheet C encumbrances. Pending entries (plombe) mark
changes in progress.

```python
with CadastralAPIClient() as client:
    # From a parcel
    unit = client.get_lr_unit_from_parcel("103/2", "SAVAR")

    # Or directly, when you know the unit number and main book id
    unit = client.get_lr_unit_detailed("769", 21277)

    print(unit.summary())
    # {'unit_number': ..., 'main_book': ..., 'total_parcels': ..., 'total_area_m2': ...,
    #  'num_owners': ..., 'has_sheet_c_entries': ..., 'is_condominium': ...,
    #  'has_pending_plombe': ..., 'pending_plombe': [...]}

    for owner in unit.get_all_owners():
        print(owner.name, owner.address)

    for parcel in unit.get_all_parcels():
        print(parcel.parcel_number, parcel.area_numeric)

    if unit.has_pending_plombe():
        details = client.get_plombe_details(unit)   # one extra request per plomba
```

`unit.cadastre_harmonized` reports whether the cadastre and the land registry agree
on the source parcel, when the unit was reached from a parcel. `unit.is_condominium()`
detects condominium units (etažno vlasništvo) from `lr_unit_type_name`, which is more
reliable than the upstream `condominiums` flag; individual apartments appear as
shares in `unit.ownership_sheet_b.lr_unit_shares`. `unit.lr_unit_type` is the same
information as an enum (`LRUnitType.OWNERSHIP`, `CONDOMINIUM_DEFINED_SHARES`, `OTHER`).

### Possession sheets and their parcels

The cadastre's web form reads a possession sheet (posjedovni list) through
endpoints its own search does not expose; the client covers them:

```python
result = client.get_possession_sheet_parcels("363", "SAVAR")   # three requests
sheet = result.sheet                       # PossessionSheet with possessors and provenance
for parcel in result.parcels:              # SearchedParcel records, sorted by number
    print(parcel.parcel_number, parcel.area_numeric, parcel.land_use_summary)
    unit = parcel.resolved_lr_unit()        # inline on a harmonized parcel, via the link otherwise
result.total_area_m2, result.maybe_truncated   # True at 30 parcels: a server cap is not ruled out

client.get_possession_sheet(16179481)                  # by the id the searches carry
client.get_possession_sheet_by_number("877", 2387)     # by number and internal municipality id
client.resolve_municipality_id("SAVAR")                # 2387, the id these endpoints take
client.search_parcels(cad_municipality_id=2387, parcel_number="103/2")   # exact match
client.lookup_possession_sheet_number(16179481)        # -> number and registration number
```

A harmonized parcel's record carries an inline `lr_unit` with sheet B
(`parcel.lr_unit.owner_rows()`) and no possession sheet; a non-harmonized one
carries `possession_sheet` and `parcel_links`. A sheet that does not exist
raises `POSSESSION_SHEET_NOT_FOUND`.

### Finding the main book

The unit endpoint wants a main book id. When you only know the name (normally the
cadastral municipality), let the client resolve it, or search yourself:

```python
with CadastralAPIClient() as client:
    unit = client.get_lr_unit_detailed("769", main_book_name="SAVAR")

    for book in client.find_main_book("SAVAR"):
        print(book.main_book_id, book.main_book_name, book.court_name)   # 21277 SAVAR ZADAR
    for book in client.find_book_of_dc("ZADAR"):        # knjige položenih ugovora (KPU)
        print(book.book_id, book.book_name, book.office_name)
    for sheet in client.find_possession_sheet("363", "334979"):   # cadastre possession sheets
        print(sheet.possession_sheet_id, sheet.sheet_number)
```

A name that matches several books raises `LR_UNIT_NOT_FOUND` with reason
`main_book_ambiguous` and the candidates in `details`.

### Entry provenance

Every owner on sheet B carries the registration entry that put them there:

```python
for share in unit.ownership_sheet_b.lr_unit_shares:
    for owner in share.owners:
        entry = owner.entry                       # None on older shares
        if entry:
            print(entry.order_number, entry.entry_date, entry.diary_number,
                  entry.action_type, entry.priority_diary_number,
                  entry.transferred_from_unit, entry.description_text)
    for note in share.share_entries:              # zabilježbe on this share alone
        print(note.order_number, note.description_text)
    for sub in share.sub_shares:                  # co-owners of a divided share
        print(sub.description, [o.name for o in sub.owners])
```

`share.sub_shares_and_entries` holds both kinds as typed objects (`LRShare` or
`LREntry`), routed by the presence of `lrUnitShareId`. `OwnershipSheetB.owner_rows()`
and `share_entry_rows()` flatten them into the dicts the CLI and the MCP server
emit. On sheet C, `entry.amount` is the secured amount as sent ("134.000,00 EUR")
and `entry.amount_value` / `entry.amount_currency` the parsed number and currency.

### Sheet A1 variants

The parcel list of a unit arrives under one of two keys, never both:
`lrParcels` (lean land-register records, where `address` is the culture or
toponym of the old land register, not a location) or `cadParcels` (full cadastre
records). `unit.sheet_a1_source_key` says which; both populate
`unit.possessory_sheet_a1.cad_parcels`, with `parcel_parts` typed as `ParcelPart`
in both shapes. A lean record is the parcel as the land register keeps it:
its `parcel_number` is the land-register number (which differs from the
cadastre number wherever a new survey renumbered the parcels) and its id is
`lr_parcel_id`, an id of the land-register parcel table; `parcel_id` is None
there and must not be passed to `get_parcel_info`. Look the cadastre parcel
up by number and cadastral municipality instead.

### Building parcels

The API spells building parcels with a leading asterisk (`*35/1`). Pass any of
`"35/1.ZGR"`, `"35/1 ZGR"`, `"zgr. 35/1"` or `"*35/1"` to `find_parcel`,
`get_parcel_by_number` or `get_lr_unit_from_parcel`; `normalize_parcel_number`
maps them to the API spelling. `parcel.is_building_parcel` is true for them,
`parcel.parcel_number_display` renders `zgr. 35/1`, and they have no land
registry unit of their own (`get_lr_unit_from_parcel` reports
`parcel_not_in_land_registry`). Asking for the land parcel `"35/1"` when only
`*35/1` exists raises `PARCEL_NOT_FOUND` with reason `only_building_parcel_exists`,
so the two are never confused.

### Unknown server fields

Every model keeps keys it does not declare in `source_fields`. The client
reports them according to `unknown_fields` (`"warn"` logs each new key path once,
`"ignore"`, `"error"` raises `INVALID_RESPONSE` with reason `unknown_fields`;
also `CADASTRAL_API_UNKNOWN_FIELDS`). The coverage gate
`api/src/cadastral_api/tests/test_api_coverage.py` keeps `source_fields` empty
on every committed fixture.

## Parcel geometry

Geometry comes from INSPIRE GML files published per municipality. The client
downloads the file once, caches it under `CADASTRAL_CACHE_DIR`, and parses the
parcel out of it. Next to each ZIP the cache keeps a `source.txt` marker with
the base URL it was downloaded from; a client configured for a different server
downloads the municipality again instead of reusing that copy. The method returns
`None` when the parcel is not in the file.

```python
with CadastralAPIClient() as client:
    geometry = client.get_parcel_geometry("103/2", "334979")
    if geometry:
        print(geometry.povrsina_graficka, "m² (graphical area)")
        print(geometry.center, geometry.bounds)
        print(geometry.to_wkt())
        feature = geometry.to_geojson()      # GeoJSON Feature, properties carry map_url
        print(geometry.map_url())            # interactive map centred on the parcel
        print(geometry.map_url(zoom=20))     # closer, for very small parcels
```

Coordinates are in EPSG:3765 (HTRS96 / Croatia TM). The GML parser is available on
its own as `cadastral_api.GMLParser` when you already have a file.

### Parcels by area and neighbours

The cached GML of a municipality holds every parcel outline, so the questions
a parcel number cannot answer are answered locally, without a request per
parcel. `get_parcel_index` loads the file once per client into a
`ParcelIndex` (pure Python, a grid prefilter and exact ring tests; EPSG:3765
metres throughout):

```python
index = client.get_parcel_index("334979")
print(len(index), "parcels")

inside = index.in_bbox((380590, 4880880, 380680, 4880980))          # touching the box
whole = index.in_bbox((380590, 4880880, 380680, 4880980), "within")  # wholly inside it
triangle = index.in_polygon([(380590, 4880880), (380680, 4880880), (380590, 4880980)])
for hit in index.within_radius(380616.77, 4880907.83, 50.0):        # nearest first
    print(hit.parcel.parcel_number, hit.distance_m)
for neighbour in index.neighbours("103/2"):
    print(neighbour.parcel.parcel_number, neighbour.shared_boundary_m, neighbour.touches_at_point)
print(ParcelIndex.total_area(inside), "m2")
```

Each result item is an `IndexedParcel` with the `ParcelGeometry`, its
`ring`, `bounds`, `centroid` and `area_m2` (the graphical area from the map).
`neighbours` reports the length of the common boundary in metres and tells a
corner touch (`touches_at_point`) from a shared edge; `tolerance_m` (default
0.10) absorbs digitising gaps. Areas are graphical, from the cadastral map,
not surveyed: compare them with the registers' areas through `check_area`
(see "Provenance and reading across the registers") before quoting one.

## Spatial plans: building areas

Spatial plans do not reference parcels, so the only way to ask "is this parcel
in a building area, and of what kind" is a spatial join. The client takes the
parcel outline from the cadastral GIS data, asks the building-areas WFS
(građevinska područja, the nationwide vector layer the county spatial-planning
institutes derived from the plans in force) for every zone that intersects it,
and estimates by point sampling how much of the parcel each zone covers.

```python
with CadastralAPIClient() as client:
    zoning = client.get_parcel_zoning("396/1", "334979")
    if zoning is None:
        print("no geometry for this parcel")
    else:
        print(zoning.status)                 # inside_settlement | detached_zone |
                                             # touches_below_threshold | outside
        print(zoning.buildability)           # always "unknown": this is a screening
        for match in zoning.matches:         # largest overlap first
            zone = match.zone
            print(zone.designation_code,     # "T3" (camp), "GPN" (settlement area) ...
                  zone.designation,          # text as written in the plan
                  zone.zone_name,            # "SAVAR - KAMP"
                  zone.plan_name,            # "PPUO SALI - III. ID"
                  zone.plan_id,              # "HR-ISPU-PPGO-03794-R05"
                  zone.generation,           # old | new: which code list applies
                  f"{match.overlap_fraction:.0%}", match.overlap_m2)
        print(zoning.dataset.disclaimer)     # must accompany any use

    # The WFS on its own: zones by attribute, by bounding box or by WKT
    t2_zones = client.planning.find_zones(municipality_code="03794", designation_code="T2")
    nearby = client.planning.zones_in_bbox((380000, 4880000, 382000, 4882000))
```

Zones covering less than two per cent of the parcel (`min_overlap`, 0 to 1)
are listed in `below_threshold` rather than `matches`, and a parcel that only
touches a zone gets the status `touches_below_threshold`, never `outside`; plan
boundaries are drawn at 1:5000 and rarely follow parcel lines. Being inside a
building area does not mean anything may be built: provisions, plot size,
access, infrastructure and protection regimes are not evaluated, so
`buildability` is always `"unknown"`. `generation` matters: in old plans T1, T2 and T3 mean hotel, tourist
settlement and camp; in plans made under the 2024 Pravilnik they mean tourism
inside a settlement, a detached zone with accommodation and one without. Every
zone the service publishes today is `old`.

The endpoint is `CADASTRAL_PLANNING_WFS_URLS` (comma-separated mirrors, tried in
order on gateway errors and timeouts) or the `planning_wfs_urls` argument;
the default is `<base_url>/planning/wfs`, which the mock server serves. The
building areas are an interpretation of the plans, not the plans themselves:
the disclaimer in `ParcelZoning.dataset` has to be shown with the result.
`dataset.source_url` and `dataset.retrieved_at` record which mirror answered
the requests of that lookup (two mirrors are joined with "; " when the two
requests were answered by different ones) and when; the service publishes no
machine-readable date, and `state_note` says what the catalogues claim.
`plans` lists the plans of the matches and of the below-threshold zones, so a
boundary case still names the plan to read next.
Endpoint details: `specs/spatial-planning-api-specification.md`.

## Error handling

Every failure raises `CadastralAPIError` carrying an `ErrorType`:

```python
from cadastral_api import CadastralAPIClient, CadastralAPIError, ErrorType

with CadastralAPIClient() as client:
    try:
        parcel = client.get_parcel_by_number("999/9", "334979")
    except CadastralAPIError as e:
        if e.error_type is ErrorType.PARCEL_NOT_FOUND:
            print("no such parcel")
        elif e.error_type in (ErrorType.CONNECTION, ErrorType.TIMEOUT):
            print("upstream unreachable, is the mock server running?")
        else:
            print(e.error_type, e.details)
```

Error types: `CONNECTION`, `TIMEOUT`, `RATE_LIMIT`, `INVALID_RESPONSE`,
`PARCEL_NOT_FOUND`, `MUNICIPALITY_NOT_FOUND`, `LR_UNIT_NOT_FOUND`, `SERVER_ERROR`,
`ACCESS_DENIED` (HTTP 401 or 403: the server refused, which is not a network
failure and not an empty parcel) and `HTTP_ERROR` (any other 4xx; both carry
`status_code` in `details`). Rate-limit and server errors are retried with
backoff before being raised.

## Provenance and reading across the registers

Every record that `get_parcel_info` or `get_lr_unit_detailed` returns (and so
`get_parcel_by_number` and `get_lr_unit_from_parcel`) carries `provenance`:
the register it came from, the URL that answered and the time of retrieval
in UTC. A record built from a file has none. Quote it with anything you
forward, so that a printout is never taken for an official extract.

```python
parcel = client.get_parcel_by_number("103/2", "334979")
print(parcel.provenance.register, parcel.provenance.source_url, parcel.provenance.retrieved_at)
```

`cadastral_api.analysis` reads across the registers without a request:

```python
from cadastral_api import check_area, count_distinct_persons, person_key, same_person

# One person identity for both registers: case, diacritics, spacing,
# punctuation and a share suffix ("... ZA 2/6") ignored; a relative's name
# ("POK. BOŽE", "UD. IVE") only in the loose key, so that match is fuzzy.
match, fuzzy = same_person(person_key("ŠARUNIĆ AUGUSTIN POK. BOŽE"), person_key("Sarunic Augustin"))
# (True, True)
owners = lr_unit.get_all_owners()
count_distinct_persons((o.name, o.tax_number) for o in owners)   # people, not records

# Do the areas agree? Cadastre record, land register, cadastral map.
check = check_area(cadastre_m2=parcel.area_numeric, land_registry_m2=1180, gis_m2=geometry.povrsina_graficka)
check.compared, check.max_difference_fraction, check.mismatch   # flagged above 5 %
```

Tax numbers decide when both records carry one; the count never merges two
people on the loose key alone.

`compare_registers` puts the two registers side by side for one parcel:

```python
from cadastral_api import compare_registers, infer_party_type

parcel = client.get_parcel_by_number("1122/1", "334979")
unit = client.get_lr_unit_from_parcel("1122/1", "334979")
result = compare_registers(parcel, unit, gis_area_m2=geometry.povrsina_graficka)
result.relationship          # same | overlapping | disjoint | cadastre_only | ...
result.summary               # the same in a sentence
[(m.possessor.name, m.owner.name, m.fuzzy) for m in result.matched]
[o.name for o in result.owners_only]     # registered owners not on the possession sheet
result.distinct_people, result.party_types, result.public_body_owner_share
result.area_check.mismatch   # cadastre against sheet A and the map

infer_party_type("HRVATSKE ŠUME d.o.o.")   # company, inferred=True, basis names the legal form
```

Every person carries `party_type_inferred`, read from the spelling of the
name and always marked as an inference: enough to estimate how many public
bodies and companies a set of parcels involves, not to state a fact about
one owner.

`build_assembly` turns a set of such records into the tables of a land
assembly: the persons x parcels matrix, the persons ranked by controlled
area and grouped by surname, and the parcels ranked by a transparent
ease-of-acquisition score:

```python
from cadastral_api import AssemblyInput, build_assembly
from cadastral_api.analysis import DEFAULT_WEIGHTS, parcels_csv, persons_csv

items = []
for number in ["103/2", "45", "396/1"]:
    parcel = client.get_parcel_by_number(number, "334979")
    unit = client.get_lr_unit_from_parcel(number, "334979")   # or None when not in the registry
    zoning = client.get_parcel_zoning(number, "334979")        # optional
    items.append(AssemblyInput(parcel, unit, compare_registers(parcel, unit), zoning))

analysis = build_assembly(items, weights={**DEFAULT_WEIGHTS, "in_building_area": 0.3})
for summary in analysis.parcels:          # easiest to acquire first
    print(summary.parcel_number, summary.score, summary.relationship)
for person in analysis.persons[:10]:      # largest controlled area first
    print(person.name, person.controlled_area_m2, person.owner_of, person.possessor_of)
analysis.surname_groups, analysis.matrix, analysis.totals, analysis.scores[0].factors
open("parcels.csv", "w").write(parcels_csv(analysis))
```

The score is a weighted share of yes/no factors (`single_owner`,
`owner_is_possessor`, `no_encumbrances`, `no_pending_plombe`,
`in_building_area`); a factor that cannot be evaluated (no unit, no zoning)
is left out of the numerator and the denominator, and each `AcquisitionScore`
lists its `factors`, `weights` and `notes`. Controlled areas use cadastre
areas and an owner role without a registered share counts the whole parcel;
`analysis.notes` repeats these caveats for whoever reads the tables.

## Things to know about the data

- Ownership fractions are optional. Many possessor records have no `ownership`
  field, so `ownership_decimal` is `None`.
- The upstream returns area as a string. Models convert it; use `area_numeric` for
  an integer.
- One parcel can have several possession sheets.
- The `condominiums` boolean on a land registry unit is unreliable; use
  `is_condominium()`.
- Models validate strictly. Unexpected upstream data raises
  `ErrorType.INVALID_RESPONSE`; unknown keys are kept in `source_fields` and
  reported per the client's `unknown_fields` setting.
- Entry kinds are `uknjižba`, `predbilježba`, `zabilježba` and the generic
  `upis`; a deletion sets `entry.deletes_prior_entry`. `share.share_status` is
  `active` for status 0 and `historical` otherwise.
- A parcel whose links name different units raises `LR_UNIT_NOT_FOUND` with
  reason `lr_unit_ambiguous`; `parcel.lr_unit_candidates()` lists them.
- Share totals are exact: `unit.ownership_sheet_b.total_ownership_fraction()`
  is a `Fraction`, `total_ownership_accounted()` its float.
- Parcels of a unit in the lean `lrParcels` shape carry only number, area,
  address and status in the unit; the other cadastre fields are `None`, not false.
- A share's `lrOwners` may be null or absent (co-owners then live in
  `sub_shares`); `LRShare.has_direct_owners` tells the two apart.

## Reference

- Models are specified in [specs/pydantic-entities-implementation.md](../specs/pydantic-entities-implementation.md).
- Upstream endpoints and payloads are in [specs/croatian-cadastral-api-specification.md](../specs/croatian-cadastral-api-specification.md).
- Worked examples: [api/examples/](../api/examples/), starting with
  [basic_usage.py](../api/examples/basic_usage.py) and
  [lr_unit_example.py](../api/examples/lr_unit_example.py).
