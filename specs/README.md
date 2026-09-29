# Technical Specifications

Index of the specifications, standards and research notes in this directory.
Each entry gives the document's status and the keywords it covers so that a
grep over this file finds the right document. Keep the table current: a new
or renamed specification gets a row here in the same commit.

Status values: `reference` (describes something that exists and is kept
current), `standard` (rules the code and docs must follow, usually enforced by
a test), `implemented` (a plan that has been carried out and is kept for the
rationale), `partial` (some of it is built), `draft` (a proposal, nothing
built), `research` (findings and options, nothing built), `historical` (kept
for the record, may be stale).

## Index

| Document | Status | What it covers | Keywords |
|---|---|---|---|
| [croatian-cadastral-api-specification.md](croatian-cadastral-api-specification.md) | reference | Every public OSS endpoint with request and response shapes, headers, rate limits, the three-step parcel workflow | OSS API, endpoints, key1, posjedovni list, zk uložak, sheet A B C, condominium, etažno, WFS, ATOM, map URL |
| [api-coverage-specification.md](api-coverage-specification.md) | implemented | Field-level inventory of every endpoint and the changes that gave complete model, client, CLI, MCP and mock coverage; redacted fixtures | coverage, fixtures, redaction, capture, mock data, entries, lrEntry, KPU, file status, plomba |
| [spatial-planning-api-specification.md](spatial-planning-api-specification.md) | partial | Spatial-plan data sources: county plan-sheet WMS, nationwide building-areas WFS, regional services, ISPU internal API, eKatalog, NIPP catalogues, new-generation plan model, parcel-matching recipe. Section 3 is implemented as `get_parcel_zoning` and `get-zoning` | prostorni plan, građevinsko područje, namjena, ISPU, MGIPU, GeoServer, WMS, WFS, CQL, EPSG:3765, zoning, T1 T2 T3, PPUO, GUP, UPU, Pravilnik NN 152/2023 |
| [parcel-locator-specification.md](parcel-locator-specification.md) | research | Finding a parcel by address or by point: DGU INSPIRE Addresses and Cadastral Parcels WFS, cadastral-zoning lookup for the k.o. number, Zagreb ArcGIS DKP layers, lookup recipes, result model, terms of use, implementation plan | address, adresa, kućni broj, point, koordinate, EPSG:3765, WGS84, INSPIRE, ad:AD.Address, cp:CadastralParcel, CadastralZoning, arcportal.zagreb.hr, DKP, RPJ, find_parcel_by_address, find_parcel_by_point |
| [web-map-exploration.md](web-map-exploration.md) | research | A web page that shows parcels on a map and queries a drawn area: base-map and imagery sources and their licences, map libraries, Google Maps assessment, recommended stack, open items | web map, OpenLayers, MapLibre, Leaflet, OpenFreeMap, Protomaps, OpenStreetMap, ODbL, DGU DOF, ortofoto, satellite, Google Maps, draw area, spatial index, STRtree |
| [sale-blockers-specification.md](sale-blockers-specification.md) | implemented | What is registered against a land-registry unit that bears on a sale, read into typed blockers with severity, scope and a screening verdict; the inferred owner flags (likely deceased, address abroad, public body); the classification table, the scope and cancellation rules, where each surface shows them | sale blockers, zapreke prodaji, teret, plomba, hipoteka, spor, ovrha, prvokup, služnost, verdict, likely_deceased, address_abroad, public_body, condominium scope, detect_blockers, owner_flags, --blockers |
| [ko-wide-scan-decision.md](ko-wide-scan-decision.md) | draft | Whether to read every parcel of a cadastral municipality to answer the possession-sheet and person-search questions the API cannot: cost, terms of service, personal data, options and a pending decision | k.o.-wide scan, posjedovni list, person search, rate limit, personal data, legal basis, decision memo |
| [response-cache-specification.md](response-cache-specification.md) | partial | Cache of upstream responses in the SDK client: one interface, memory, memory plus disk, Redis or Valkey and cluster backends; keys, data classes and lifetimes, personal-data policy, CLI, MCP and gateway surfaces; wire budget for MCP results and result artifacts read in increments (tool, resource, gateway URL) | cache, response cache, TTL, cachetools, diskcache, Redis, Valkey, memcached, CADASTRAL_CACHE, refresh, fetched_at, 1 MB, structuredContent, wire budget, read_result, result artifact, paging |
| [gateway-service.md](gateway-service.md) | draft | Hosted REST plus remote MCP service exposing the SDK: architecture, REST conventions, OAuth, caching, deployment phases | gateway, REST, remote MCP, FastAPI, API keys, OAuth 2.1, cache, deployment |
| [mcp-server.md](mcp-server.md) | reference | MCP server architecture, tools, resources, prompts, transports, configuration for AI clients | MCP, tools, resources, prompts, stdio, HTTP, Claude Desktop, claude.ai |
| [mcp-client-efficiency.md](mcp-client-efficiency.md) | partial | Reducing MCP round trips and token use: source register, list tools, detail levels, limits | MCP, efficiency, tokens, source, owners_limit, detail, batching |
| [pydantic-entities-implementation.md](pydantic-entities-implementation.md) | reference | Pydantic V2 models for every API entity, validation rules, aliases, helper methods | Pydantic, models, entities, aliases, validation, ParcelInfo, LRUnit, PossessionSheet |
| [lr-unit-implementation-plan.md](lr-unit-implementation-plan.md) | implemented | Original plan for land-registry unit support: models for sheets A, B, C, client method, CLI command | zemljišnoknjižni uložak, LR unit, main book, glavna knjiga, sheet A B C, owners, encumbrances |
| [naming-conventions.md](naming-conventions.md) | standard | File, directory, package, module, test and document naming across the monorepo | naming, kebab-case, snake_case, monorepo layout |
| [terminology.md](terminology.md) | standard | Croatian legal and cadastral vocabulary the CLI and docs must use; forbidden terms; Croatian command, option and output-key naming. Enforced by `cli/tests/test_terminology.py` | terminologija, posjednik, vlasnik, prijedlog, način uporabe, Croatian option names, output keys, uz |
| [documentation-guide.md](documentation-guide.md) | standard | How the CLI user documentation is written: audience, page template, generated vs authored parts, Croatian edition, update procedure. Enforced by `cli/tests/test_docs_coverage.py` | docs, CLI documentation, build_docs.py, docs-hr.po, generated pages, tutorial, glossary |
| [documentation-structure.md](documentation-structure.md) | historical | Directory layout of the documentation at the time of the monorepo refactoring; some paths have since moved | docs layout, README locations |
| [release-process.md](release-process.md) | standard | Versioning, the seven version strings, annotated tags, changelog format, release script and gate. Enforced by `cli/tests/test_release_consistency.py` | release, version, tag, CHANGELOG, release.py, semver |
| [i18n-guide.md](i18n-guide.md) | standard | Adding and translating user-facing strings: gettext, `_()`, plural and context forms, po workflow, localized command names | i18n, gettext, po, pot, hr.po, translation, ngettext, pgettext, localized.py |
| [i18n-status.md](i18n-status.md) | reference | What is localized and how the coverage gate verifies it | i18n status, coverage gate, test_i18n_coverage |
| [localization_example.py](localization_example.py) | reference | Code example accompanying the i18n guide | i18n example |
| [linting-guide.md](linting-guide.md) | standard | Ruff, mypy and pylint setup, configuration and rationale | lint, ruff, mypy, pylint, code quality |
| [quick-lint-reference.md](quick-lint-reference.md) | reference | One-line commands to run the linters | lint commands |
| [pylint-setup-summary.md](pylint-setup-summary.md) | historical | What the pylint integration changed when it was added | pylint |
| [refactoring-todo.md](refactoring-todo.md) | historical | Checklist of the monorepo refactoring, completed | refactoring, monorepo migration |

