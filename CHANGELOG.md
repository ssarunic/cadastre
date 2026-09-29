# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/). Every release corresponds to an
annotated git tag `vX.Y.Z`; see [specs/release-process.md](specs/release-process.md).

The whole monorepo (SDK, CLI, MCP server, mock server) shares one version
number and one tag.

## [Unreleased]

### Added

- SDK: a response cache in the client (`specs/response-cache-specification.md`,
  phase 1). Every upstream response is kept for the lifetime of its data
  class (reference lists 24 h, searches 6 h, parcel records, possession
  sheets and land-registry units 30 min, file statuses 5 min) and served
  from the cache on the next identical request without touching the rate
  limiter; two threads asking for one record make one fetch; errors and
  empty answers are never stored. `CADASTRAL_CACHE=memory|off` (default
  `memory`, `CADASTRAL_CACHE_MEMORY_MB` sizes it) or
  `CadastralAPIClient(cache=...)`; `client.cache.stats()` and `clear()`;
  `refresh=True` on `get_parcel_info`, `get_possession_sheet*`,
  `get_lr_unit_detailed`, `get_lr_unit_from_parcel` and
  `get_possession_sheet_parcels` reads the record again. A cached body the
  current models reject is dropped and fetched again. `provenance.retrieved_at`
  is the time of the upstream fetch, the original one on a cache hit. New
  dependency `cachetools`.
- CLI: `cadastral info` reports the response cache (backend, entries, size).
- MCP: `get_parcel` and `get_lr_unit` take `refresh`, and their `page` block
  carries `fetched_at`; paging, detail levels and filters of a record already
  read make no upstream request. `CADASTRAL_CACHE` is read from the client's
  `env` block.
- SDK, MCP: `build_assembly` returns `blockers`, one row per parcel and
  counted sale blocker with the parcel, the unit and every blocker field
  (`ParcelBlocker`), the list the verdicts and counts on the parcels rest
  on, so a report or a spreadsheet needs no second call per unit;
  `blockers_csv` exports the same table; `include_blockers=false` leaves it
  out of a large response and the size error names that option.
- MCP: the prompt `due_diligence_report(parcels, municipality, language,
  format)`: the request that has the model call `build_assembly` and render
  the result as a screening report with a fixed section order, Croatian
  register terms with the English gloss, provenance on every fact and the
  screening and inference notices, in Croatian or English, as Markdown or one
  self-contained HTML file. The same text for pasting into Claude Code is in
  `docs/due-diligence-report-prompt.md`.
- MCP: `cadastral-mcp --transport http` serves the tools over the SDK's
  streamable HTTP transport at `http://127.0.0.1:8080/mcp` (stateless, JSON
  responses; `GET /health`), for clients that connect to a URL such as Claude
  Code (`claude mcp add --transport http ...`) and the MCP Inspector. No
  authentication: loopback by default, another interface is logged as a
  warning. The placeholder SSE endpoint, `/mcp/capabilities` and the CORS
  setting are gone; `fastapi` and `uvicorn[standard]` are no longer
  dependencies (the SDK brings `starlette` and `uvicorn`). The handlers run
  the SDK client in worker threads, so one slow land-registry read no longer
  stalls every other caller.
- MCP: access keys for the HTTP transport. `MCP_HTTP_KEYS` in `.env` lists
  random keys, read on every check, so removing one revokes it without a
  restart. A key is accepted as a bearer header (Claude Code, Codex, the MCP
  Inspector) or on the login page of the built-in OAuth 2.1 authorization
  server (claude.ai custom connectors, ChatGPT): the client registers itself,
  the person types a key, tokens are issued for as long as the key stays in
  the file and kept in `MCP_HTTP_AUTH_STORE` across restarts;
  `MCP_HTTP_PUBLIC_URL` is the issuer behind a proxy, and its hostname is
  accepted by the DNS-rebinding protection of a loopback listener. Without
  keys the server is open and refuses to listen anywhere but the loopback
  interface.

### Fixed

- SDK: the rate limiter was a check-then-sleep on one timestamp, so
  concurrent threads (the MCP server over HTTP) could all fire at once.
  `cadastral_api.rate_limiter.RateLimiter` hands each caller the next slot
  one interval apart, in both the API client and the planning WFS client;
  the per-file GML parsers and parcel indexes and the municipality download
  are locked as well.

- SDK, CLI, MCP: a land-registry unit whose sheet A lists a parcel with a
  possession sheet that has no number (`possessionSheetNumber: null`, unit
  11216 of main book 221290) was rejected by the `PossessionSheet` model
  (`INVALID_RESPONSE`, reason `validation_failed`), hiding the whole unit.
  `possession_sheet_number` is optional now; the CLI prints `-` for it and
  the JSON has `null`.

### Changed

- Repository renamed from `boljeuredjenazemlja` to `cadastre`; the old
  GitHub URL redirects. Package, command and module names are unchanged.

## [0.3.0] - 2026-09-16

### Security

- Mock server: the ATOM download route (`/atom/ko-<code>.zip`) no longer builds
  a file path from the request; the municipality code is matched against the
  ZIP files under `data/geometry`, so anything but a registration number is
  a 404. The building-areas WFS parses the `INTERSECTS` clause of `cql_filter`
  in linear time (the old pattern was quadratic on hostile input).
- MCP: the HTTP transport logs only the JSON-RPC method name of an SSE
  request, with line breaks stripped, instead of the whole request body.

### Added

- SDK: `CadastralAPIClient.resolve_municipality_reg_num(name_or_code)` turns a
  municipality name into its registration number the same way everywhere: a
  number passes through, an exact name wins, a single match is taken, and an
  ambiguous name raises `MUNICIPALITY_NOT_FOUND` with reason
  `municipality_ambiguous` and the candidates. The CLI (single and list
  lookups), the MCP tools and `get_lr_unit_from_parcel` all use it; the list
  path and the MCP used to take the first of several matches silently, and
  the CLI list resolved the same name once per parcel instead of once.
- SDK: `GISCache.cached_municipalities()` and `GISCache.size_bytes()` list
  what the GIS cache holds; `strip_html(keep_breaks=True)` and `fold_text()`
  in `cadastral_api.utils` are the one HTML stripper and one diacritic fold
  the CLI and the MCP share.

