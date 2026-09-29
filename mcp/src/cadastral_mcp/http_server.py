"""Streamable HTTP transport for the MCP server.

The transport is the MCP Python SDK's own: one ``POST /mcp`` endpoint,
stateless (no session to keep, so the process restarts cleanly and sits
behind any reverse proxy), JSON responses (no event stream to hold open).
Claude Desktop, claude.ai custom connectors, Claude Code and the MCP
Inspector speak it.

Access is controlled by the keys in ``.env`` (``cadastral_mcp.auth``): a
bearer header or the OAuth login. Without keys the server is open, which is
acceptable on the loopback interface only; ``run_http_server`` refuses to
listen anywhere else without keys.
"""

import ipaddress
import logging
from typing import Any
from urllib.parse import urlparse

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

from .auth import AuthStore, KeyAuthProvider, KeyStore, build_auth_settings
from .config import config

logger = logging.getLogger(__name__)

#: Where the MCP endpoint is mounted; the URL a client is given ends in this.
MCP_PATH = "/mcp"


def is_loopback(host: str) -> bool:
    """Whether ``host`` names the loopback interface (127.0.0.1, ::1, localhost)."""
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def auth_for(keys: KeyStore, host: str, public_url: str) -> tuple[Any, Any]:
    """``(auth settings, provider)`` for the keys, or ``(None, None)`` when there are none.

    Raises:
        ValueError: no keys and ``host`` is not the loopback interface; an
            open server may not listen where others can reach it.
    """
    if keys.configured():
        provider = KeyAuthProvider(keys, AuthStore(config.http_auth_store), public_url)
        return build_auth_settings(public_url, MCP_PATH), provider
    if not is_loopback(host):
        raise ValueError(
            f"No access keys ({KEYS_HINT}) and host {host!r} is not the loopback interface: "
            "everyone who could reach the port could read what the server serves. "
            "Set MCP_HTTP_KEYS or listen on 127.0.0.1."
        )
    return None, None


KEYS_HINT = "MCP_HTTP_KEYS in .env"


LOCAL_HOSTS = ["127.0.0.1:*", "localhost:*", "[::1]:*"]


def transport_security(host: str, public_url: str) -> TransportSecuritySettings | None:
    """DNS-rebinding protection: on loopback, only local ``Host`` headers and the public one.

    The SDK turns the protection on for a loopback listener and accepts local
    hosts only; behind a reverse proxy the requests carry the public
    hostname, so that one is allowed as well. None on any other interface
    (the SDK's default there: no protection).
    """
    if not is_loopback(host):
        return None
    public = urlparse(public_url)
    hosts, origins = list(LOCAL_HOSTS), [f"http://{h}" for h in LOCAL_HOSTS]
    if public.hostname and public.hostname not in ("127.0.0.1", "localhost", "::1"):
        # With and without a port: the SDK matches "name:*" only against "name:port".
        hosts += [public.hostname, f"{public.hostname}:*"]
        origins += [f"{public.scheme}://{public.hostname}", f"{public.scheme}://{public.hostname}:*"]
    return TransportSecuritySettings(allowed_hosts=hosts, allowed_origins=origins)


def create_http_app(
    mcp_server: MCPServer,
    host: str | None = None,
    provider: KeyAuthProvider | None = None,
    public_url: str | None = None,
) -> Starlette:
    """The ASGI application: the MCP endpoint at ``/mcp``, ``GET /health``, the login page.

    Args:
        mcp_server: The configured server (``create_mcp_server()``), built
            with the auth settings that go with ``provider``.
        host: The interface the app will listen on; on the loopback interface
            the SDK adds DNS-rebinding protection (only local ``Host`` and
            ``Origin`` headers are accepted, and the public URL's).
        provider: The key provider, whose login page is added to the app.
        public_url: The URL clients use (``MCP_HTTP_PUBLIC_URL``), whose host
            a reverse proxy forwards in the ``Host`` header.
    """
    host = host or config.http_host
    public_url = public_url or config.public_url()
    if provider is not None:
        provider.add_routes(mcp_server)

    @mcp_server.custom_route("/health", methods=["GET"])  # type: ignore[misc]
    async def health(_request: Request) -> JSONResponse:
        body: dict[str, Any] = {
            "status": "ok",
            "server": config.server_name,
            "version": config.server_version,
            "api_base_url": config.api_base_url,
            "mcp_path": MCP_PATH,
        }
        return JSONResponse(body)

    return mcp_server.streamable_http_app(
        streamable_http_path=MCP_PATH,
        json_response=True,
        stateless_http=True,
        host=host,
        transport_security=transport_security(host, public_url),
    )


def run_http_server(
    mcp_server: MCPServer, provider: KeyAuthProvider | None, keys: KeyStore
) -> None:
    """Serve ``create_http_app`` with uvicorn on ``config.http_host:config.http_port``."""
    import uvicorn

    host, port = config.http_host, config.http_port
    if provider is None:
        logger.warning(
            "No access keys in %s: the server is open to everyone who can reach it. "
            "Keys added later take effect after a restart.",
            keys.describe(),
        )
    else:
        logger.info(
            "Access keys from %s; OAuth issuer %s", provider.keys.describe(), provider.public_url
        )
    app = create_http_app(mcp_server, host, provider, config.public_url())
    logger.info("MCP endpoint: http://%s:%d%s (health: /health)", host, port, MCP_PATH)
    uvicorn.run(app, host=host, port=port, log_level="info")
