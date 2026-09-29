"""Shared fixtures: a running HTTP server for the transport and auth tests."""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Callable, Iterator

import pytest
import uvicorn
from starlette.applications import Starlette


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def run_server() -> Iterator[Callable[[Callable[[str], Starlette]], str]]:
    """``run_server(build)`` serves ``build(base_url)`` in a thread and returns the base URL.

    The app is built after the port is known, so an app that must know its
    own public URL (the OAuth issuer) can be given it.
    """
    servers: list[tuple[uvicorn.Server, threading.Thread]] = []

    def start(build: Callable[[str], Starlette]) -> str:
        port = _free_port()
        base_url = f"http://127.0.0.1:{port}"
        app = build(base_url)
        uvi = uvicorn.Server(
            uvicorn.Config(
                app, host="127.0.0.1", port=port, log_level="error", timeout_graceful_shutdown=5
            )
        )
        thread = threading.Thread(target=uvi.run, daemon=True)
        thread.start()
        deadline = time.monotonic() + 10
        while not uvi.started:
            assert time.monotonic() < deadline, "server did not start"
            time.sleep(0.02)
        servers.append((uvi, thread))
        return base_url

    yield start

    for uvi, thread in servers:
        uvi.should_exit = True
        thread.join(timeout=10)
        assert not thread.is_alive(), "server did not stop"