- MCP: `get_parcel` pages through the possessors of a parcel with `offset` and
  `limit`, counted across its possession sheets in sheet order, and every
  cadastre entry carries `total_possessors`, `possessors_truncated` and a
  `page` block (`next_offset` says where to continue). A parcel under a large
  condominium keeps hundreds of possessors on one sheet and used to overrun
  the client's response limit whole; an entry above the response ceiling is
  now recorded as that parcel's error naming a smaller `limit` and the
  `source` values that omit the possessors, as `get_lr_unit` already does.
  Each entry also carries `distinct_possessors`, the different names among
  the possessor records (a person holding two units is two records).
  `possessor_name` (every word must occur in the name, case and diacritics
  ignored) and `condominium_unit` ("E-16" or "16") filter the possessors, so
  one person or one flat is found on a sheet of thousands without paging;
  a filtered entry carries `possessor_filter` and `matching_possessors`.
  A parcel entry is refused above 100,000 characters (twice the
  land-registry ceiling, since possessor records are flat and uniform) and
  the refusal suggests the largest limit that fits rather than a quarter of
  the window.
- MCP: `get_lr_unit` takes `owner_name` and returns only the owners whose
  name contains every word of it (case and diacritics ignored, words in any
  order): the owner rows with `detail="ownership"`, the shares holding such
  an owner, kept whole with their co-owners, with `"shares"` and `"full"`.
  "Is this person an owner in unit X" is one call on a condominium of
  hundreds of shares instead of a walk through every page; the answer
  carries `matching_owners` / `matching_shares` next to the whole sheet's
  totals, and 0 matches is an answer, not an error.
- SDK: `PossessionSheet.is_condominium`, true when a possessor carries a
  condominium unit number or a common-area share.
- SDK: `ErrorType.ACCESS_DENIED` for HTTP 401 and 403 and `ErrorType.HTTP_ERROR`
  for any other 4xx, both with `status_code` in the details. A refusal used to
  fall through as `connection`, indistinguishable from a network failure. The
  CLI labels them "Access denied" / "Pristup odbijen" and "HTTP error".
- SDK: every record from `get_parcel_info` and `get_lr_unit_detailed` carries
  `provenance` (`register`, `source_url`, `retrieved_at` in UTC), stamped by
  the client after the fetch; a record built from a file has none.
  `GISCache.downloaded_at(code)` gives the download time of a cached
  municipality.
- SDK: `cadastral_api.analysis`, pure functions over the models: `person_key`,
  `same_person` and `count_distinct_persons` (one person identity for both
  registers: case, diacritics, spacing, punctuation and a share suffix
  ignored, a relative's name ("POK. BOŽE", "UD. IVE") only in the loose key,
  tax numbers decisive when both records have one) and `check_area` /
  `AreaCheck` (cadastre, land-register and graphical areas compared, a
  difference above 5 % flagged).
- SDK: the possession-sheet endpoints the cadastre's web form uses
  (OQ4 of the coverage specification, resolved by the capture of
  2026-09-15): `get_possession_sheet(id)` and
  `get_possession_sheet_by_number(number, cad_municipality_id)` return a
  `PossessionSheet` with its possessors; `search_parcels` is the
  `POST /cad/search-parcels` behind the form (every parcel of a sheet, an
  exact parcel number, or a parcel id) returning `SearchedParcel` records in
  their two shapes (a non-harmonized parcel with its `possession_sheet` and
  links, a harmonized one with an inline `lr_unit` carrying sheet B);
  `get_possession_sheet_parcels(number, municipality)` bundles the three
  calls; `resolve_municipality_id` gives the internal id the endpoints need;
  `lookup_possession_sheet_number` is the reverse lookup;
  `ErrorType.POSSESSION_SHEET_NOT_FOUND`. The mock server serves all four
  routes from its parcel data.
- CLI: `get-possession-sheet SHEET -m K.O.` (Croatian `posjedovni-list`): the
  sheet, every parcel on it with area, land use and land-registry unit, and
  with `--show-owners` (`--posjednici`) its possessors; `--format json`
  writes the sheet with `parcels`, `total_parcels`, `total_area_m2` and
  `parcels_complete`, `--format csv` one row per parcel. The Croatian
  spelling of `search-possession-sheet` is now `traži-posjedovni-list`
  (it was `posjedovni-list`), in line with `traži-općinu`; both commands'
  help now point to each other.
- MCP: `get_possession_sheet(sheet_number, municipality)`: the sheet's
  possessors (paged, filterable by name) and every parcel on it with area,
  land use and land-registry reference, `total_area_m2`, both provenances
  and `parcels_complete` (false with a note when the list is as long as the
  search has ever returned, since a server cap is not ruled out).
  `find_possession_sheet` no longer says the sheet cannot be read.
- SDK: `ParcelIndex` (`cadastral_api.gis`), a spatial index over the parcels
  of one municipality's cached GML: `in_bbox`, `in_polygon` (touching, or
  wholly within, boundary included), `within_radius` (distance from a point
  to each outline, nearest first), `neighbours` (shared boundary length in
  metres, corner touches told apart) and `total_area`; pure Python with a
  grid prefilter. `CadastralAPIClient.get_parcel_index(code)` builds it once
  per GML file. `geometry_ops` gains point, segment and ring distances,
  `shared_boundary_length`, `ring_centroid` and `parse_ring` (WKT or
  vertex lists); `ParcelGeometry.ring` gives the outline as tuples.
