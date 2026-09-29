# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ DEMO PROJECT: CHECK YOUR RIGHTS BEFORE USING ANOTHER SERVER

**This is a demonstration and educational project showing how cadastral and land registry systems could be connected via modern APIs.** It ships with a mock server, and that is what the defaults, the examples, the tests and the documentation use.

### RULES

1. The default configuration and every example target the included mock server (`http://localhost:8000`)
2. Anyone may point the code at another server, including the Croatian government systems, **after verifying that they have the rights to use that server and its data** (its terms of service, data-protection law). They do so **at their own risk**. When helping with such a setup, remind the user of this once; do not refuse
3. **DO NOT** help bypass authorization, rate limits or terms of service of any server
4. Treat real cadastral and land registry data as sensitive personal data: keep raw captures out of the repository (see `scripts/redact_capture.py`)
5. Say that the project is a demonstration when the context suggests the user takes it for an official tool

### Purpose

This project demonstrates modern API architecture patterns that could be applied to cadastral systems. It includes a **mock server** for safe testing and learning, whose data replicates the shapes of the public API (redacted).

---

## Project Overview

This is a **monorepo** containing multiple related projects demonstrating modern cadastral API architecture patterns:

- **`api/`** - Python SDK with type-safe Pydantic models and GIS integration
- **`cli/`** - Command-line interface with rich formatting and list processing
- **`mcp/`** - Model Context Protocol server for AI agent integration
- **`mock-server/`** - Mock API server for safe testing and development

**⚠️ Important:** This project is an educational demonstration. It includes a localhost mock server for testing. Before using it with any other server, including the Croatian government systems, verify that you have the rights to do so (terms of service, data protection); use at your own risk.

**Mock Test Server (Default):** `http://localhost:8000` (configured via environment variables)
**Other servers:** at your own risk, after verifying your rights (see `docs/legal.md`)

### Key Features

- **Python SDK** (`api/`): Type-safe Pydantic V2 models with full validation, GIS integration
- **CLI Tool** (`cli/`): Rich terminal interface with table/JSON/CSV/WKT/GeoJSON output formats
- **MCP Server** (`mcp/`): AI agent integration via Model Context Protocol
- **GIS Integration**: Parcel geometry parsing and local caching from GML files
- **Spatial plans**: Parcel matched against the building areas derived from the plans in force (`get_parcel_zoning`, `get-zoning`, MCP `get_parcel_zoning`); zones carry designation code, plan, `generation` (old/new code list) and the dataset disclaimer; see [specs/spatial-planning-api-specification.md](specs/spatial-planning-api-specification.md)
- **Lists**: `get-parcel` and `get-lr-unit` accept a list of items (comma-separated or from a file) as well as a single one
- **Internationalization**: Croatian (default) and English support via gettext
- **Rate Limiting**: Automatic request throttling (0.375s default, configurable)
- **Error Handling**: Comprehensive error types with user-friendly messages

## API Integration Architecture

The API follows a three-step workflow for retrieving complete parcel information:

1. **Municipality Lookup** → Get municipality registration number from name
2. **Parcel Search** → Get parcel ID using parcel number + municipality code
3. **Detailed Info** → Retrieve full parcel data including ownership using parcel ID

### Critical API Requirements

- **Required Headers:**
  - `Accept: application/json, text/plain, */*`
  - `User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15`

- **Rate Limiting:** Must wait 0.5-1 seconds between requests
- **Authentication:** None required (public data)
- **Timeout:** Set to 10 seconds minimum

### Key Data Structures

**Municipality Search Response:**

- `key1`: Municipality registration number (required for parcel searches)
- `name`: Short municipality name
- `fullName`: Full official name

**Parcel Search Response:**

- `key1`: Parcel ID (critical - needed for detailed info)
- `parcelNumber`: Confirmed parcel number
- `municipalityName`: Municipality name
- `address`: Parcel location

**Parcel Detailed Info Response:**

- `possessionSheets[]`: Array of ownership records
  - Each sheet contains `possessors[]` with name, ownership fraction, and address
