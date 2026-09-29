# File & Folder Naming Conventions

This document defines the official naming conventions for the Cadastre monorepo. **All new code and files must follow these conventions.**

---

## Repository Structure Philosophy

This is a **monorepo** containing multiple related projects:
- **`api/`** - Python SDK for cadastral API access
- **`cli/`** - Command-line interface application
- **`mcp/`** - Model Context Protocol server for AI agents
- **`mock-server/`** - Mock API server for testing

Each project is **self-contained** with its own `src/`, `tests/`, `docs/`, etc.

Shared repository-level resources go in the root.

---

## 1. Top-Level Directory Structure

```text
cadastre/
├── api/                    # Python SDK project
│   ├── src/
│   ├── tests/
│   ├── docs/              # API-specific docs
│   ├── examples/
│   └── pyproject.toml
│
├── cli/                    # CLI application project
│   ├── src/
│   ├── tests/
│   ├── docs/              # CLI-specific docs
│   └── pyproject.toml
│
├── mcp/                    # MCP server project
│   ├── src/
│   ├── tests/
│   ├── docs/              # MCP-specific docs
│   └── pyproject.toml
│
├── mock-server/            # Mock API server
│   ├── src/
│   ├── data/              # Test data for mock server
│   ├── docs/
│   └── requirements.txt
│
├── docs/                   # Repository-wide documentation
│   ├── architecture.md
│   ├── contributing.md
│   └── development-guide.md
│
├── scripts/                # Repository-wide scripts
│   └── setup_dev_env.sh
│
├── .github/                # GitHub configuration
├── README.md               # Repository root README
├── CLAUDE.md               # AI assistant instructions
├── NAMING_CONVENTIONS.md   # This file
└── REFACTORING_TODO.md     # Refactoring checklist
```

---

## 2. Naming Conventions by Item Type

### Top-Level Project Directories

**Convention: `kebab-case/` (lowercase with hyphens)**

- ✅ `api/` - Single word OK
- ✅ `cli/` - Single word OK
- ✅ `mcp/` - Acronym single word OK
- ✅ `mock-server/` - Multi-word uses kebab-case
- ✅ `integration-tests/` - Multi-word uses kebab-case
- ❌ `mock_server/` - Don't use snake_case for top-level projects
- ❌ `MockServer/` - Don't use PascalCase

**Rationale**: Top-level projects are language-agnostic. Kebab-case is universal across languages and ecosystems.

### Standard Subdirectories (within each project)

**Convention: `lowercase/` (single word preferred)**

Every project can have:
- ✅ `src/` - Source code
- ✅ `tests/` - Test files
- ✅ `docs/` - Project-specific documentation
- ✅ `examples/` - Example code/usage
- ✅ `data/` - Data files (if needed)
- ✅ `scripts/` - Project-specific scripts
- ✅ `config/` - Configuration files

### Python Package Names (inside `src/`)

**Convention: `snake_case/`**

- ✅ `src/cadastral_api/` - Python package uses snake_case
- ✅ `src/cadastral_cli/` - Python package uses snake_case
- ✅ `src/cadastral_mcp/` - Python package uses snake_case
- ❌ `src/cadastral-api/` - Hyphens not allowed in Python

**Why different from top-level?**
- Python requires importable names (no hyphens allowed)
- Top-level directories are not imported, so can use kebab-case
- This is a standard monorepo pattern

### Python Module Files

**Convention: `snake_case.py`**

- ✅ `api_client.py`
- ✅ `batch_processor.py`
- ✅ `gis_parser.py`
- ❌ `apiClient.py` - No camelCase
- ❌ `api-client.py` - No kebab-case in Python

### Test Files

**Convention: `test_<module_name>.py`**

- ✅ `test_api_client.py`
- ✅ `test_batch_processor.py`
- ✅ `test_integration.py`

### Documentation Files

**Convention:**
- **Standard docs**: `UPPERCASE.md` (README, CHANGELOG, etc.)
- **Multi-word docs**: `kebab-case.md`

Examples:
- ✅ `README.md` - Standard (uppercase)
- ✅ `CHANGELOG.md` - Standard (uppercase)
- ✅ `CLAUDE.md` - Standard (uppercase)
- ✅ `api-specification.md` - Multi-word (kebab-case)
- ✅ `i18n-guide.md` - Multi-word (kebab-case)
- ✅ `pydantic-entities-implementation.md` - Multi-word (kebab-case)
- ❌ `I18N_GUIDE.md` - No underscores
- ❌ `Pydantic_Business_Entities.md` - No mixed case with underscores