- MCP: `find_parcels_in_area` (bounding box, polygon or radius around a
  point, EPSG:3765 metres; `relation` intersects or within; paged rows with
  graphical area, centroid, bounds, distance and map link; `total_area_m2`
  over every match; optional GeoJSON; the map's provenance under `dataset`)
  and `find_parcel_neighbours` (parcels sharing a boundary or a corner with
  one parcel). Longitude/latitude input is refused with a hint.
- SDK: `compare_registers(parcel, lr_unit)` in `cadastral_api.analysis`
  matches a parcel's cadastre possessors against its unit's registered
  owners with the shared person identity (exact first, then fuzzy and
  flagged) and returns a `RegisterComparison`: relationship (`same`,
  `overlapping`, `disjoint`, `cadastre_only`, ...), matched pairs with
  `shares_agree`, who is in one register only, distinct people, inferred
  party types, the share registered to public bodies and the area check
  against sheet A. `infer_party_type(name)` reads individual / company /
  state / municipality from a name (legal forms, "Republika Hrvatska",
  grad / općina / županija), always labelled inferred.
- MCP: `compare_registers(parcels)`: one entry per parcel with the
  comparison, both registers' provenance and, when the unit could not be
  read, `land_registry_error`; units shared by several parcels are read
  once; `relationships` and `people` (distinct possessors, owners and people
  across the set) summarise the whole set.
- SDK: `build_assembly(items)` and `acquisition_score(item)` in
  `cadastral_api.analysis`: the persons x parcels matrix (long form), the
  persons ranked by controlled area (share x cadastre area, plus the parcels
  only possessed) and grouped by surname, and an ease-of-acquisition score
  per parcel as a weighted share of yes/no factors (single owner, owner is
  possessor, no encumbrances, no pending plombe, in a building area) whose
  weights are returned and overridable; a factor that cannot be evaluated is
  left out of the score rather than counted against the parcel. Totals by
  land use, relationship and zoning status. `parcels_csv`, `persons_csv`,
  `matrix_csv` and `parcels_geojson` export the tables as text or a
  FeatureCollection.
- MCP: `build_assembly(parcels, include_zoning, weights, export,
  persons_offset, persons_limit)`: the analysis over up to 50 parcels, units
  read once, zoning optional (a failed zoning lookup is a note, not an
  error), references that could not be read listed under `failed`, and one
  export at a time under `export`.
- SDK: `cadastral_api.analysis.sale_blockers`: `detect_blockers(unit)` reads
  what is registered against a land-registry unit that bears on a sale into
  a list of `Blocker`s, each with a kind (pending_entry, mortgage, lien,
  enforcement, dispute, transfer_prohibition, preemption, social_claim,
  personal_servitude, easement, fiduciary_transfer, rejected_request,
  public_body_share, other_annotation), a severity (blocking, conditional,
  informational; defaults overridable), the share or condominium unit it
  attaches to (a mortgage on flat 88 does not block flat 40), the entry it
  comes from, the amount and the beneficiary, and the pattern the
  classification rests on; a `verdict` (clear, conditional, blocked) follows
  the rule returned next to it and is a screening of the register's text,
  not a legal opinion. An entry the table does not recognise stays in the
  list as `other_annotation`; an entry a later entry deletes goes to
  `blockers_cancelled`. `owner_name` or `condominium_unit` narrow the answer
  to one owner's shares or one flat; a plomba detail map turns a bare plomba
  into the request it is. `cadastral_api.analysis.owner_flags`: per owner,
  `likely_deceased` (registration entry older than 40 years, owner carried
  over from an earlier unit, or a death marker on the owner's own name),
  `address_abroad` (a country named in the address, or a foreign postcode as
  a weak signal; unknown without an address) and `public_body`, every one
  marked inferred with its basis. `owner_rows()` carries
  `share_order_number` (the top-level share, as sheet C refers to it).
  `compare_registers` adds `sale_blockers` (the unit's blockers plus
  `owner_not_possessor` and `fuzzy_owner_match`) and `owner_flag_counts`,
  and every owner record its `flags`; `build_assembly` derives the
  `no_encumbrances` and `no_pending_plombe` factors from the blockers (an
  informational note or a cancelled entry no longer counts against the
  parcel), gives each parcel `sale_verdict`, `blocker_counts` and
  `blocker_kinds`, each person `likely_deceased` and `address_abroad`, each
  surname group the counts of both, and the totals `parcels_by_verdict`,
  `persons_likely_deceased` and `persons_address_abroad`; the CSV exports
  carry the new columns. `surname_of` skips markers, so "POKOJNI HORVAT
  MARKO" groups under Horvat.
- SDK: the person identity matches a cadastre possessor written with the
  father's name after a comma ("ŠARUNIĆ AUGUSTIN, BOŽO") to the owner
  written with the marker ("ŠARUNIĆ AUGUSTIN POK. BOŽE"), and a name written
  given name first ("AUGUSTIN ŠARUNIĆ") to the register's surname-first form;
  both are reported as fuzzy matches, never merged silently, and the distinct
  counts still use the strict key. A personal servitude (habitation,
  usufruct, maintenance) registered 40 years ago or more is a blocker marked
  `likely_lapsed` with the reason in its basis (the holder's death ends it;
  deletion needs the death certificate); a plomba whose resolved file is a
  cadastre administrative case (UP/I 932) says so in its basis. The CLI
  prints the lapsed count under the blockers table.
- SDK: `compare_registers` matches per person, not per share record: once
  one record of an owner on several shares matches a possessor, the others
  match the same possessor instead of landing in `owners_only` and raising an
  `owner_not_possessor` blocker (the assembly counts that possessor's share
  once). The same words in another order with no relative on either side
  ("AUGUSTIN ŠARUNIĆ" against "ŠARUNIĆ AUGUSTIN") are an exact match, not a
  fuzzy one; only a relative written differently ("AUGUSTIN, BOŽO" against
  "AUGUSTIN POK. BOŽE") is fuzzy. `likely_deceased` has a fourth signal,
  `legacy_record`: a record with neither an OIB nor a registration entry was
  carried from the paper register and is usually an estate. An
  `area_mismatch` above the 5 % tolerance is a conditional blocker of the
  comparison. `owner_not_possessor` is informational when the owner's entry
  is recent and carries an OIB (the cadastre lags the register, the normal
  state) and conditional otherwise (an old or legacy record, so the possessor
  may be a genuine third party). `compare_registers(plombe_detail=...)` names
  the pending requests among the blockers.
- SDK: a share registered to an owner likely deceased is a `likely_estate`
  blocker of its own (conditional, scoped to the share, on every surface),
  whether or not the cadastre lists the same person: an unprobated estate
  blocks that share even when the usufructs around it are deleted. A match
  extends to a person's other shares by OIB only (the same name on another
  share may be a namesake); a name written in another order is fuzzy unless
  the shares or the addresses corroborate it. An area difference counts as
  a mismatch only above the 5 % tolerance and above 20 m²
  (`DEFAULT_AREA_MIN_DIFFERENCE_M2`), so digitisation noise on a small
  building parcel is not a finding.
- SDK: each matched pair says how it was found, `via` (`tax_number`, `name`,
  `name_reordered`, `name_loose`, `tax_number_extension`) and, for an
  extension, `extended_from` (the share it was extended from), so a safe
  extension can be told from a namesake later; the comparison summary counts
  people, not pairs; an owner whose share is already a `likely_estate`
  blocker gets no `owner_not_possessor` row (a deceased owner not appearing
  as possessor is expected, not a second risk); the fuzzy-match wording says
  which of the two loose rules applied; `plombe_detail_included` is true
  whenever the detail was asked for, and a pending request resolved to a
  cadastre case is described as one. `by_tax_number` is derived from `via`,
  so the two cannot disagree.
- MCP: the `people` block of `compare_registers` and `totals.distinct_people`
  of `build_assembly` count a person matched across the two registers once
  (they added the possessors and the owners, so every match counted twice).
- MCP: `compare_registers` and `build_assembly` take `include_plombe_detail`
  (the plomba detail fetched once per unit), so a "blocked" parcel says what
  the pending request is.
- MCP: every `get_lr_unit` entry carries `sale_blockers` at every detail
  level (the blockers themselves in "ownership" and "encumbrances"; the
  verdict, counts and rule elsewhere, since a large condominium's list runs
  to tens of kilobytes) and `owner_flags_summary`; each "ownership" row
  carries `flags`. `condominium_unit` narrows the blockers to one flat;
  `include_plombe_detail` also names the pending requests among them, from
  one fetch. `compare_registers` and `build_assembly` carry the same
  through the SDK models. The size ceiling names the narrowing options when
  the blockers are many.
- CLI: `get-lr-unit --blockers` (Croatian `--zapreke`) prints the sale
  screening (verdict, one row per blocker with kind, severity, the share or
  flat it applies to, description and amount, the cancelled count and the
  rule) and the owners flagged likely deceased, abroad or a public body with
  the basis of each flag; `--format json` writes `sale_blockers` and
  `owner_flags`, the list CSV gets `sale_verdict` and `blockers` columns.
  With `--plombe-detail` the pending requests are named.
- MCP: every `get_parcel` entry carries `provenance` and `area_check` (the
  cadastre area against the cadastral map's graphical area and the
  land-register area on the parcel link), every `get_lr_unit` entry
  `provenance` and, on the owner levels, `distinct_owners`; a failed entry of
  either tool carries `error_type` (`parcel_not_found`, `access_denied`,
  `rate_limit`, `response_too_large`, `invalid_request` ...) and
  `error_details`, and every tool error message ends with `[error_type=...]`.
  `download_municipality_gis` returns `downloaded_at`.

### Changed

- MCP: the tool list a client receives from `tools/list` now carries every
  parameter's description in the input schema (`Annotated[..., Field(...)]`
  on the tool signatures, `Field(description=...)` on `ParcelRef` and
  `LRUnitRef`) and the choice parameters as enums (`get_parcel.source`,
  `get_lr_unit.detail`, `get_parcel_geometry.format`,
  `find_parcels_in_area.relation`, `build_assembly.export` are `Literal`
  types, so a typo is refused by the schema instead of the handler). The
  docstrings no longer repeat the parameters in an `Args:` block. The server
  sends an `instructions` text in the `initialize` response (the two
  registers, where to start, paging, provenance), `find_parcel` and
  `resolve_municipality` say when to use `get_parcel` and
  `list_municipalities` instead, `list_cadastral_offices` names its result
  keys, and the four prompts describe what they produce instead of "Generate a
  prompt to ...". `mcp/tests/test_tool_surface.py` guards all of it.

