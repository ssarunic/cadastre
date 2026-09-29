"""Access keys in ``.env``: bearer header, OAuth login, revocation by editing the file.

The server runs with two keys in a ``.env`` file. A call without a key is
refused, a call with a key served, and once the key is removed from the file
the next call is refused, without a restart. The OAuth flow is walked with
the SDK's own client: registration, the login page, the code exchange, the
tool call with the issued token, and the refresh that fails once the key
behind the session is gone.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import httpx2
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "api" / "src"))
sys.path.insert(0, str(REPO / "mcp" / "src"))

from cadastral_api import CadastralAPIClient  # noqa: E402
from mcp.client.auth import OAuthClientProvider, TokenStorage  # noqa: E402
from mcp.client.session import ClientSession  # noqa: E402
from mcp.client.streamable_http import streamable_http_client  # noqa: E402
from mcp.shared.auth import (  # noqa: E402
    AuthorizationCodeResult,
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthToken,
)

from cadastral_mcp import auth, http_server, server  # noqa: E402

FIXTURES = REPO / "api" / "src" / "cadastral_api" / "tests" / "fixtures"
KEY_A = "11111111-aaaa-4aaa-8aaa-111111111111"
KEY_B = "22222222-bbbb-4bbb-8bbb-222222222222"
CALLBACK = "http://localhost:3030/callback"


def _write_keys(env_file: Path, *keys: str) -> None:
    env_file.write_text(f"OTHER=1\nMCP_HTTP_KEYS={','.join(keys)}\n", encoding="utf-8")


@pytest.fixture
def env_file(tmp_path) -> Path:
    path = tmp_path / ".env"
    _write_keys(path, KEY_A, KEY_B)
    return path


@pytest.fixture
def secured(monkeypatch, tmp_path, env_file, run_server) -> tuple[str, auth.KeyAuthProvider]:
    """A running server that requires one of the keys in ``env_file``."""

    def serve(request: httpx.Request) -> httpx.Response:
        body = json.loads((FIXTURES / "municipalities_savar.json").read_text("utf-8"))
        return httpx.Response(200, json=body)

    def make_client(**kwargs):
        kwargs.update(rate_limit=0, cache="off", cache_dir=tmp_path)
        client = CadastralAPIClient(**kwargs)
        client.client = httpx.Client(base_url="http://mock", transport=httpx.MockTransport(serve))
        return client

    monkeypatch.setattr(server, "CadastralAPIClient", make_client)
    providers: list[auth.KeyAuthProvider] = []

    def build(base_url: str):
        keys = auth.KeyStore(env_file)
        provider = auth.KeyAuthProvider(keys, auth.AuthStore(tmp_path / "auth.json"), base_url)
        providers.append(provider)
        mcp = server.create_mcp_server(
            auth=auth.build_auth_settings(base_url, http_server.MCP_PATH),
            auth_server_provider=provider,
        )
        return http_server.create_http_app(mcp, "127.0.0.1", provider, "https://mcp.example")

    base_url = run_server(build)
    return base_url, providers[0]


async def _call(url: str, http_client: httpx2.AsyncClient | None) -> str:
    """resolve_municipality over the transport; the municipality code it returns."""
    async with streamable_http_client(url, http_client=http_client) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("resolve_municipality", {"name_or_code": "SAVAR"})
            assert not result.is_error, result.content
            return result.structured_content["code"]


def _bearer(key: str) -> httpx2.AsyncClient:
    return httpx2.AsyncClient(headers={"Authorization": f"Bearer {key}"})


# -- bearer keys ---------------------------------------------------------------


def test_no_key_is_refused(secured) -> None:
    base_url, _ = secured
    response = httpx.post(f"{base_url}/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "ping"})
    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Bearer")


def test_wrong_key_is_refused(secured) -> None:
    base_url, _ = secured
    response = httpx.post(
        f"{base_url}/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
        headers={"Authorization": "Bearer not-a-key"},
    )
    assert response.status_code == 401


def test_health_stays_public(secured) -> None:
    base_url, _ = secured
    assert httpx.get(f"{base_url}/health").status_code == 200


def test_key_in_header_is_served(secured) -> None:
    base_url, _ = secured
    assert asyncio.run(_call(f"{base_url}/mcp", _bearer(KEY_A))) == "334979"


def test_removing_a_key_from_the_file_revokes_it(secured, env_file) -> None:
    base_url, _ = secured
    assert asyncio.run(_call(f"{base_url}/mcp", _bearer(KEY_A))) == "334979"
    _write_keys(env_file, KEY_B)
    with pytest.raises(Exception):
        asyncio.run(_call(f"{base_url}/mcp", _bearer(KEY_A)))
    assert asyncio.run(_call(f"{base_url}/mcp", _bearer(KEY_B))) == "334979"


# -- OAuth -----------------------------------------------------------------------


class _Memory(TokenStorage):
    def __init__(self) -> None:
        self.tokens: OAuthToken | None = None
        self.client_info: OAuthClientInformationFull | None = None

    async def get_tokens(self) -> OAuthToken | None:
        return self.tokens

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self.tokens = tokens

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        return self.client_info

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self.client_info = client_info


def _login(authorize_url: str, key: str, seen: dict[str, int]) -> dict[str, list[str]]:
    """Follow the authorize redirect to the login page, submit the key; the callback query.

    ``seen["login_status"]`` records the login page's answer to the key.
    """
    with httpx.Client(follow_redirects=False) as browser:
        to_login = browser.get(authorize_url)
        assert to_login.status_code == 302, to_login.text
        login_url = to_login.headers["location"]
        assert "/login?txn=" in login_url
        page = browser.get(login_url)
        assert page.status_code == 200 and "Access key" in page.text
        txn = parse_qs(urlparse(login_url).query)["txn"][0]
        done = browser.post(f"{login_url.split('/login')[0]}/login", data={"txn": txn, "key": key})
        seen["login_status"] = done.status_code
        assert done.status_code == 302, done.text
        location = done.headers["location"]
        assert location.startswith(CALLBACK)
        return parse_qs(urlparse(location).query)


def _oauth_client(
    base_url: str, key: str, storage: _Memory, seen: dict[str, int] | None = None
) -> httpx2.AsyncClient:
    callback: dict[str, list[str]] = {}
    seen = {} if seen is None else seen

    async def redirect_handler(url: str) -> None:
        callback.update(await asyncio.to_thread(_login, url, key, seen))

    async def callback_handler() -> AuthorizationCodeResult:
        return AuthorizationCodeResult(
            code=callback["code"][0], state=callback.get("state", [None])[0]
        )

    provider = OAuthClientProvider(
        server_url=f"{base_url}/mcp",
        client_metadata=OAuthClientMetadata(
            client_name="test client",
            redirect_uris=[CALLBACK],
            grant_types=["authorization_code", "refresh_token"],
        ),
        storage=storage,
        redirect_handler=redirect_handler,
        callback_handler=callback_handler,
    )
    return httpx2.AsyncClient(auth=provider)


def test_metadata_is_published(secured) -> None:
    base_url, _ = secured
    issuer = httpx.get(f"{base_url}/.well-known/oauth-authorization-server").json()
    assert issuer["registration_endpoint"] == f"{base_url}/register"
    assert "S256" in issuer["code_challenge_methods_supported"]
    resource = httpx.get(f"{base_url}/.well-known/oauth-protected-resource/mcp").json()
    assert [s.rstrip("/") for s in resource["authorization_servers"]] == [base_url]


def test_oauth_login_with_a_key_issues_tokens_that_work(secured) -> None:
    base_url, provider = secured
    storage = _Memory()
    code = asyncio.run(_call(f"{base_url}/mcp", _oauth_client(base_url, KEY_A, storage)))
    assert code == "334979"
    assert storage.tokens is not None and storage.tokens.refresh_token
    assert storage.client_info is not None
    # Nothing but a hash of the key is written down.
    record = provider.store.get("access_tokens", storage.tokens.access_token)
    assert record["subject"] == auth.key_id(KEY_A)
    assert KEY_A not in (provider.store.path.read_text("utf-8"))


def test_oauth_login_with_a_wrong_key_is_refused(secured) -> None:
    base_url, _ = secured
    seen: dict[str, int] = {}
    with pytest.raises(Exception):
        asyncio.run(_call(f"{base_url}/mcp", _oauth_client(base_url, "wrong", _Memory(), seen)))
    assert seen["login_status"] == 403


def test_revoking_the_key_ends_the_oauth_session(secured, env_file) -> None:
    base_url, provider = secured
    storage = _Memory()
    code = asyncio.run(_call(f"{base_url}/mcp", _oauth_client(base_url, KEY_A, storage)))
    assert code == "334979"
    _write_keys(env_file, KEY_B)
    # The access token is refused ...
    with pytest.raises(Exception):
        asyncio.run(_call(f"{base_url}/mcp", _bearer(storage.tokens.access_token)))
    # ... and so is the refresh.
    client = asyncio.run(provider.get_client(storage.client_info.client_id))
    refresh = asyncio.run(provider.load_refresh_token(client, storage.tokens.refresh_token))
    assert refresh is not None
    with pytest.raises(Exception, match="revoked"):
        asyncio.run(provider.exchange_refresh_token(client, refresh, refresh.scopes))


def test_tokens_survive_a_restart(secured) -> None:
    base_url, provider = secured
    storage = _Memory()
    code = asyncio.run(_call(f"{base_url}/mcp", _oauth_client(base_url, KEY_A, storage)))
    assert code == "334979"
    reloaded = auth.KeyAuthProvider(provider.keys, auth.AuthStore(provider.store.path), base_url)
    token = asyncio.run(reloaded.load_access_token(storage.tokens.access_token))
    assert token is not None and token.subject == auth.key_id(KEY_A)


def test_registration_sweep_forgets_clients_that_never_logged_in(secured) -> None:
    base_url, provider = secured
    storage = _Memory()
    code = asyncio.run(_call(f"{base_url}/mcp", _oauth_client(base_url, KEY_A, storage)))
    assert code == "334979"
    live = storage.client_info.client_id
    old = time.time() - auth.UNUSED_CLIENT_TTL - 1
    for n in range(3):
        provider.store.put("clients", f"stale-{n}", {"info": {}, "registered_at": old})
    for n in range(auth.MAX_UNUSED_CLIENTS + 5):
        provider.store.put("clients", f"fresh-{n}", {"info": {}, "registered_at": time.time()})
    provider.sweep()
    left = provider.store.records("clients")
    assert live in left
    assert not any(k.startswith("stale-") for k in left)
    assert sum(k.startswith("fresh-") for k in left) == auth.MAX_UNUSED_CLIENTS


def test_public_host_header_is_accepted_behind_a_proxy(secured) -> None:
    """A reverse proxy forwards the public hostname; a rebinding attempt gets 421."""
    base_url, _ = secured
    ping = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
    ok = httpx.post(
        f"{base_url}/mcp",
        json=ping,
        headers={"Host": "mcp.example", "Authorization": f"Bearer {KEY_A}"},
    )
    assert ok.status_code != 421, ok.text
    # Authentication runs first, so the rebinding check is seen with a valid key.
    bad = httpx.post(
        f"{base_url}/mcp",
        json=ping,
        headers={"Host": "evil.example", "Authorization": f"Bearer {KEY_A}"},
    )
    assert bad.status_code == 421


# -- the listen rule -------------------------------------------------------------


def test_open_server_may_only_listen_on_loopback(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("MCP_HTTP_KEYS", raising=False)
    none = auth.KeyStore(None)
    assert http_server.auth_for(none, "127.0.0.1", "http://127.0.0.1:8080") == (None, None)
    with pytest.raises(ValueError, match="MCP_HTTP_KEYS"):
        http_server.auth_for(none, "0.0.0.0", "http://0.0.0.0:8080")
    env = tmp_path / ".env"
    _write_keys(env, KEY_A)
    settings, provider = http_server.auth_for(auth.KeyStore(env), "0.0.0.0", "https://mcp.example")
    assert provider is not None
    assert str(settings.issuer_url).rstrip("/") == "https://mcp.example"
