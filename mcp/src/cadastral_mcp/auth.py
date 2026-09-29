"""Access control for the HTTP transport: a list of keys in ``.env``.

``MCP_HTTP_KEYS`` in the ``.env`` file is a comma-separated list of random
keys (UUIDs). The file is read on every check, so removing a key from it
revokes that key at once, no restart. A key opens the server in two ways:

* as a bearer token, ``Authorization: Bearer <key>``, for clients that can
  send a header (Claude Code, the MCP Inspector, Codex, scripts);
* as the credential on the login page of the small OAuth 2.1 authorization
  server this module also is, for clients that only speak OAuth (claude.ai
  custom connectors, ChatGPT). The client registers itself, the person is
  sent to ``/login``, types a key, and the client gets short-lived tokens.
  A token stays valid only while the key it was issued to is in the file.

The MCP SDK does the protocol (metadata, registration, PKCE, the token
endpoint, the bearer middleware); this module supplies the policy: what a
valid key is and where issued tokens live (``AuthStore``, a JSON file, so a
restart does not log everyone out).
"""

from __future__ import annotations

import hashlib
import hmac
import html
import json
import logging
import os
import secrets
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from dotenv import dotenv_values, find_dotenv
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    TokenError,
    construct_redirect_uri,
)
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.server.mcpserver import MCPServer
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import AnyHttpUrl
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

logger = logging.getLogger(__name__)

#: The ``.env`` variable that lists the keys.
KEYS_VARIABLE = "MCP_HTTP_KEYS"
#: Where the login page lives (a custom route next to the SDK's OAuth routes).
LOGIN_PATH = "/login"

ACCESS_TOKEN_TTL = 60 * 60
REFRESH_TOKEN_TTL = 30 * 24 * 60 * 60
AUTHORIZATION_CODE_TTL = 5 * 60
LOGIN_TTL = 10 * 60
#: A registered client that never logged in is forgotten after this long,
#: and at most this many such clients are kept: registration is public.
UNUSED_CLIENT_TTL = 24 * 60 * 60
MAX_UNUSED_CLIENTS = 100
EXPIRED_LOGIN = "This login link has expired. Start again from your client."