### Fixed

- SDK, CLI, MCP: a land-registry unit with no entry in the electronic diary
  comes back without the `lastDiaryNumber` key, and the
  `LandRegistryUnitDetailed` model rejected the whole unit (`INVALID_RESPONSE`,
  reason `validation_failed`), hiding its owners and encumbrances (k.o. LUKA
  11269, 11225). `last_diary_number` is optional now; the CLI prints an empty
  row and the JSON has `null`.
- SDK, CLI, MCP: a possession sheet harmonized with the land registry comes
  back from the cadastre as a stub without possessors (and, by number,
  without its id) that names the land-registry unit; the `PossessionSheet`
  model rejected it. `possession_sheet_id` is optional now, `lr_unit_id` is
  declared, `possessors_in_land_registry` tells the stub apart, and
  `get_possession_sheet` (MCP and CLI) lists the unit's registered owners
  from the sheet B the parcel search inlines, labelled as land-registry
  owners. The stub's missing sheet id and municipality are filled from the
  parcel records (`backfilled_from_parcels`), `is_condominium` is null on it,
  and `possessor_name` reports `matching_owners` there. The mock server
  returns the stub for its harmonized sheets and caps the sheet-number
  search at 50 records, as the live one does.
- MCP: `distinct_possessors` compared title-cased names, so a possessor
  written "ŠARUNIĆ" on one sheet and "SARUNIC" on another counted twice; it
  now uses the shared person identity (`count_distinct_persons`).

- CLI: `get-geometry --format wkt` printed the polygon through the terminal
  renderer, which wrapped it at 80 columns even when piped; it is printed as
  one line now. An unknown municipality in `get-parcel` and the other
  commands now prints the suggestions (search, list, use the code) that were
  written for it but never reached.
- SDK: the parser of a municipality's GML file is kept per client, so a list
  of parcels in one municipality parses the file once instead of once per
  parcel; the zoning overlap estimate tests each sample only against the
  zone edges near the parcel, which cuts the cost on settlement polygons of
  thousands of vertices. The MCP `get_parcel` also stops computing the map
  link twice for a parcel given by number.
- MCP: `get_parcel`'s land-registry hint now uses the same resolution as
  `data.lr_unit` (direct unit, then the units of parcel links, then the
  links themselves), so the two no longer disagree for a parcel reachable
  only through `parcel_links`.

- MCP: `get_parcel` promised the land-registry reference under `data.lr_unit`
  but left it null for a parcel whose unit the cadastre reaches only through
  parcel links; the resolved unit is now placed there and
  `data.lr_reference_shape` says `linked`.
- SDK, MCP: a possession sheet whose shares do not sum to 1 carries
  `total_ownership_note` with the exact fraction and why (the shares are the
  register's, copied from the unit's list B, not a rounding error).
- SDK: a cadastre record whose land-register link (`parcelLinks[]`) carries
  no `area` (parcel 9970 in k.o. SPLIT, id 16901331) failed to parse; the
  field is now optional.
- SDK, CLI, MCP: the lean parcel records of list A (`lrParcels`) are the land
  register's own parcels, not the cadastre's: their id belongs to the
  land-register parcel table and their number is the land-register number
  (unit 8974 of GRAD ZAGREB lists 7484/3 with id 36039405 where the cadastre
  has 4090/1 in k.o. PEŠČENICA with id 21358541). The id used to be exposed
  as `parcel_id` and, fed to `get_parcel_info`, fetched an unrelated parcel;
  it is now `lr_parcel_id` (`id_zk_cestice` in Croatian output) and
  `parcel_id` is null on lean records.
