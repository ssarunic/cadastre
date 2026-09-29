#!/usr/bin/env python3
"""
CLI entry point for the Cadastral MCP server.

Supports two transport modes:
- STDIO: For local integration with Claude Desktop
- HTTP: Streamable HTTP (the MCP SDK's transport) for clients that connect
  to a URL; no authentication, so keep it on the loopback interface
"""

import argparse
import logging
import sys

from mcp.server.mcpserver import MCPServer

from .auth import KeyStore
from .config import config
from .http_server import auth_for, run_http_server
from .server import create_mcp_server

logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point for the MCP server CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "Cadastral MCP Server - Model Context Protocol server for land registry queries"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with STDIO transport (for Claude Desktop)
  %(prog)s --transport stdio

  # Run with HTTP transport on custom port
  %(prog)s --transport http --port 8080

  # The MCP endpoint is then http://127.0.0.1:8080/mcp (health: /health).
  # Access keys: MCP_HTTP_KEYS in .env (bearer header or OAuth login);
  # without keys the server is open and only listens on 127.0.0.1.
  %(prog)s --transport http --host 0.0.0.0 --port 8080

Environment Variables:
  CADASTRAL_API_BASE_URL    API base URL (default: http://localhost:8000)
  CADASTRAL_API_TIMEOUT     Request timeout in seconds (default: 10.0)
  CADASTRAL_API_RATE_LIMIT  Rate limit in seconds (default: 0.75)
  CADASTRAL_LANG            Language: hr, en, de, it (default: hr)
  CADASTRAL_CACHE           Response cache: memory | off (default: memory)
  CADASTRAL_CACHE_MEMORY_MB Byte budget of the memory cache (default: 64)
  MCP_HTTP_HOST             HTTP server host (default: 127.0.0.1)
  MCP_HTTP_PORT             HTTP server port (default: 8080)
  MCP_HTTP_KEYS             Access keys, comma-separated, read from .env on every check
  MCP_HTTP_KEYS_FILE        The .env file to read them from (default: nearest .env)
  MCP_HTTP_PUBLIC_URL       URL clients use (default: http://HOST:PORT), the OAuth issuer
  MCP_HTTP_AUTH_STORE       Issued OAuth tokens (default: <cache dir>/mcp_http_auth.json)

⚠️  This server is an educational demonstration. It connects to the localhost
    mock server by default. Before configuring any other server, verify that
    you have the rights to use it and its data; use at your own risk.
        """,
    )

    parser.add_argument(
        "--transport",
        "-t",
        choices=["stdio", "http"],
        default="stdio",
        help=(
            "Transport mode: stdio (default, for Claude Desktop) or http "
            "(streamable HTTP at /mcp, for clients that connect to a URL)"
        ),
    )

    parser.add_argument(
        "--host",
        default=None,
        help=f"HTTP server host (default: {config.http_host})",
    )

    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=None,
        help=f"HTTP server port (default: {config.http_port})",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"%(prog)s {config.server_version}",
    )

    args = parser.parse_args()

    # Configure logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Override config if provided
    if args.host:
        config.http_host = args.host
    if args.port:
        config.http_port = args.port

    # Create MCP server
    logger.info(f"Starting Cadastral MCP Server v{config.server_version}")
    logger.info(f"Transport: {args.transport}")
    logger.info(f"API Base URL: {config.api_base_url}")

    if args.transport == "stdio":
        run_stdio_server(create_mcp_server())
        return

    keys = KeyStore.default()
    try:
        auth, provider = auth_for(keys, config.http_host, config.public_url())
    except ValueError as e:
        logger.error(str(e))
        sys.exit(2)
    run_http_server(create_mcp_server(auth=auth, auth_server_provider=provider), provider, keys)


def run_stdio_server(mcp_server: MCPServer) -> None:
    """
    Run MCP server with STDIO transport.

    This mode is used for local integration with Claude Desktop
    or other local MCP clients.

    Args:
        mcp_server: The configured MCPServer server instance
    """
    logger.info("Running in STDIO mode (for Claude Desktop integration)")
    logger.info("IMPORTANT: All logs go to stderr, JSON-RPC to stdout")

    try:
        # Run the MCPServer server with STDIO transport
        mcp_server.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