- `parcelParts[]`: Land use classification (Pašnjak/Pasture, Oranica/Arable, Šuma/Forest, etc.)
- `area`: Total area in square meters
- `hasBuildingRight`: Boolean indicating if construction is permitted

**Land Registry Unit (Zemljišnoknjižni uložak) Response:**

- **Sheet A (Popis čestica)**: All parcels included in the land registry unit
  - Parcel numbers, cadastral municipalities, areas
- **Sheet B (Vlasnički list)**: Ownership information
  - Owner names, addresses, ownership shares/fractions
  - Ownership type (e.g., full ownership, co-ownership)
- **Sheet C (Teretni list)**: Encumbrances and charges
  - Mortgages, liens, easements, usage rights
  - Registration dates and amounts

**Condominium Support (Etažno vlasništvo):**

Condominiums (apartment buildings) have a special structure in the land registry:

- **Unit Types**: `lrUnitTypeName` indicates property type:
  - `VLASNIČKI` - Standard ownership
  - `ETAŽNO VLASNIŠTVO S ODREĐENIM OMJERIMA` - Condominium with defined shares
- **Detection**: Use `lr_unit.is_condominium()` method (checks `lrUnitTypeName` for "ETAŽN")
  - ⚠️ The `condominiums` boolean flag is **unreliable** (often `false` for actual condominiums)
- **Ownership Shares**: Each apartment is a separate share with:
  - `condominium_number`: Apartment identifier (e.g., "E-16")
  - `condominium_descriptions`: Detailed apartment info (floor, area, rooms)
- **Nested Co-ownership**: Shared apartments use `subSharesAndEntries` for co-owners
- **Possessor Fields**: `condominiumShareNumber` and `condominiumShareOwnership` for common area shares

## Known Municipality Codes

- SAVAR: `334979`
- LUKA: `334731`

(See [specs/croatian-cadastral-api-specification.md](specs/croatian-cadastral-api-specification.md) for complete API documentation)

## Map Integration

Interactive map URL format:

```text
https://oss.uredjenazemlja.hr/map?cad_parcel_id=PARCELID
```

Coordinate system: EPSG:3765 (HTRS96 / Croatia TM)

## Environment Configuration

The API client can be configured via environment variables or a `.env` file:

**Environment Variables:**

- `CADASTRAL_API_BASE_URL`: API base URL (default: `http://localhost:8000`)
- `CADASTRAL_API_TIMEOUT`: Request timeout in seconds (default: `10.0`); the two whole-record endpoints (`/lr/lr-unit`, `/cad/parcel-info`) wait up to 120 s for the response body (`CadastralAPIClient(long_timeout=...)`), since a large condominium takes the server 20 s or more to assemble
- `CADASTRAL_API_RATE_LIMIT`: Rate limit between requests in seconds (default: `0.375`)
- `CADASTRAL_PLANNING_WFS_URLS`: Building-areas WFS endpoint(s) for `get-zoning`, comma-separated mirrors tried in order (default: `<base URL>/planning/wfs`, the mock server)
- `CADASTRAL_LANG`: Language for CLI output (`hr`, `en`) - Croatian is default

**Setup:**

1. Copy `.env.example` to `.env`
2. Configure the API base URL (defaults to localhost test server)
3. Set another URL only after verifying that you have the rights to use that server; use at your own risk

**Example `.env` file:**

```bash
# Use local test server (default)
CADASTRAL_API_BASE_URL=http://localhost:8000

# Or another server, at your own risk, after verifying your rights to use it
# CADASTRAL_API_BASE_URL=https://oss.uredjenazemlja.hr/oss/public

# Optional: Set language (hr, en)
# CADASTRAL_LANG=hr
```

**Python API Usage:**