- SDK: a large condominium's land-registry unit (`get_lr_unit_detailed`,
  thousands of shares) or parcel record (`get_parcel_info`, thousands of
  possessors) failed with a timeout after 10 s, since the server assembles
  the whole record on every request and takes 20 s or more before the first
  byte. Those two calls now wait up to `long_timeout` (120 s, or
  `CADASTRAL_API_TIMEOUT` when that is larger) for the response body;
  connecting and every other endpoint keep the 10 s, and the timeout error
  names the value that applied.
- SDK: `PossessionSheet.total_ownership` on a condominium sheet summed each
  possessor's share of their own unit ("1/1" of a flat) and reported
  thousands of percent for a large building; it now counts each unit once:
  the unit's common-area share (`condominium_share_ownership`) times its
  co-owners' shares of the unit added together and capped at 1, so two
  co-owners of one flat count the flat once whether they are recorded "1/2"
  each, "1/1" each or without a unit share. Null when the cadastre gives no
  common-area shares.

- CLI: the hint under a usage error ("Try 'cadastral ... --help' for help.")
  names the help option in the language of the session: `--help` in English,
  `--pomoć` in Croatian. click 8.5 started naming the longest spelling, which
  put `--pomoć` into English sessions; every spelling stays accepted.
- CLI documentation: the generated pages of 0.2.0 still said `cadastral 0.1.0`
  in their banner and the `get-zoning` example had been captured from the real
  building-areas service through a developer's `.env`, so the documentation
  gate failed on the release commit. The docs build now pins the building-areas
  endpoint to the mock server whatever `.env` says, and `scripts/release.py`
  rebuilds the documentation after the version bump and commits it with the
  release.

### Removed

- SDK: `CadastralAPIClient.get_map_url()` (it built the old
  `?cad_parcel_id=` link; use `ParcelGeometry.map_url()` or
  `build_map_url()`) and `get_municipality_gis_download_url()` (it named the
  production host; `GISCache` downloads from the configured base URL).

## [0.2.0] - 2026-09-14

### Added

- Spatial plans: what the building areas (građevinska područja) derived from
  the plans in force say about a parcel. SDK `CadastralAPIClient.get_parcel_zoning`
  and `PlanningWFSClient` (mirror rotation over the Ministry's GeoServer
  hosts, `CADASTRAL_PLANNING_WFS_URLS`), models `ParcelZoning`, `PlanningZone`
  (with `generation`, because T1/T2/T3 mean different things in old and
  new-generation plans), `ZoneMatch` with an overlap fraction estimated by
  point sampling, `ParcelZoning.buildability` (always `unknown`: the lookup is
  a screening, never a building permission), a `touches_below_threshold`
  status with the sub-threshold zones kept in `below_threshold`, and
  `PlanningDataset` carrying the dataset's disclaimer, the mirror that
  answered and the retrieval time. CLI `get-zoning` (`uz namjena`) with
  table, JSON, CSV and GeoJSON output;
  MCP tool `get_parcel_zoning`; the mock server imitates the WFS at
  `/planning/wfs` with synthetic zones around the SAVAR sample parcels.
  Endpoint research in `specs/spatial-planning-api-specification.md`.
- Complete API coverage per `specs/api-coverage-specification.md`. Every key
  the public API returns is now a declared, typed field: `Party.entry` (the
  registration entry that put an owner on a share, with `priority_diary_number`
  and `transferred_from_unit` parsed from its text), `LRShare.sub_shares` and
  `LRShare.share_entries` (the two kinds of `subSharesAndEntries` element,
  routed by a discriminated union instead of being dropped), `Plumb.plumb_mark`,
  `LREntry.amount` with parsed `amount_value` and `amount_currency`,
  `LREntry.style_class` and `description_text`, `ParcelPart.part_type`,
  `building_right` and `last_change_log_file_num`, typed `LRUnitParcel.parcel_parts`
  and `possession_sheets`, `SheetAParcelList.source_key` (`lrParcels` or
  `cadParcels`), `LandRegistryUnit.reference_shape`, `ParcelInfo.lr_reference_shape`,
  `is_building_parcel` and `parcel_number_display`, and the `LRUnitType` enum.
  Every model that receives server JSON keeps unknown keys in `source_fields`
  (`SourceModel` base) and the client's `unknown_fields` setting (`warn`,
  `ignore`, `error`; `CADASTRAL_API_UNKNOWN_FIELDS`) reports them.
- SDK: the three search endpoints that had no client method. `find_possession_sheet`,
  `find_main_book`, `find_book_of_dc` and `resolve_main_book_id`, with the typed
  `KeyValueSearchResult` hierarchy (`PossessionSheetSearchResult`,
  `MainBookSearchResult`, `BookOfDCSearchResult`; `ParcelSearchResult` and
  `MunicipalitySearchResult` are subclasses now). `get_lr_unit_detailed` accepts
  `main_book_name` instead of the id and reports `main_book_ambiguous` or
  `main_book_not_found`.
- SDK: building parcels. `normalize_parcel_number` maps `35/1.ZGR`, `35/1 ZGR`,
  `zgr. 35/1` and `*35/1` to the API spelling, `display_parcel_number` renders
  `zgr. 35/1`; every parcel lookup applies it, and asking for a land parcel
  when only the building parcel exists reports `only_building_parcel_exists`.
- CLI: `list-main-books` (`glavne-knjige`), `list-books-of-dc` (`kpu`) and
  `search-possession-sheet` (`posjedovni-list`); `get-lr-unit --main-book-name`
  (`--naziv-glavne-knjige`, `-n`/`-ng`). `get-lr-unit --show-owners` prints each
  owner's registration entry (order number, receipt date, diary number); `--all`
  lists the notes registered on individual shares and the secured amount on
  list C entries; the parcel list says whether it comes from the land register
  or the cadastre. `get-parcel` marks building parcels and prints the file of
  the last change per land use. JSON output carries the new fields under the
  keys listed in `output_keys.py`; a `get-parcel` list resolves the land registry
  reference through parcel links too and reports `is_building_parcel`.
- MCP: tools `find_main_book`, `find_book_of_dc` and `find_possession_sheet`;
  `get_lr_unit` accepts `main_book_name`; `detail="ownership"` owner rows carry
  `entry` and the result carries `share_entries` and `sheet_a1_source_key`.
