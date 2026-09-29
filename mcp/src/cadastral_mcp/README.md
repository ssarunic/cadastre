# Cadastral MCP Server

Model Context Protocol (MCP) server for querying Croatian cadastral and land registry data.

## Quick Start

### Installation

```bash
pip install -e .
```

### Run with STDIO (Claude Desktop)

```bash
cadastral-mcp --transport stdio
```

### Run over HTTP (clients that connect to a URL)

```bash
cadastral-mcp --transport http --port 8080
# MCP endpoint: http://127.0.0.1:8080/mcp, health: /health; no authentication
```

## Documentation

See [docs/mcp-usage-guide.md](../../../docs/mcp-usage-guide.md) for complete documentation including:

- Setup and configuration
- Claude Desktop integration
- HTTP deployment
- Available tools, resources, and prompts
- Example interactions
- Development guide

## ⚠️ Important

This MCP server is an **educational demonstration**. It connects to `http://localhost:8000` (mock server) by default. Before configuring any other server, including the Croatian government systems, verify that you have the rights to use it and its data; you do so at your own risk (see `docs/legal.md`).

## Architecture

The server exposes three MCP primitive types:

### Resources (Read-only data)
- `cadastral://parcel/{id}` - Parcel details
- `cadastral://municipality/{code}` - Municipality info
- `cadastral://office/{code}` - Office info

### Tools (AI-invoked actions)
- `find_parcel` - Find one parcel (id, exact-match check, map link)
- `get_parcel` - Cadastre record of one or more parcels (list of references)
- `get_lr_unit` - One or more land registry units, by unit number or by parcel
- `resolve_municipality` - Name to code resolution
- `get_parcel_geometry` - Boundary coordinates
- `list_cadastral_offices` - List offices
- `find_main_book`, `find_book_of_dc`, `find_possession_sheet` - Registry lookups

### Prompts (User templates)
- `explain_ownership_structure` - Ownership analysis
- `property_report` - Comprehensive report
- `compare_parcels` - Multi-parcel comparison
- `land_use_summary` - Land use analysis

## Configuration

Via environment variables:

```bash
CADASTRAL_API_BASE_URL=http://localhost:8000  # API URL
CADASTRAL_LANG=hr                              # Language
MCP_HTTP_HOST=127.0.0.1                        # HTTP transport: interface (loopback)
MCP_HTTP_PORT=8080                             # HTTP transport: port
```

## Project Structure

```text
src/cadastral_mcp/
├── config.py         # Configuration
├── server.py         # Main MCPServer instance
├── resources.py      # Resource handlers
├── tools.py          # Tool handlers
├── prompts.py        # Prompt templates
├── http_server.py    # Streamable HTTP transport (the SDK's) and /health
└── main.py           # CLI entry point
```

## License

Educational/demonstration purposes only.
