# cadastral_mcp: MCP server

Model Context Protocol server that lets Claude Desktop and other MCP clients look
up parcels, owners, land registry units, encumbrances, and geometry.

```bash
pip install -e ./api -e ./mcp
cadastral-mcp --transport stdio
```

Claude Desktop configuration and a tool-by-tool guide:
[docs/mcp-usage-guide.md](../docs/mcp-usage-guide.md). Architecture:
[specs/mcp-server.md](../specs/mcp-server.md).

`cadastral-mcp --transport http` serves the same tools over streamable HTTP at
`http://127.0.0.1:8080/mcp` for clients that connect to a URL. Access keys in
`.env` (`MCP_HTTP_KEYS`) open it, as a bearer header (Claude Code, Codex, the
MCP Inspector) or through the built-in OAuth login (claude.ai connectors,
ChatGPT, behind an HTTPS proxy); removing a key from the file revokes it.
Without keys the server is open and listens on loopback only. See the
[usage guide](../docs/mcp-usage-guide.md#running-over-http). A hosted service
with real accounts is specified in
[specs/gateway-service.md](../specs/gateway-service.md).

Runs against the included mock server only; see [docs/legal.md](../docs/legal.md).
