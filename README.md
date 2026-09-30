# Croatian Cadastral API Client

Read the cadastre, the land registry and the spatial plans from a terminal, from
Python, or from an AI assistant. Look up a parcel, see who owns it, read the land
registry unit with its encumbrances and pending entries, check whether the parcel
lies in a building area, and export parcel boundaries for GIS tools.

> **Demonstration project with practice data.** This repository shows how a modern
> cadastral API could work. It ships with a mock server, and every example here runs
> against it. Before pointing it at any other server, including the official Croatian
> cadastre, land registry and spatial-plan services, verify that you have the rights
> to use that server and its data (terms of service, data protection). You do so at
> your own risk. Full terms in [docs/legal.md](docs/legal.md).

Requires Python 3.12 or newer.

## See it work

**From the terminal.** One line from a parcel number to owners, parcels,
encumbrances, and pending entries (plombe):

```bash
cadastral get-lr-unit --from-parcel 103/2 -m SAVAR --all --plombe-detail
```

The same program answers to `uz` with Croatian command names, so
`uz čestica 103/2 -ko SAVAR` works too. Output samples are on the
[get-lr-unit page](docs/en/cli/commands/get-lr-unit.md).

**From Python.**

```python
from cadastral_api import CadastralAPIClient

with CadastralAPIClient() as client:
    unit = client.get_lr_unit_from_parcel("103/2", "SAVAR")
    for owner in unit.get_all_owners():
        print(owner.name)
    if unit.has_pending_plombe():
        print("A change is pending on this unit")
```

**From Claude Desktop.** Add the MCP server to `claude_desktop_config.json` and
ask in plain language: "Who owns parcel 103/2 in SAVAR, and are there any
encumbrances?"

```json
{
  "mcpServers": {
    "cadastral": {
      "command": "cadastral-mcp",
      "args": ["--transport", "stdio"],
      "env": { "CADASTRAL_API_BASE_URL": "http://localhost:8000" }
    }
  }
}
```

## What you can do

| Task | CLI | Read more |
|---|---|---|
| Find a parcel and its basic data | `cadastral search` | [search](docs/en/cli/commands/search.md) |
| Everything the cadastre holds, with possessors | `cadastral get-parcel --show-owners` | [get-parcel](docs/en/cli/commands/get-parcel.md) |
| Land registry unit: owners, parcels, encumbrances | `cadastral get-lr-unit --all` | [get-lr-unit](docs/en/cli/commands/get-lr-unit.md) |
| Pending entries (plombe), resolved to what each one is about | `--plombe-detail` | [get-lr-unit](docs/en/cli/commands/get-lr-unit.md) |
| Condominiums (etažno vlasništvo), unit by unit | `cadastral get-lr-unit --show-owners` | [glossary](docs/en/cli/glossary.md) |
| Is the cadastre in step with the land registry? | shown on every parcel and unit | [get-parcel](docs/en/cli/commands/get-parcel.md) |
| Many parcels, then many units, in one pipeline | `cadastral get-parcel --detail registry`, `get-lr-unit --input` | [get-parcel](docs/en/cli/commands/get-parcel.md), [get-lr-unit](docs/en/cli/commands/get-lr-unit.md) |
| Parcel boundaries as WKT or GeoJSON, offline GIS download | `cadastral get-geometry`, `download-gis` | [get-geometry](docs/en/cli/commands/get-geometry.md) |
| Spatial plans: is the parcel in a building area, of what kind (tourist zone, settlement) | `cadastral get-zoning` | [get-zoning](docs/en/cli/commands/get-zoning.md) |
| Table, JSON, or CSV output, in Croatian or English | `--format`, `--lang` | [complete reference](docs/en/cli/reference.md) |

Everything the CLI does is also available as Python calls and as MCP tools.

## Get started

```bash
git clone https://github.com/ssarunic/cadastre.git
cd cadastre
python3 -m venv .venv && source .venv/bin/activate
pip install -e ./api -e ./cli -e ./mcp
pip install -r mock-server/requirements.txt

# terminal 1: the practice server
python mock-server/src/main.py

# terminal 2: your first query
cadastral search 103/2 -m SAVAR
```

The full installation page, written for the person setting this up for
someone else, is at [docs/en/cli/install.md](docs/en/cli/install.md).

## Documentation

| For | Start at |
|---|---|
| Using the CLI (English) | [Start here](docs/en/cli/start-here.md), then the [complete reference](docs/en/cli/reference.md) |
| Korištenje alata (hrvatski) | [Vodič za početak](docs/hr/cli/start-here.md), zatim [sve naredbe](docs/hr/cli/reference.md) |
| Using the Python SDK | [SDK guide](docs/sdk-guide.md) |
| Using the MCP server with Claude | [MCP usage guide](docs/mcp-usage-guide.md) |
| Running the mock server | [mock-server/README.md](mock-server/README.md) |
| Developing and releasing | [Development guide](docs/development-guide.md), [CHANGELOG](CHANGELOG.md) |
| Architecture and specifications | [specs/](specs/README.md) |

## License

MIT. Use only with the included mock server; see [docs/legal.md](docs/legal.md).