```python
from cadastral_api import CadastralAPIClient

# Uses environment variables or defaults to localhost
with CadastralAPIClient() as client:
    offices = client.list_cadastral_offices()

# Override base URL programmatically
with CadastralAPIClient(base_url="http://test-server:9000") as client:
    offices = client.list_cadastral_offices()

# Specify cache directory for GIS data
with CadastralAPIClient(cache_dir="./my_gis_cache") as client:
    geometry = client.get_parcel_geometry("103/2", "334979")

# Get land registry unit from parcel
with CadastralAPIClient() as client:
    lr_unit = client.get_lr_unit_from_parcel("279/6", "334979")
    print(f"Unit: {lr_unit.lr_unit_number}")
    print(f"Owners: {len(lr_unit.ownership_sheet_b.owners)}")
    print(f"Parcels: {len(lr_unit.possessory_sheet_a1.cad_parcels)}")

# Get land registry unit by unit number and main book ID
with CadastralAPIClient() as client:
    lr_unit = client.get_lr_unit_detailed("769", 21277)
    summary = lr_unit.summary()
    print(f"Total area: {summary['total_area_m2']} m²")
    print(f"Number of owners: {summary['num_owners']}")

# Main book by name, entry provenance, share entries
with CadastralAPIClient() as client:
    lr_unit = client.get_lr_unit_detailed("769", main_book_name="SAVAR")
    for share in lr_unit.ownership_sheet_b.lr_unit_shares:
        for owner in share.owners:
            if owner.entry:   # the registration entry that put the owner on the share
                print(owner.name, owner.entry.entry_date, owner.entry.diary_number)
        for note in share.share_entries:   # zabilježbe on this share alone
            print(note.order_number, note.description_text)
    books = client.find_main_book("SAVAR")           # main_book_id 21277, court ZADAR
    sheets = client.find_possession_sheet("363", "334979")

# Working with condominiums (etažno vlasništvo)
with CadastralAPIClient() as client:
    lr_unit = client.get_lr_unit_detailed("13998", 30783)  # Split condominium
    if lr_unit.is_condominium():
        print(f"Condominium with {lr_unit.get_condominium_units_count()} units")
        for share in lr_unit.ownership_sheet_b.lr_unit_shares:
            if share.is_condominium_share():
                print(f"  {share.condominium_number}: {share.get_apartment_description()}")
```

## CLI Features

The project includes a comprehensive command-line interface (`cadastral`) with multiple commands:

### Core Commands

- **`cadastral search`** - Quick parcel search with basic information
- **`cadastral get-parcel`** - Detailed parcel information with possessors; one parcel, a comma-separated list, or a file (`--input`). `--detail registry` gives one row per parcel with its LR unit reference
- **`cadastral get-lr-unit`** - Get land registry unit (zemljišnoknjižni uložak) with ownership, parcels, and encumbrances (`--main-book-name` resolves the main book by name; `--input` reads a list of units from a file or from get-parcel list output)
- **`cadastral list-main-books`** - Find land registry main books (glavne knjige) and their IDs
- **`cadastral list-books-of-dc`** - List books of deposited contracts (knjige položenih ugovora, KPU)
- **`cadastral search-possession-sheet`** - Find a cadastre possession sheet by number
- **`cadastral list-municipalities`** - List and filter municipalities
- **`cadastral list-offices`** - List all cadastral offices
- **`cadastral info`** - Display system information, cache status, and API settings
- **`cadastral get-geometry`** - Retrieve parcel boundary coordinates
- **`cadastral get-zoning`** - What the spatial plans' building areas say about a parcel (inside a settlement, in a detached T2/T3 zone, or outside), with the plan it comes from and the dataset disclaimer
- **`cadastral download-gis`** - Download GIS data for a municipality
- **`cadastral cache clear`** - Clear local GIS cache

### CLI Usage Examples