def key_id(key: str) -> str:
    """A short, non-reversible name for a key, for logs and token records."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


class KeyStore:
    """The keys in ``MCP_HTTP_KEYS``, read from the ``.env`` file on every check.

    Args:
        env_file: The ``.env`` file; None to read the process environment
            instead (then a change needs a restart). ``KeyStore.default()``
            looks for ``.env`` from the working directory upwards.
    """

    def __init__(self, env_file: Path | None) -> None:
        self.env_file = env_file

    @classmethod
    def default(cls) -> KeyStore:
        """``MCP_HTTP_KEYS_FILE`` or the nearest ``.env`` above the working directory."""
        configured = os.environ.get("MCP_HTTP_KEYS_FILE")
        if configured:
            return cls(Path(configured))
        found = find_dotenv(usecwd=True)
        return cls(Path(found) if found else None)

    def keys(self) -> list[str]:
        """The keys as they are now (empty when none are configured)."""
        if self.env_file is not None:
            # The file alone: the process environment may hold a copy loaded
            # at start, which a removal from the file must override.
            raw = dotenv_values(self.env_file).get(KEYS_VARIABLE) or ""
        else:
            raw = os.environ.get(KEYS_VARIABLE, "")
        return [key.strip() for key in raw.split(",") if key.strip()]

    def configured(self) -> bool:
        return bool(self.keys())

    def is_valid(self, key: str) -> bool:
        """Whether ``key`` is in the list now (constant-time comparison)."""
        wanted = key.encode("utf-8")
        return any(hmac.compare_digest(wanted, known.encode("utf-8")) for known in self.keys())

    def is_valid_id(self, subject: str) -> bool:
        """Whether the key with this ``key_id`` is still in the list."""
        return any(key_id(known) == subject for known in self.keys())

    def describe(self) -> str:
        return str(self.env_file) if self.env_file else f"${KEYS_VARIABLE}"


class AuthStore:
    """Registered clients and issued tokens, in one JSON file.

    Small enough to rewrite whole on every change; written atomically and
    readable by the owner only. ``path=None`` keeps everything in memory.
    """

    COLLECTIONS = ("clients", "codes", "access_tokens", "refresh_tokens")

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._data: dict[str, dict[str, Any]] = {name: {} for name in self.COLLECTIONS}
        if path is not None and path.exists():
            loaded = json.loads(path.read_text("utf-8"))
            for name in self.COLLECTIONS:
                self._data[name] = dict(loaded.get(name, {}))

    def get(self, collection: str, key: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._data[collection].get(key)
            return dict(record) if record is not None else None

    def put(self, collection: str, key: str, record: dict[str, Any]) -> None:
        with self._lock:
            self._data[collection][key] = record
            self._save()

    def delete(self, collection: str, key: str) -> None:
        with self._lock:
            if self._data[collection].pop(key, None) is not None:
                self._save()

    def records(self, collection: str) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {key: dict(record) for key, record in self._data[collection].items()}

    def delete_many(self, collection: str, keys: list[str]) -> None:
        with self._lock:
            removed = [self._data[collection].pop(key, None) for key in keys]
            if any(record is not None for record in removed):
                self._save()

    def _save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=self.path.name, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(self._data, handle, indent=1)
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.path)


def _expired(record: dict[str, Any]) -> bool:
    expires_at = record.get("expires_at")
    return expires_at is not None and expires_at < time.time()


class KeyAuthProvider(
    OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]
):
    """Bearer keys and the OAuth authorization server whose login is a key.

    Args:
        keys: Where the valid keys are.
        store: Where clients and issued tokens are kept.
        public_url: The URL clients reach the server at (issuer; the login
            page and the redirects are built on it).
    """

    def __init__(self, keys: KeyStore, store: AuthStore, public_url: str) -> None:
        self.keys = keys
        self.store = store
        self.public_url = public_url.rstrip("/")
        self._pending: dict[str, dict[str, Any]] = {}
        self._pending_lock = threading.Lock()

    # -- bearer tokens -------------------------------------------------------

    async def load_access_token(self, token: str) -> AccessToken | None:
        """A key itself, or an access token issued to one that is still listed."""
        if self.keys.is_valid(token):
            return AccessToken(token=token, client_id="key", scopes=[], subject=key_id(token))
        record = self.store.get("access_tokens", token)
        if record is None:
            return None
        if _expired(record) or not self.keys.is_valid_id(record["subject"]):
            self.store.delete("access_tokens", token)
            return None
        return AccessToken(
            token=token,
            client_id=record["client_id"],
            scopes=record["scopes"],
            expires_at=int(record["expires_at"]),
            resource=record.get("resource"),
            subject=record["subject"],
        )

    # -- clients ----------------------------------------------------------------

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        record = self.store.get("clients", client_id)
        return OAuthClientInformationFull.model_validate(record["info"]) if record else None

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        self.sweep()
        self.store.put(
            "clients",
            client_info.client_id,
            {"info": client_info.model_dump(mode="json"), "registered_at": time.time()},
        )
        logger.info(
            "OAuth client registered: %s (%s)", client_info.client_id, client_info.client_name
        )

    def sweep(self) -> None:
        """Drop expired codes and tokens, and clients that registered but never logged in.

        Registration needs no key, so anyone reaching the server can add a
        client; without this the store would grow with every scan.
        """
        for collection in ("codes", "access_tokens", "refresh_tokens"):
            expired = [k for k, r in self.store.records(collection).items() if _expired(r)]
            self.store.delete_many(collection, expired)
        in_use = {
            record["client_id"]
            for collection in ("access_tokens", "refresh_tokens")
            for record in self.store.records(collection).values()
        }
        unused = sorted(
            (
                (record.get("registered_at", 0.0), client_id)
                for client_id, record in self.store.records("clients").items()
                if client_id not in in_use
            ),
        )
        cutoff = time.time() - UNUSED_CLIENT_TTL
        stale = [client_id for registered_at, client_id in unused if registered_at < cutoff]
        over = max(0, len(unused) - len(stale) - MAX_UNUSED_CLIENTS)
        stale += [client_id for _, client_id in unused if client_id not in stale][:over]
        self.store.delete_many("clients", stale)

    # -- authorization ----------------------------------------------------------

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        """Remember the request and send the person to the login page."""
        txn = secrets.token_urlsafe(32)
        with self._pending_lock:
            now = time.time()
            for stale in [k for k, v in self._pending.items() if v["expires_at"] < now]:
                del self._pending[stale]
            self._pending[txn] = {
                "client_id": client.client_id,
                "client_name": client.client_name,
                "params": params.model_dump(mode="json"),
                "expires_at": now + LOGIN_TTL,
            }
        return f"{self.public_url}{LOGIN_PATH}?txn={txn}"

    def _take_pending(self, txn: str) -> dict[str, Any] | None:
        with self._pending_lock:
            pending = self._pending.get(txn)
            if pending is None or pending["expires_at"] < time.time():
                self._pending.pop(txn, None)
                return None
            return pending

    def add_routes(self, mcp_server: MCPServer) -> None:
        """Register the login page on the server (public routes, like /health)."""

        @mcp_server.custom_route(LOGIN_PATH, methods=["GET"])  # type: ignore[misc]
        async def login_form(request: Request) -> Response:
            txn = request.query_params.get("txn", "")
            pending = self._take_pending(txn)
            if pending is None:
                return _login_page(None, None, EXPIRED_LOGIN, 400)
            return _login_page(txn, pending["client_name"], None, 200)

        @mcp_server.custom_route(LOGIN_PATH, methods=["POST"])  # type: ignore[misc]
        async def login_submit(request: Request) -> Response:
            form = await request.form()
            txn = str(form.get("txn", ""))
            key = str(form.get("key", "")).strip()
            pending = self._take_pending(txn)
            if pending is None:
                return _login_page(None, None, EXPIRED_LOGIN, 400)
            if not self.keys.is_valid(key):
                logger.warning("Login refused for client %s: unknown key", pending["client_id"])
                return _login_page(txn, pending["client_name"], "That key is not valid.", 403)
            with self._pending_lock:
                self._pending.pop(txn, None)
            params = AuthorizationParams.model_validate(pending["params"])
            code = secrets.token_urlsafe(32)
            self.store.put(
                "codes",
                code,
                {
                    "client_id": pending["client_id"],
                    "scopes": params.scopes or [],
                    "expires_at": time.time() + AUTHORIZATION_CODE_TTL,
                    "code_challenge": params.code_challenge,
                    "redirect_uri": str(params.redirect_uri),
                    "redirect_uri_provided_explicitly": params.redirect_uri_provided_explicitly,
                    "resource": params.resource,
                    "subject": key_id(key),
                },
            )
            logger.info("Login accepted for client %s (key %s)", pending["client_id"], key_id(key))
            location = construct_redirect_uri(
                str(params.redirect_uri), code=code, state=params.state
            )
            return RedirectResponse(
                location, status_code=302, headers={"Cache-Control": "no-store"}
            )

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        record = self.store.get("codes", authorization_code)
        if record is None:
            return None
        if _expired(record):
            self.store.delete("codes", authorization_code)
            return None
        return AuthorizationCode(code=authorization_code, **record)

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        self.store.delete("codes", authorization_code.code)
        return self._issue(
            client.client_id, authorization_code.scopes, authorization_code.subject,
            authorization_code.resource,
        )

    # -- refresh --------------------------------------------------------------

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        record = self.store.get("refresh_tokens", refresh_token)
        if record is None:
            return None
        if _expired(record):
            self.store.delete("refresh_tokens", refresh_token)
            return None
        return RefreshToken(
            token=refresh_token,
            client_id=record["client_id"],
            scopes=record["scopes"],
            expires_at=int(record["expires_at"]),
            resource=record.get("resource"),
            subject=record["subject"],
        )

    async def exchange_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: RefreshToken, scopes: list[str]
    ) -> OAuthToken:
        record = self.store.get("refresh_tokens", refresh_token.token) or {}
        self.store.delete("refresh_tokens", refresh_token.token)
        if access := record.get("access_token"):
            self.store.delete("access_tokens", access)
        subject = refresh_token.subject or ""
        if not self.keys.is_valid_id(subject):
            raise TokenError(
                "invalid_grant", "the key this session was opened with has been revoked"
            )
        return self._issue(client.client_id, scopes, subject, refresh_token.resource)

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        if isinstance(token, RefreshToken):
            record = self.store.get("refresh_tokens", token.token) or {}
            self.store.delete("refresh_tokens", token.token)
            if access := record.get("access_token"):
                self.store.delete("access_tokens", access)
        else:
            record = self.store.get("access_tokens", token.token) or {}
            self.store.delete("access_tokens", token.token)
            if refresh := record.get("refresh_token"):
                self.store.delete("refresh_tokens", refresh)

    async def exchange_identity_assertion(self, *args: Any, **kwargs: Any) -> OAuthToken:
        raise NotImplementedError("identity assertion is not offered")

    def _issue(
        self, client_id: str, scopes: list[str], subject: str | None, resource: str | None
    ) -> OAuthToken:
        access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        now = time.time()
        self.store.put(
            "access_tokens",
            access,
            {
                "client_id": client_id,
                "scopes": scopes,
                "expires_at": now + ACCESS_TOKEN_TTL,
                "resource": resource,
                "subject": subject,
                "refresh_token": refresh,
            },
        )
        self.store.put(
            "refresh_tokens",
            refresh,
            {
                "client_id": client_id,
                "scopes": scopes,
                "expires_at": now + REFRESH_TOKEN_TTL,
                "resource": resource,
                "subject": subject,
                "access_token": access,
            },
        )
        return OAuthToken(
            access_token=access,
            expires_in=ACCESS_TOKEN_TTL,
            scope=" ".join(scopes) or None,
            refresh_token=refresh,
        )


def build_auth_settings(public_url: str, mcp_path: str) -> AuthSettings:
    """The SDK's auth settings: this server is both the issuer and the resource."""
    base = public_url.rstrip("/")
    return AuthSettings(
        issuer_url=AnyHttpUrl(base),
        resource_server_url=AnyHttpUrl(base + mcp_path),
        client_registration_options=ClientRegistrationOptions(enabled=True),
        revocation_options=RevocationOptions(enabled=True),
        # Tokens are issued by this server for this server; the verifier
        # checks the key behind each token instead of a resource claim.
        validate_token_resource=False,
    )