- MCP parity with the SDK and CLI. New tools `list_municipalities` (filter by
  name, cadastral office or department, paged), `get_file_status` (one
  land-registry file by number and institution id, without fetching a unit)
  and `download_municipality_gis` (fetch or refresh a municipality's GIS data
  into the cache and report the parcel count). `get_lr_unit` gains
  `historical_overview`, the per-sheet levels `detail="shares"` (raw list B),
  `detail="parcels"` (list A) and `detail="encumbrances"` (list C), and
  `offset`/`limit` paging over owner rows, top-level shares, parcels or entry
  groups with a `page` block in every response (`owners_limit` stays as a
  synonym of `limit`; in `full` it now counts shares, so a share without
  owners is never skipped), so a unit whose full dump is refused can still be
  read completely in pages; every level names the unit's `institution_id`.
  `find_parcel` takes `max_matches` and returns the complete search response
  under `matches`, also when no single parcel can be chosen (`success: false`
  with the warning in `match_note`). `resolve_municipality` returns the complete
  record (`municipality_id`, `office_id`, `department_id`, `other_matches`)
  with one request instead of listing every municipality.
- Mock server: routes for possession sheet, main book and books-of-DC search;
  the parcel search reproduces the observed prefix, asterisk-wildcard and
  `ZGR` semantics; data sets regenerated from the redacted capture (59 parcels
  of k.o. Savar in all three shapes including six building parcels, all 17
  Savar units and the Split condominium, the real offices list).
- Coverage gate `api/src/cadastral_api/tests/test_api_coverage.py` over 21
  redacted fixtures (`api/src/cadastral_api/tests/fixtures/`), produced by
  `scripts/redact_capture.py` from a raw sample that `scripts/capture_api_sample.py`
  fetches (it refuses to run without an explicit `--base-url`).
- `specs/api-coverage-specification.md`: field-level inventory of every public
  API endpoint from a live capture and the specification for complete coverage
  in the SDK models, client, CLI, MCP server and mock server, including a
  coverage gate test.
- Map link for parcel geometry. `ParcelGeometry.map_url(zoom=19)` and
  `build_map_url()` in the SDK build the interactive-map URL centred on the
  parcel (EPSG:3765 centre, zoom, standard layer set); `ParcelGeometry.to_geojson()`
  returns a GeoJSON Feature whose properties include it. The MCP tool
  `get_parcel_geometry` returns `map_url` in `dict` and `geojson` output and
  accepts a `zoom` argument; `find_parcel` and each successful
  `batch_fetch_parcels` entry return `map_url` too when the municipality's GIS
  data is available (best effort, omitted otherwise). The CLI `get-geometry` command prints the link with
  `--show-stats` and includes `map_url` in `json` and `geojson` output;
  `get-parcel` uses the same builder.
- `specs/gateway-service.md`: specification for a hosted gateway exposing the SDK
  as a REST API and as a remote MCP server (single container, SQLite, no external
  services).
- `docs/sdk-guide.md`, `docs/development-guide.md`, `docs/legal.md`: SDK reference,
  developer setup and release procedure, and the full terms of use, moved out of
  the top-level README.

### Changed

- MCP server: upgraded to MCP Python SDK v2 (`mcp>=2,<3`, protocol revision
  2026-07-28). `FastMCP` is now `MCPServer` and the server reports its own
  version to clients. Tools, resources and prompts are unchanged; 2025-era
  clients such as Claude Desktop keep working. Reinstall with
  `pip install -U -e ./mcp`.
- CLI: `get-parcel` and `get-lr-unit` take a list as well as a single item;
  the separate `batch-fetch` and `batch-lr-unit` commands are gone. `get-parcel`
  accepts several parcel numbers (comma-separated or as separate arguments) or
  `--input FILE` (CSV or JSON, any language), `--detail registry` prints one
  row per parcel with its land registry unit, and `--continue-on-error/--stop-on-error`
  moved over. `get-lr-unit --input FILE` reads a CSV or JSON of units or the
  JSON that `get-parcel` writes for a list (replacing `--from-batch-output`).
  A single parcel number keeps today's output and exit codes; a list gives the
  `summary` plus `results` document, exit code 1 if any item failed, with each
  successful result carrying the single-item record under `full_data` (except
  in `registry` mode). Progress goes to stderr, so `--format json` on stdout
  is clean. The CSV of a list of parcels names the column `possessors` (was
  `owners`); `get-parcel --format yaml`, which never produced YAML, is removed.
  Croatian spellings: `uz čestica "103/2,45" -ko SAVAR --detalji registry`,
  `uz uložak --ulaz parcels.json --sve`.
- MCP: the same merge on the tool surface. `get_parcel` (replaces
  `batch_fetch_parcels`) and `get_lr_unit` (replaces `get_lr_unit`,
  `get_lr_unit_from_parcel` and `batch_lr_units`) each take a list of typed
  references and return one entry per reference, in order, with a `status`.
  A `get_lr_unit` reference is `lr_unit_number` + `main_book_id`, `lr_unit_number`
  + `main_book_name`, or `parcel_number` + `municipality`; units that several
  references resolve to are fetched once (`status: "duplicate"`, `same_unit_as`).
  A single unit that fails, or a `full` dump too large to return, is that entry's
  `error` instead of a tool error. Nine tools instead of eleven. The MCP usage
  guide is rewritten around the register choice and the two tools; the
  `cadastral-lookup` skill follows.
- MCP: `find_main_book`, `find_book_of_dc` and `find_possession_sheet` return
  the named fields only (`main_book_id`, `sheet_number`, ...); the server's raw
  `key1`/`value1`/`key2`/`value2`/`value3`/`display_value1` are no longer
  repeated beside them.
- MCP: `parcel_id` and `lr_unit_number` in tool references accept a number as
  well as a string, so the `data.parcel_id` that `get_parcel` returns can be
  passed back unchanged.
- MCP: the `get_lr_unit` envelope carries a `duplicates` count next to
  `successful` and `failed`, so the three add up to `total`; the tool
  description says so.
- SDK: numeric ids of the search results are integers, as they are in the
  detailed models: `ParcelSearchResult.parcel_id`,
  `PossessionSheetSearchResult.possession_sheet_id`,
  `MainBookSearchResult.institution_id`, `BookOfDCSearchResult.office_id`,
  `MunicipalitySearchResult.municipality_id`, `institution_id` and
  `department_id`, and `CadastralOffice.id`. The municipality registration
  number stays a string (it is a code). CLI JSON and MCP results follow; the
  MCP `parcel_id` reference is an integer (a numeric string is accepted).
