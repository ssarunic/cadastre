# Development Guide

How to set up a development environment, run the checks, and cut a release.

## Layout

The repository is a monorepo with four installable projects that share one version
number:

| Directory | Package | What it is |
|---|---|---|
| `api/` | `cadastral_api` | Python SDK: HTTP client, Pydantic models, GIS parsing |
| `cli/` | `cadastral_cli` | The `cadastral` / `uz` command-line tool |
| `mcp/` | `cadastral_mcp` | Model Context Protocol server for AI assistants |
| `mock-server/` | | FastAPI mock of the upstream API, used by every test and example |

Repository-wide material lives in `docs/` (user documentation), `specs/` (technical
specifications), `po/` (translation sources), and `scripts/` (build and release
tooling). Naming rules are in [specs/naming-conventions.md](../specs/naming-conventions.md).

## Setup

```bash
git clone https://github.com/ssarunic/cadastre.git
cd cadastre
python3 -m venv .venv && source .venv/bin/activate
pip install -e "./api[dev]" -e "./cli[dev]" -e "./mcp[dev]"
pip install -r mock-server/requirements.txt
```

Start the mock server in its own terminal whenever you run anything end to end:

```bash
python mock-server/src/main.py
```

## Checks

```bash
# Tests (SDK, CLI, MCP)
pytest api cli mcp

# Tests with coverage for the SDK
pytest api --cov=cadastral_api

# Type checking
mypy api/src/cadastral_api

# Linting
ruff check api/src cli/src mcp/src
```

Linting conventions and the pylint configuration are described in
[specs/linting-guide.md](../specs/linting-guide.md) and
[specs/quick-lint-reference.md](../specs/quick-lint-reference.md).

## Translations

User-facing strings are wrapped in `_()` from the `i18n` module. After adding or
changing strings:

```bash
./scripts/generate_pot.sh        # extract to po/cadastral.pot
./scripts/update_translations.sh # merge into po/hr.po and po/en.po
# edit the .po files
./scripts/compile_translations.sh
```

Details are in [specs/i18n-guide.md](../specs/i18n-guide.md).

## CLI documentation

The English CLI pages under `docs/en/cli/` are the source. The Croatian edition
under `docs/hr/cli/` and all command output samples are generated:

```bash
python scripts/build_docs.py
```

Never edit generated regions or anything under `docs/hr/` by hand. The rules, the
page template, and the procedure to follow when a command changes are in
[specs/documentation-guide.md](../specs/documentation-guide.md).

## Releases

Releases are occasional, cut after a major feature or an important fix, and marked
by an annotated git tag `vX.Y.Z` on `main`. All four projects share the version
number. Changes are listed in [CHANGELOG.md](../CHANGELOG.md); the full procedure
is in [specs/release-process.md](../specs/release-process.md).

```bash
# Describe the change under [Unreleased] in CHANGELOG.md, then:
scripts/release.py 0.2.0 --dry-run   # preview
scripts/release.py 0.2.0             # bump versions, date the changelog, rebuild docs, commit, tag
git push origin main v0.2.0
```

## Where things are specified

- Upstream API shape: [specs/croatian-cadastral-api-specification.md](../specs/croatian-cadastral-api-specification.md)
- Pydantic models: [specs/pydantic-entities-implementation.md](../specs/pydantic-entities-implementation.md)
- MCP server: [specs/mcp-server.md](../specs/mcp-server.md)
- Planned hosted gateway (REST and remote MCP): [specs/gateway-service.md](../specs/gateway-service.md)