### Configuration Files

Follow standard conventions for configuration files:

- ✅ `pyproject.toml` - Python standard
- ✅ `requirements.txt` - Python standard
- ✅ `.env` - Standard config
- ✅ `.env.example` - Standard config
- ✅ `.gitignore` - Standard config
- ✅ `settings.json` - JSON config
- ✅ `launch.json` - JSON config

### Data Files

**Convention: `snake_case.ext` or numeric IDs**

- ✅ `municipalities.json`
- ✅ `cadastral_offices.json`
- ✅ `334979.json` - Numeric ID OK
- ✅ `batch_parcels.csv`

### Script Files

**Convention: `snake_case.sh` or `kebab-case.sh`**

- ✅ `setup_dev_env.sh` - snake_case
- ✅ `compile-translations.sh` - kebab-case
- Either is acceptable, be consistent within a directory

---

## 3. Python Code Naming (Internal to Python projects)

### Classes
**Convention: `PascalCase`**
- ✅ `CadastralAPIClient`
- ✅ `ParcelInfo`
- ✅ `GMLParser`

### Functions & Methods
**Convention: `snake_case`**
- ✅ `get_parcel_info()`
- ✅ `search_municipality()`

### Variables
**Convention: `snake_case`**
- ✅ `parcel_number`
- ✅ `api_client`

### Constants
**Convention: `UPPER_SNAKE_CASE`**
- ✅ `DEFAULT_TIMEOUT`
- ✅ `API_BASE_URL`

### Private Members
**Convention: `_snake_case`**
- ✅ `_internal_cache`
- ✅ `_validate_response()`

---

## 4. Acronyms and Abbreviations

### In Directory Names (top-level projects)
- ✅ `api/` - Lowercase
- ✅ `cli/` - Lowercase
- ✅ `mcp/` - Lowercase

### In Python Package Names
- ✅ `cadastral_api/` - Lowercase with underscore
- ✅ `cadastral_cli/` - Lowercase with underscore

### In Python Class Names
- ✅ `APIClient` - Uppercase acronym
- ✅ `GMLParser` - Uppercase acronym
- ✅ `GISCache` - Uppercase acronym

### In Python File Names
- ✅ `api_client.py` - Lowercase with underscore
- ✅ `gis_parser.py` - Lowercase with underscore

---

## 5. Singular vs Plural

### Use Plural

When directory contains **multiple items of the same type**:

- ✅ `tests/` - Multiple test files
- ✅ `examples/` - Multiple example files
- ✅ `docs/` - Multiple documentation files
- ✅ `scripts/` - Multiple script files
- ✅ `models/` - Multiple model files
- ✅ `commands/` - Multiple command files

### Use Singular

When directory represents **a category or single concept**:
- ✅ `src/` - Source code (category)
- ✅ `data/` - Data (category)
- ✅ `config/` - Configuration (category)
- ✅ `client/` - Single client module
- ✅ `gis/` - GIS domain (category)

---

## 6. Project-Specific Structure Examples

### API Project (`api/`)

```text
api/
├── src/
│   └── cadastral_api/          # Python package (snake_case)
│       ├── __init__.py
│       ├── client/
│       │   └── api_client.py   # Module (snake_case)
│       ├── models/
│       │   ├── entities.py
│       │   └── gis_entities.py
│       └── gis/
│           ├── parser.py
│           └── cache.py
├── tests/
│   ├── unit/
│   │   ├── test_api_client.py
│   │   └── test_models.py
│   └── integration/
│       └── test_full_workflow.py
├── docs/
│   ├── README.md
│   ├── api-reference.md
│   └── pydantic-models.md
├── examples/
│   ├── basic_usage.py
│   └── advanced_usage.py
└── pyproject.toml
```

### CLI Project (`cli/`)

```text
cli/
├── src/
│   └── cadastral_cli/          # Python package (snake_case)
│       ├── __init__.py
│       ├── main.py
│       ├── formatters.py
│       └── commands/
│           ├── search.py
│           ├── batch.py
│           └── parcel.py
├── tests/
│   └── test_cli_commands.py
├── docs/
│   ├── README.md
│   └── command-reference.md
└── pyproject.toml
```