- SDK: entry kinds follow the Land Registry Act. `ActionType` gains `uknjižba`
  (unconditional registration, previously folded into the generic `upis`);
  `upis` is now only the fallback for "upisuje se". A deletion is reported by
  the new `LREntry.deletes_prior_entry` flag, and `brisanje` is the kind only
  when the text names no other kind. CLI and MCP `action_type` values change
  accordingly.
- SDK: `ParcelInfo.total_owners` is renamed `total_possessors` (the cadastre
  records possessors, not owners); no alias is kept. CLI JSON key `total_owners` becomes
  `total_possessors` (Croatian `broj_posjednika`, unchanged). The `Possessor`,
  `PossessionSheet` and `ParcelInfo` descriptions no longer say "owner", and
  `cli/tests/test_terminology.py` enforces that.
- SDK: `LRShare.share_status` (`ShareStatus.ACTIVE` for status 0, otherwise
  `HISTORICAL`) replaces the unused enum; `LRUnitParcel.area_numeric` is `None`
  instead of 0 when the area is missing or unparsable. `has_encumbrances()` is
  renamed to what it tests: `EncumbranceSheetC.has_entries()` and
  `LandRegistryUnitDetailed.has_sheet_c_entries()`; the summary key and the CLI
  JSON key `has_encumbrances` become `has_sheet_c_entries` (Croatian
  `ima_upise_u_teretovnici`). No aliases are kept.
- SDK: a parcel without a direct unit whose links name different units raises
  `LR_UNIT_NOT_FOUND` with reason `lr_unit_ambiguous` and the candidates
  instead of silently taking the first; `ParcelInfo.lr_unit_candidates()`
  lists them. The CLI explains the message.
- SDK: share totals (`OwnershipSheetB.total_ownership_accounted`,
  `PossessionSheet.total_ownership`) are summed exactly as fractions
  (`total_ownership_fraction()` returns the `Fraction`) and converted once, so
  three thirds are 1.0.
- Terms of use: the "never use against government systems" wording is replaced
  everywhere (README, `docs/legal.md`, CLAUDE.md, `.env.example`, module
  docstrings, CLI help footers, documentation banner) by "verify that you have
  the rights to use that server and its data first; use at your own risk".
- Documentation: `docs/en/cli/commands/` gains pages for the three new commands;
  `get-lr-unit` and `get-parcel` pages describe the main book name, the entry
  column and building parcels; the glossary gains čestica zgrade, knjiga
  položenih ugovora and upis. Croatian edition regenerated.