## Find by Topic

- **Calling the government APIs, response shapes, field meanings:**
  croatian-cadastral-api-specification, api-coverage-specification, pydantic-entities-implementation
- **Land registry (zemljišne knjige), sheets A/B/C, condominiums:**
  croatian-cadastral-api-specification, lr-unit-implementation-plan, pydantic-entities-implementation
- **Spatial plans, building areas, zoning, WMS and WFS services:**
  spatial-planning-api-specification, web-map-exploration
- **Maps, geometry, imagery, web front end:**
  web-map-exploration, spatial-planning-api-specification (section 9), croatian-cadastral-api-specification (WFS, ATOM), parcel-locator-specification
- **MCP server and AI clients:** mcp-server, mcp-client-efficiency, gateway-service
- **Hosting and deployment:** gateway-service, response-cache-specification
- **Caching and response size:** response-cache-specification, mcp-client-efficiency
- **Croatian wording, command and output names:** terminology, i18n-guide
- **Translations and the po workflow:** i18n-guide, i18n-status, localization_example.py
- **CLI user documentation:** documentation-guide
- **Releases and versions:** release-process
- **Code style and naming:** naming-conventions, linting-guide, quick-lint-reference

## Conventions for This Directory

- File names are `kebab-case.md` ([naming-conventions.md](naming-conventions.md)).
- No emojis; specifications are formal and technical.
- A document states its status near the top and a date for any finding that
  can go stale (endpoint behaviour, licences, prices).
- Any service other than the mock server is documented with the reminder to
  verify the right to use it; see `docs/legal.md`.