```bash
# Search for a parcel
cadastral search 103/2 --municipality SAVAR

# Get detailed info with owners
cadastral get-parcel 103/2 -m 334979 --show-owners

# Get land registry unit from parcel
cadastral get-lr-unit --from-parcel 279/6 -m SAVAR --all

# Get land registry unit by unit number and main book ID (or main book name)
cadastral get-lr-unit --unit-number 769 --main-book 21277 --show-owners
cadastral get-lr-unit --unit-number 769 --main-book-name SAVAR --show-owners

# Building parcels: any spelling works (35/1.ZGR, 35/1 ZGR, zgr. 35/1, *35/1)
cadastral get-parcel 35/1.ZGR -m SAVAR

# Land registry books and possession sheets
cadastral list-main-books --search SAVAR
cadastral list-books-of-dc --search ZADAR
cadastral search-possession-sheet 363 -m SAVAR

# A list of parcels: one row per parcel with its LR unit reference
cadastral get-parcel "103/2,45,396/1" --municipality SAVAR --detail registry

# A list from a file
cadastral get-parcel --input parcels.csv --detail registry --format json --output results.json

# Pipeline: parcels → their LR units
cadastral get-parcel "103/2,45,396/1" -m SAVAR --detail registry --format json -o parcels.json
cadastral get-lr-unit --input parcels.json --all

# A list of LR units from a CSV
cadastral get-lr-unit --input lr_units.csv --show-owners

# Get parcel geometry in WKT format
cadastral get-geometry 103/2 -m 334979 --format wkt

# Get geometry as GeoJSON
cadastral get-geometry 103/2 -m 334979 --format geojson --output parcel.json

# List cadastral offices
cadastral list-offices

# Download GIS data for municipality
cadastral download-gis 334979 --output ./gis_data

# Change language
cadastral search 103/2 -m SAVAR --lang en
```

### Output Formats

All commands support multiple output formats:
- **table** - Rich formatted tables (default for terminal)
- **json** - JSON output
- **csv** - CSV format
- **wkt** - Well-Known Text (geometry commands)
- **geojson** - GeoJSON format (geometry commands)

### Internationalization

The CLI supports multiple languages via the `--lang` flag or `CADASTRAL_LANG` environment variable:

- **Croatian (hr)** - Default language
- **English (en)** - Full English translation

Language selection priority:
1. `--lang` CLI flag
2. `CADASTRAL_LANG` environment variable
3. System locale
4. Default: Croatian

**Note:** Command names and JSON keys remain in English (standard practice), only user-facing text is localized.

## GIS Integration

The project includes robust GIS data handling:

### GIS Cache System

- **Local caching** of downloaded GML files (default: `~/.cadastral_api_cache`)
- **Automatic downloads** when geometry is requested
- **Cache management** via CLI (`cadastral cache-clear`)
- **Municipality-based** organization

### GML Parser

The `GMLParser` class parses INSPIRE-compliant GML files from the ATOM feed:

```python
from cadastral_api import GMLParser

parser = GMLParser("path/to/katastarske_cestice.gml")

# Get single parcel geometry
geometry = parser.get_parcel_by_number("103/2")

# Get all parcels (memory intensive for large municipalities)
all_parcels = parser.get_all_parcels()
```

### Parcel Geometry

The `ParcelGeometry` model includes:
- **parcel_number**: Cadastral parcel number
- **coordinates**: List of Coordinate objects (EPSG:3765)
- **area**: Calculated area in m²
- **centroid**: Calculated center point
- **bounds**: Bounding box (min/max lat/lon)
- **to_wkt()**: Export to Well-Known Text format
- **to_geojson()**: Export to GeoJSON format

### API Method

```python
with CadastralAPIClient() as client:
    # Automatically downloads and caches GML if not present
    geometry = client.get_parcel_geometry("103/2", "334979")

    print(f"Area: {geometry.area} m²")
    print(f"Centroid: {geometry.centroid}")
    print(f"WKT: {geometry.to_wkt()}")
```

## Lists of Parcels and Units

`get-parcel` and `get-lr-unit` take one item or a list; there are no separate
batch commands. A single parcel number gives the single-item output (one JSON
object, fail fast). A comma-separated list, several positional arguments or
`--input FILE` give the list output: a `summary` (counts) and `results` (one
record per item with `status`, the item's summary fields and, unless
`--detail registry`, its `full_data`). Failures are recorded per item and the
exit code is 1 if any item failed; `--stop-on-error` aborts at the first one.