def _login_page(
    txn: str | None, client_name: str | None, error: str | None, status: int
) -> Response:
    who = html.escape(client_name or "An MCP client")
    message = f'<p class="error">{html.escape(error)}</p>' if error else ""
    form = (
        f"""<form method="post" action="{LOGIN_PATH}">
  <input type="hidden" name="txn" value="{html.escape(txn)}">
  <label for="key">Access key</label>
  <input id="key" name="key" type="password" autocomplete="off" autofocus required>
  <button type="submit">Allow access</button>
</form>"""
        if txn
        else ""
    )
    body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Cadastral MCP - access</title>
<style>
body{{font:16px/1.5 system-ui,sans-serif;max-width:28rem;margin:4rem auto;padding:0 1rem;
  color:#222}}
label{{display:block;margin-top:1rem}}
input{{width:100%;padding:.5rem;font-size:1rem;margin:.25rem 0 1rem}}
button{{padding:.5rem 1rem;font-size:1rem}} .error{{color:#b00020}}
.note{{color:#555;font-size:.9rem}}
</style></head><body>
<h1>Cadastral MCP server</h1>
<p><strong>{who}</strong> asks to use this server on your behalf. Enter one of the access keys
from the server's <code>.env</code> file.</p>
{message}
{form}
<p class="note">Demonstration project. Removing the key from the file revokes this access.</p>
</body></html>"""
    return HTMLResponse(body, status_code=status, headers={"Cache-Control": "no-store"})