- CLI: `get-lr-unit --show-encumbrances` prints, under each list C entry, the
  persons it is registered in favour of (**In favour of** / **U korist**). In
  `json` output each entry is now an object (`order_number`, `description`,
  `beneficiaries`, and `source_fields` with the server's nested data verbatim)
  instead of a plain description string, and each group carries
  `share_order_number`.
- CLI: short option flags now have Croatian spellings as well, two letters taken
  from the Croatian long option (`-bu` for `--broj-uloška`, `-gk` for
  `--glavna-knjiga`, `-vl` for `--vlasnici`, `-ob` for `--oblik`, ...). Croatian
  help and documentation show them; the English single-letter flags keep working
  in every language, like `-ko` did before.
- Top-level README rewritten as a short teaser: three usage examples and a
  capability table linking to the per-command CLI documentation. Stale SDK method
  names, the wrong rate-limit default, and the unimplemented HTTP transport claim
  were removed.
- `api/`, `cli/`, and `mcp/` READMEs trimmed to short pointers into `docs/`.

### Fixed

- MCP: tool and resource failures reach the agent with their message. The MCP
  SDK withholds the text of any exception that is not its own `ToolError` or
  `ResourceError`, and the handlers raised `ValueError`, so every failure
  ("No parcels found ...", "Could not match parcel ... against the building
  areas ...") arrived as the bare "Error executing tool <name>". The server now
  converts them. `get_parcel_zoning` failures name the WFS endpoint(s) tried
  and, when that is the mock server's default path on another server, say to
  set `CADASTRAL_PLANNING_WFS_URLS`.
- MCP: the three resources and the four prompts work again. They called
  `get_parcel_by_id` and `search_municipalities`, which the SDK never had, and
  read `municipality_name`, `cadastral_office_name`, `land_use_name` and
  `land_use`, which `ParcelInfo` does not have, so every parcel resource, the
  municipality resource and every prompt failed at runtime. A test now checks
  each `self.client.<method>` in the MCP sources against the real client.
- SDK: an encumbrance in favour of a legal person no longer comes back without a
  beneficiary. The server sends no person record when the name is written into
  the entry text ("... za korist REPUBLIKE HRVATSKE, Centar za socijalnu skrb
  Zadar"), so `EncumbranceGroup` now reads the name back out of the text when
  `lrOwners` is empty; `beneficiary_source` says whether the beneficiary came
  from the person records (`lr_owners`) or from the text (`description`). CLI
  `get-lr-unit --all` and `batch-lr-unit` print it under "u korist".
- MCP: `find_parcel` no longer passes a prefix match off as the parcel that was
  asked for. Searching "973" in a municipality that has only 973/1 returned
  973/1 with nothing to say the number differed; the response now carries
  `requested_parcel_number` and `exact_match`, plus `match_note` and
  `other_matches` when the match is not exact. `batch_fetch_parcels` carries the
  same warning per entry.
- MCP: `owners_limit` now applies to `detail="full"`, not only to
  `detail="ownership"`. A full dump of a unit with a hundred co-owners ignored
  the cap and overran the caller's context; owner records are capped in both
  views, `total_owners` and `owners_truncated` are reported in both, and a full
  dump still too large to return is refused with the smaller views named.
- SDK: a parcel number with an empty sub-number is no longer sent to the server
  as written. "56/" and "56/.ZGR" normalised to "56/" and "*56/", numbers that
  exist in no cadastral municipality, and the server's substring match answered
  them with 56/1 - a different parcel, in a different land-registry unit. The
  trailing separator is dropped, so they normalise to "56" and "*56".
- MCP: `find_parcel` no longer falls back across the two numbering series. A
  building parcel ("56/.ZGR") that the search cannot find is reported as not
  found instead of being answered with the land parcel 56/1, and a land parcel
  that exists only as a building parcel is answered with the ZGR spelling to
  ask for. `match_note` also distinguishes a number that begins with the
  requested one from a number that merely contains it (the server matches on a
  substring, so "*56/" used to return 256/1 and 656/1 as "prefix matches"), and
  `other_matches` lists only matches of the kind the note describes.
- MCP: `owners_limit` in `detail="full"` now cuts sheet B off at the cap
  instead of only emptying its shares. A condominium keeps its weight in the
  shares themselves - 85 shares with every owner removed still serialise to
  135,000 characters - so the shares past the cap are dropped whole and counted
  in `shares_omitted`. The ceiling for a full dump is lowered to 50,000
  characters, well under a typical client's per-response limit, and the refusal
  names the sheet at fault (an encumbrance sheet that is the bulk cannot be
  helped by `owners_limit`).

- SDK: parcels of a land registry unit (`LRUnitParcel`) no longer invent facts
  for keys the lean `lrParcels` shape does not send. `graphic`, `alpha_numeric`,
  `is_harmonized`, `legal_regime`, `status`, `resource_code`, `building_remark`,
  `has_building_right` and `area` are `None` when absent instead of defaulting
  to true, false or zero; `area_numeric` stays 0 for a missing area.
- SDK: encumbrance entries (teretovnica, list C) no longer lose their
  beneficiaries. The server lists the persons an entry is registered in favour
  of under `lrOwners` (the entry text ends with "u korist:"), which the model
  silently dropped. `LREntry.owners` now types that list; `LREntry`,
  `EncumbranceGroup` and `EncumbranceSheetC` keep any other undeclared field
  (`extra="allow"`, exposed as `LREntry.source_fields`); and
  `LREntry.get_parties()` / `EncumbranceGroup.get_parties()` return the
  beneficiaries as `Party` objects. The MCP `detail="full"` output includes
  them through the model dump. Mock unit 657 now carries a list C with this
  structure, and the API specification documents it.
- SDK: `EncumbranceGroup.right_type` and `EncumbranceGroup.beneficiary` were
  always `null`. They are now derived when the server does not send them:
  `right_type` is parsed from the entry text (`parse_right_type()` in
  `cadastral_api.utils`: pravo plodouživanja → `usufruct`, založno pravo →
  `mortgage`, služnost → `easement`, tražbina → `lien`, zabrana otuđenja →
  `prohibition`, prvokup → `preemption`, zabilježba → `annotation`, anything
  else → `other`) and `beneficiary` is the first person in the entries'
  `lrOwners`. The CLI `get-lr-unit` `json` output carries `right_type` per
  encumbrance group.
- SDK: `LREntry.action_type`, `diary_number`, `entry_date` and `basis_document`
  were always `null`. They are now parsed from the entry text
  (`parse_lr_entry()` in `cadastral_api.utils`): the action (uknjižba → `upis`,
  predbilježba, zabilježba, brisanje), the diary number normalised to
  `Z-487/49`, the receipt date (first date in the text, Croatian month names or
  numeric), the legal basis (the phrase after "Na temelju") and `basis_date`,
  the date inside that phrase. The CLI `get-lr-unit` `json` output carries them
  per entry.
- SDK: a share written into a beneficiary's name (`"... ZA 2/6"`) is no longer
  treated as part of the name. `Party.share` exposes it as `{num, den, decimal}`
  (the shape of a Sheet B `share_fraction`), `name_normalized` drops the suffix
  and the raw `name` is kept. The CLI `get-lr-unit` `json` beneficiaries carry
  `name_normalized` and `share`.
- CLI: `get-geometry` `json`, `geojson` and `csv` output is no longer soft-wrapped
  at the terminal width, which broke lines longer than the window (such as the
  map link) when the output was piped.
- MCP server: `get_parcel_geometry` with `format="geojson"` failed on every
  parcel because the geometry model had no `to_geojson()` method.
- MCP server: `get_parcel_geometry` reports a clear error when the parcel is
  not in the municipality's GIS data instead of failing with
  `'NoneType' object has no attribute 'to_geojson'` (or `model_dump`).
- SDK: the GIS cache records which server each municipality ZIP came from
  (`source.txt` next to the ZIP) and downloads the municipality again when the
  configured API base URL differs or the marker is missing. Synthetic geometry
  downloaded from the mock server can no longer be served to a client configured
  for another server; caches written by earlier versions are refreshed on first
  use.

### Security

- Weekly Dependabot version checks for every project in the monorepo and for
  the GitHub Actions used by the workflows, plus two vulnerability gates: a
  `pip-audit` run over the installed runtime dependencies (on every push and
  pull request, and weekly on its own) and a CodeQL scan of the Python sources.
  Pull requests also get a dependency review that blocks a newly introduced
  vulnerable package.
- Mock server: the pinned `fastapi` and `uvicorn` were old enough to pull in a
  `starlette` with published advisories, and conflicted with the version range
  the MCP server requires. Both pins are now current.

## [0.1.0] - 2026-09-08

Baseline release. Everything the repository contained when release tagging
was introduced.

### Added

- Python SDK (`api/`) with Pydantic V2 models, rate-limited HTTP client,
  GIS geometry parsing from INSPIRE GML files, and a local GIS cache.
- Command-line interface (`cli/`): `search`, `get-parcel`, `get-lr-unit`,
  `batch-fetch`, `batch-lr-unit`, `list-municipalities`, `list-offices`,
  `info`, `get-geometry`, `download-gis`, `cache clear`; table, JSON, CSV,
  WKT and GeoJSON output.
- MCP server (`mcp/`) exposing cadastre and land-registry lookups to AI
  agents over STDIO and HTTP, with bilingual tool descriptions and a routing
  skill.
- Mock API server (`mock-server/`) with sample municipalities, offices,
  parcels, land-registry units and geometry, so the tools can be exercised
  without touching any production system.
- Land-registry unit support: sheets A, B and C, condominiums (etažno
  vlasništvo), plombe with detail resolution, explicit register source
  (cadastre vs. land registry) and a cadastre/land-registry divergence notice.
- Complete Croatian localization of the CLI, including Croatian command and
  option names, with a translation coverage gate.
- Bilingual CLI user documentation (`docs/en/cli/`, `docs/hr/cli/`) generated
  by `scripts/build_docs.py`, with documentation and terminology gates in CI.

[Unreleased]: https://github.com/ssarunic/cadastre/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/ssarunic/cadastre/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/ssarunic/cadastre/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ssarunic/cadastre/releases/tag/v0.1.0