```bash
# Comma-separated list, one row per parcel with its LR unit reference
cadastral get-parcel "103/2,45,396/1" -m SAVAR --detail registry

# From CSV or JSON file
cadastral get-parcel --input parcels.csv --detail registry --format json -o results.json

# Stop on first error (default is to continue)
cadastral get-parcel --input parcels.csv --stop-on-error

# Full parcel details for each item
cadastral get-parcel "103/2,45" -m SAVAR --show-owners

# Pipeline: parcels → LR units (ownership and encumbrances)
cadastral get-parcel "103/2,45,396/1" -m SAVAR --detail registry --format json -o parcels.json
cadastral get-lr-unit --input parcels.json --show-owners

# Direct LR unit list (CSV with lr_unit_number,main_book_id)
cadastral get-lr-unit --input lr_units.csv --format json -o lr_results.json
```

`get-lr-unit --input` accepts a CSV or JSON with `lr_unit_number` and
`main_book_id`, or the JSON that `get-parcel` writes for a list (it takes the
`lr_unit_number` and `main_book_id` of every successful result and reads each
unit once).

### Input File Formats

**Parcel CSV format:**

```csv
parcel_number,municipality
103/2,334979
45,SAVAR
396/1,334979
```

**Parcel JSON format:**

```json
[
  {"parcel_number": "103/2", "municipality": "334979"},
  {"parcel_number": "45", "municipality": "SAVAR"},
  {"parcel_id": "direct_parcel_id_if_known"}
]
```

**LR Unit CSV format (for get-lr-unit --input):**

```csv
lr_unit_number,main_book_id
769,21277
123,45678
```

**LR Unit JSON format (for get-lr-unit --input):**

```json
[
  {"lr_unit_number": "769", "main_book_id": 21277},
  {"lr_unit_number": "123", "main_book_id": 45678}
]
```

### Python List Processing

```python
from cadastral_api import CadastralAPIClient
from cadastral_cli.input_parsers import ParcelInput
from cadastral_cli.list_processing import process_parcel_list

inputs = [
    ParcelInput(parcel_number="103/2", municipality="334979"),
    ParcelInput(parcel_number="45", municipality="SAVAR"),
]

with CadastralAPIClient() as client:
    summary = process_parcel_list(client, inputs, continue_on_error=True)

for result in summary.results:
    if result.ok:
        print(f"✓ {result.data.parcel_number}")
    else:
        print(f"✗ Error: {result.error_message}")
```

## Monorepo Structure

**Note:** This repository has been refactored to a monorepo structure. See [specs/refactoring-todo.md](specs/refactoring-todo.md) for the migration checklist.

### Target Structure (Monorepo)

