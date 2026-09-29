"""Configuration for the MCP server."""

import os
from dataclasses import dataclass
from pathlib import Path

from cadastral_api import CadastralAPIClient
from cadastral_api.gis import GISCache


@dataclass
class MCPConfig:
    """Configuration for the Cadastral MCP server."""

    # API Configuration (the SDK reads the CADASTRAL_API_* variables and
    # owns the defaults; importing it loads the .env file first)
    api_base_url: str = CadastralAPIClient.BASE_URL
    api_timeout: float = CadastralAPIClient.DEFAULT_TIMEOUT
    api_rate_limit: float = CadastralAPIClient.DEFAULT_RATE_LIMIT

    # Language Configuration
    language: str = os.getenv("CADASTRAL_LANG", "hr")

    # Cache Configuration
    cache_dir: Path = Path(os.getenv("CADASTRAL_CACHE_DIR", str(GISCache.DEFAULT_CACHE_DIR)))
    # Response cache backend (memory | off); None leaves the SDK to read CADASTRAL_CACHE
    cache: str | None = os.getenv("CADASTRAL_CACHE")

    # MCP Server Configuration
    server_name: str = "cadastral-mcp-server"
    server_version: str = "0.3.0"

    # HTTP transport (--transport http): interface and port to listen on.
    # Without MCP_HTTP_KEYS the server is open, so it only listens on loopback.
    http_host: str = os.getenv("MCP_HTTP_HOST", "127.0.0.1")
    http_port: int = int(os.getenv("MCP_HTTP_PORT", "8080"))
    # The URL clients reach the server at (issuer of the OAuth tokens, base of
    # the login page): the HTTPS proxy's address when there is one.
    http_public_url: str | None = os.getenv("MCP_HTTP_PUBLIC_URL")
    # Registered OAuth clients and issued tokens, so a restart keeps sessions.
    http_auth_store: Path = Path(
        os.getenv("MCP_HTTP_AUTH_STORE", str(cache_dir / "mcp_http_auth.json"))
    )

    def public_url(self) -> str:
        return (self.http_public_url or f"http://{self.http_host}:{self.http_port}").rstrip("/")

    def __post_init__(self) -> None:
        """Ensure cache directory exists."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)


# Global config instance
config = MCPConfig()