### MCP Project (`mcp/`)

```text
mcp/
├── src/
│   └── cadastral_mcp/          # Python package (snake_case)
│       ├── __init__.py
│       ├── server.py
│       ├── tools.py
│       └── resources.py
├── tests/
│   └── test_mcp_server.py
├── docs/
│   ├── README.md
│   └── mcp-protocol.md
└── pyproject.toml
```

### Mock Server (`mock-server/`)

```text
mock-server/
├── src/
│   └── main.py                # FastAPI application
├── data/                       # Test data
│   ├── municipalities.json
│   └── parcels/
│       ├── 334979.json
│       └── 334731.json
├── docs/
│   ├── README.md
│   └── QUICKSTART.md
└── requirements.txt
```

### Repository Root

```text
cadastre/
├── api/                        # API project
├── cli/                        # CLI project
├── mcp/                        # MCP project
├── mock-server/                # Mock server
│
├── docs/                       # Repo-wide documentation
│   ├── README.md              # Docs index
│   ├── architecture.md        # Overall architecture
│   ├── contributing.md        # Contribution guide
│   └── development-guide.md   # Dev setup
│
├── scripts/                    # Repo-wide scripts
│   ├── setup_all.sh           # Setup all projects
│   └── run_all_tests.sh       # Run all tests
│
├── .github/                    # GitHub config
│   └── workflows/
│       └── ci.yml
│
├── README.md                   # Main repository README
├── CLAUDE.md                   # AI assistant instructions
├── NAMING_CONVENTIONS.md       # This file
├── REFACTORING_TODO.md         # Refactoring tasks
└── .gitignore                  # Git ignore patterns
```

---

## 7. Documentation Placement Rules

### Repository-Level Docs (in root `docs/`)
Documentation that covers **multiple projects** or **overall architecture**:
- Architecture diagrams
- Development environment setup
- Contributing guidelines
- API specification (if shared)
- Internationalization guide (if shared)

### Project-Level Docs (in `{project}/docs/`)
Documentation **specific to one project**:
- Project-specific README
- CLI command reference (in `cli/docs/`)
- API library usage (in `api/docs/`)
- MCP protocol details (in `mcp/docs/`)

### When in Doubt

- If it mentions multiple projects → root `docs/`
- If it's specific to one project → `{project}/docs/`
- If it's for end users → `{project}/docs/`
- If it's for contributors → root `docs/`

---

## 8. Quick Reference Table

| Item | Convention | Example |
|------|------------|---------|
| Top-level project dir | `kebab-case/` | `api/`, `mock-server/` |
| Standard subdir | `lowercase/` | `src/`, `tests/`, `docs/` |
| Python package | `snake_case/` | `cadastral_api/` |
| Python module | `snake_case.py` | `api_client.py` |
| Python class | `PascalCase` | `CadastralAPIClient` |
| Python function | `snake_case` | `get_parcel_info()` |
| Python constant | `UPPER_SNAKE_CASE` | `DEFAULT_TIMEOUT` |
| Test file | `test_<name>.py` | `test_api_client.py` |
| Standard doc | `UPPERCASE.md` | `README.md`, `CHANGELOG.md` |
| Multi-word doc | `kebab-case.md` | `api-specification.md` |
| Config file | `lowercase` | `pyproject.toml`, `.env` |
| Data file | `snake_case.ext` | `municipalities.json` |
| Script file | `snake_case.sh` | `setup_env.sh` |

---

## 9. Migration Rules

When refactoring existing code to monorepo structure:

1. **Preserve Python package names** - `cadastral_api` stays as-is (Python requirement)
2. **Use kebab-case for new top-level projects** - Even if source uses snake_case
3. **Move project-specific docs** - From root `docs/` to `{project}/docs/`
4. **Keep shared docs at root** - Architecture, contributing, etc.
5. **Update imports** - Only if package structure changes
6. **Use `git mv`** - Preserve Git history when moving files

---

## 10. For New Code

**Creating a new project:**
1. Use kebab-case for project directory name: `new-project/`
2. Create standard subdirectories: `src/`, `tests/`, `docs/`
3. Python package inside `src/` uses snake_case: `src/new_package/`

**Adding to existing project:**
1. Follow conventions already established in that project
2. Check this guide if creating new file types
3. Be consistent with sibling files

---

**Document Version:** 1.0
**Last Updated:** 2025-01-14