```text
cadastre/
├── api/                          # Python SDK project
│   ├── src/cadastral_api/
│   │   ├── client/              # HTTP client with rate limiting
│   │   │   └── api_client.py
│   │   ├── models/              # Pydantic data models
│   │   │   ├── entities.py      # Core business entities
│   │   │   └── gis_entities.py  # GIS geometry models
│   │   ├── gis/                 # GIS functionality
│   │   │   ├── parser.py        # GML file parser
│   │   │   └── cache.py         # Local GIS cache
│   │   ├── locale/              # Compiled translations
│   │   ├── exceptions.py        # Custom exceptions
│   │   └── i18n.py              # Internationalization
│   ├── tests/unit/              # Unit tests
│   ├── tests/integration/       # Integration tests
│   ├── examples/                # Usage examples
│   ├── docs/                    # API-specific documentation
│   └── pyproject.toml
│
├── cli/                          # CLI application project
│   ├── src/cadastral_cli/
│   │   ├── main.py              # CLI entry point
│   │   ├── commands/            # Command modules
│   │   │   ├── search.py        # search, search-municipality
│   │   │   ├── parcel.py        # get-parcel (one parcel or a list)
│   │   │   ├── registry.py      # get-lr-unit (one unit or a list)
│   │   │   ├── discovery.py     # list-offices, list-municipalities, info
│   │   │   ├── gis.py           # get-geometry, download-gis
│   │   │   └── cache.py         # cache-clear
│   │   ├── formatters.py        # Output formatting
│   │   ├── input_parsers.py     # Input parsing (lists, --input files)
│   │   ├── list_processing.py   # List lookups (per-item results)
│   │   └── lr_unit_output.py    # Shared LR unit output formatting
│   ├── tests/                   # CLI tests
│   ├── docs/                    # CLI documentation
│   └── pyproject.toml
│
├── mcp/                          # MCP server project
│   ├── src/cadastral_mcp/
│   │   ├── server.py            # MCP server
│   │   ├── tools.py             # MCP tools
│   │   ├── resources.py         # MCP resources
│   │   ├── prompts.py           # MCP prompts
│   │   └── http_server.py       # HTTP transport
│   ├── tests/                   # MCP tests
│   ├── docs/                    # MCP documentation
│   └── pyproject.toml
│
├── mock-server/                  # Mock API server
│   ├── src/main.py              # FastAPI server
│   ├── data/                    # Test data
│   │   ├── municipalities.json
│   │   ├── offices.json
│   │   └── parcels/
│   ├── docs/                    # Mock server docs
│   └── requirements.txt
│
├── docs/                         # Repository-wide documentation
│   ├── architecture.md          # Overall architecture
│   ├── contributing.md          # Contribution guide
│   └── development-guide.md     # Dev setup
│
├── scripts/                      # Repository-wide scripts
│   ├── compile_translations.sh
│   ├── generate_pot.sh
│   └── update_translations.sh
│
├── po/                           # Translation source files (shared)
│   ├── cadastral.pot
│   ├── hr.po
│   └── en.po
│
├── README.md                     # Main repository README
├── CLAUDE.md                     # This file
├── .env.example                  # Environment variables template
└── pyproject.toml                # Legacy (for reference)
```

## Development Guidelines

### Naming Conventions

**IMPORTANT:** All new code must follow the naming conventions in [specs/naming-conventions.md](specs/naming-conventions.md):

- **Top-level projects**: `kebab-case/` (e.g., `api/`, `mock-server/`)
- **Python packages**: `snake_case/` (e.g., `cadastral_api/`, `cadastral_cli/`)
- **Python modules**: `snake_case.py` (e.g., `api_client.py`)
- **Documentation**: `kebab-case.md` or `UPPERCASE.md` (e.g., `api-reference.md`, `README.md`)
- **Test files**: `test_<module>.py` (e.g., `test_api_client.py`)

### Adding New Features

1. **Models**: Use Pydantic V2 with strict validation
2. **Type hints**: Required on all functions (Python 3.12+ syntax)
3. **CLI commands**: Keep command/option names in English
4. **Localization**: Wrap user-facing strings in `_()` from `i18n` module
5. **Error handling**: Use typed exceptions from `exceptions.py`
6. **Testing**: Add tests for new features
7. **File naming**: Follow [specs/naming-conventions.md](specs/naming-conventions.md)
8. **CLI documentation**: Any change to a CLI command (new, changed, or removed) must update the user docs in the same commit, following [specs/documentation-guide.md](specs/documentation-guide.md)
9. **Changelog**: Any user-visible change (SDK, CLI, MCP server) gets a bullet under `[Unreleased]` in `CHANGELOG.md` in the same commit; see [specs/release-process.md](specs/release-process.md)
9. **Croatian command and option names**: every command, long option, positional argument and word-like choice value needs an entry in `cli/src/cadastral_cli/localized.py` and a translation in `po/hr.po` (naming convention in [specs/terminology.md](specs/terminology.md) section 4); `cd cli && pytest tests/test_localized_cli.py` enforces it. English names stay canonical; the Croatian program name is `uz`
10. **Output field names**: every JSON key or CSV column the CLI emits needs an entry in `cli/src/cadastral_cli/output_keys.py` and a Croatian spelling in `po/hr.po` (ASCII snake_case, [specs/terminology.md](specs/terminology.md) section 5). Output goes through `print_output`, which localizes keys; input parsers accept any language via `canonical_keys`. The MCP server uses the SDK models directly, so its JSON is always English; anything that reuses the CLI formatters and needs English must run with `--lang en` or `CADASTRAL_LANG=en`. `cd cli && pytest tests/test_output_keys.py` enforces it

### Documentation Style

**Emoji usage in documentation:**
- **User docs** (`docs/`, READMEs): Emojis are acceptable for visual clarity
- **Technical specs** (`specs/`): No emojis - keep specs formal and technical

### Internationalization Workflow

When adding user-facing text:

```python
from ...i18n import _, ngettext, pgettext

# Simple translation
print(_("Parcel not found"))

# Plural forms
msg = ngettext("{n} parcel", "{n} parcels", count)

# Context-specific (when same word has different meanings)
label = pgettext("table_header", "Name")
```

After adding strings:

```bash
# Extract strings to template
./scripts/generate_pot.sh

# Update translation files
./scripts/update_translations.sh

# Edit po/hr.po, po/en.po with translations

# Compile translations
./scripts/compile_translations.sh
```

### Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=cadastral_api

# Type checking
mypy src/cadastral_api

# Linting
ruff check src/

# Translation coverage gate (run before every release)
cd cli && pytest tests/test_i18n_coverage.py

# Documentation gate (needs the mock server dependencies; rebuild first with python scripts/build_docs.py)
cd cli && pytest tests/test_docs_coverage.py

# Release consistency gate (version strings + CHANGELOG)
cd cli && pytest tests/test_release_consistency.py
```

### Releases

Releases are occasional (after a major feature or an important bug fix), not
scheduled. The whole monorepo shares one version number, written in seven
files and kept identical by `scripts/release.py`. Each release is an annotated
tag `vX.Y.Z` on `main` whose message is the matching `CHANGELOG.md` section;
pushing the tag creates a GitHub Release. Full rules: [specs/release-process.md](specs/release-process.md).

```bash
scripts/release.py 0.2.0 --dry-run   # preview: versions, changelog, commit, tag
scripts/release.py 0.2.0             # do it (never pushes)
git push origin main v0.2.0
```

Never edit the version strings by hand and never move or delete a tag; fix a
bad release with a new PATCH release.

## Documentation

### User Documentation

- **[README.md](README.md)** - Main repository README
- **[docs/](docs/)** - User guides and documentation
  - **[docs/en/cli/](docs/en/cli/)** - CLI user documentation (English source; tutorial, one page per command, glossary, errors, install)
  - **[docs/hr/cli/](docs/hr/cli/)** - Croatian edition, generated by `python scripts/build_docs.py` (never edit by hand)
  - **[docs/sdk-guide.md](docs/sdk-guide.md)** - Python SDK guide
  - **[docs/mcp-usage-guide.md](docs/mcp-usage-guide.md)** - MCP server usage guide
  - **[docs/development-guide.md](docs/development-guide.md)** - Setup, checks, releases
  - **[docs/legal.md](docs/legal.md)** - Terms of use

### Project READMEs

- **[api/README.md](api/README.md)** - Python SDK documentation
- **[cli/README.md](cli/README.md)** - CLI application documentation
- **[mcp/README.md](mcp/README.md)** - MCP server documentation
- **[mock-server/README.md](mock-server/README.md)** - Mock server documentation

### Technical Specifications (specs/)

[specs/README.md](specs/README.md) is the index: status and keywords for every document. A new or renamed spec gets a row there in the same commit; `cd cli && pytest tests/test_specs_index.py` enforces it.

- **[specs/croatian-cadastral-api-specification.md](specs/croatian-cadastral-api-specification.md)** - Complete API specification
- **[specs/api-coverage-specification.md](specs/api-coverage-specification.md)** - Field inventory of every endpoint and the plan for complete coverage (models, client, CLI, MCP, mock, coverage gate)
- **[specs/spatial-planning-api-specification.md](specs/spatial-planning-api-specification.md)** - Spatial-plan data sources (ISPU raster WMS, building-areas WFS, regional services, catalogues), the new-generation plan model and the parcel-matching recipe (section 3, the building-areas WFS, is implemented as `get-zoning`)
- **[specs/web-map-exploration.md](specs/web-map-exploration.md)** - Web map front end exploration: open base-map and imagery sources and licences, map libraries, Google Maps assessment, recommended stack (research, not implemented)
- **[specs/parcel-locator-specification.md](specs/parcel-locator-specification.md)** - Parcel by address and by point: DGU INSPIRE Addresses and Cadastral Parcels WFS, Zagreb ArcGIS DKP, lookup recipes and terms (research, not implemented)
- **[specs/pydantic-entities-implementation.md](specs/pydantic-entities-implementation.md)** - Pydantic models specification
- **[specs/mcp-server.md](specs/mcp-server.md)** - MCP server architecture
- **[specs/gateway-service.md](specs/gateway-service.md)** - Hosted REST + remote MCP gateway service (draft)
- **[specs/naming-conventions.md](specs/naming-conventions.md)** - File and folder naming standards
- **[specs/i18n-guide.md](specs/i18n-guide.md)** - Internationalization developer guide
- **[specs/terminology.md](specs/terminology.md)** - Croatian legal and cadastral vocabulary the CLI and docs must use; enforced by `cli/tests/test_terminology.py`
- **[specs/documentation-guide.md](specs/documentation-guide.md)** - CLI user documentation guide (audience, page template, generated vs authored, Croatian edition, update procedure)
- **[specs/release-process.md](specs/release-process.md)** - Versioning, release tags, changelog and the release gate
- **[specs/i18n-status.md](specs/i18n-status.md)** - i18n implementation status
- **[specs/refactoring-todo.md](specs/refactoring-todo.md)** - Monorepo refactoring checklist

### Examples

- **[api/examples/basic_usage.py](api/examples/basic_usage.py)** - Basic SDK usage
- **[api/examples/municipality_search.py](api/examples/municipality_search.py)** - Municipality search
- **[api/examples/gis_parcel_geometry.py](api/examples/gis_parcel_geometry.py)** - GIS geometry examples
- **[api/examples/lr_unit_example.py](api/examples/lr_unit_example.py)** - Land registry unit examples

### AI Assistant

- **[CLAUDE.md](CLAUDE.md)** - This file (AI assistant instructions)

## Related Services

- **WFS INSPIRE Service:** `https://api.uredjenazemlja.hr/services/inspire/cp/wfs` - Download cadastral geometries (WFS 2.0, GML/GeoJSON); the old `oss.uredjenazemlja.hr/wfs` address no longer serves a WFS
- **ATOM Download Service:** Bulk municipality data downloads via catalog.uredjenazemlja.hr
- **Interactive Map:** `https://oss.uredjenazemlja.hr/map?cad_parcel_id=PARCELID` - View parcels on map

## Important Notes

### Python Version

Requires Python 3.12+ for modern type hint syntax (`str | None`, `list[T]`, etc.)

### Data Inconsistencies

Based on live API testing:
- **Ownership fractions are optional** - Many parcels don't include the `ownership` field
- **Area is string type** - API returns area as string, automatically converted in models
- **Multiple possession sheets** - A single parcel can have multiple ownership records

### Translation Status

The CLI is fully localized (Croatian and English), including option help,
command help, output, error messages and click's own messages. The
authoritative status is the output of `cd cli && pytest tests/test_i18n_coverage.py`
(see [specs/i18n-status.md](specs/i18n-status.md)). Rules that keep it that way:
- Command descriptions go through `help=command_help(_("""..."""))`, never the
  docstring; option help through `help=_("...")`
- `from cadastral_api.i18n import _` is safe at module level: `_` delegates to
  the active catalog, so `--lang` works after import
- Croatian strings use the vocabulary in [specs/terminology.md](specs/terminology.md)
  (posjednik not vlasnik for the cadastre, prijedlog not prijava, način uporabe not
  namjena); `cd cli && pytest tests/test_terminology.py` rejects the listed terms
- After changing strings run `./scripts/generate_pot.sh`,
  `./scripts/update_translations.sh`, translate `po/hr.po`, then
  `./scripts/compile_translations.sh`; the gate fails otherwise
- The MCP server is intentionally not localized (its text is read by an AI agent)
