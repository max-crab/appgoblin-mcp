"""Test fixtures.

Tests must never hit the real AppGoblin API. We build clients with an
`httpx.MockTransport` that routes by path+method and returns canned JSON.
"""
from __future__ import annotations

import json
import os
from collections.abc import Callable

import httpx
import pytest

# Make sure no real API key leaks in from the dev environment.
os.environ.setdefault("APPGOBLIN_API_KEY", "test-key-not-real")


@pytest.fixture()
def mock_transport_factory() -> Callable[[dict], httpx.MockTransport]:
    """Returns a factory that builds an httpx.MockTransport from a route map:

        {("GET", "/api/v1/apps/com.foo"): (200, {"name": "Foo"})}

    Match is exact on (method, path); unmatched routes return 404 so tests fail
    loudly instead of returning empty success."""
    def build(routes: dict) -> httpx.MockTransport:
        def handler(req: httpx.Request) -> httpx.Response:
            key = (req.method, req.url.path)
            if key not in routes:
                return httpx.Response(404, json={"error": f"no mock for {key}"})
            status, body = routes[key]
            if isinstance(body, (dict, list)):
                return httpx.Response(status, content=json.dumps(body),
                                      headers={"content-type": "application/json"})
            return httpx.Response(status, text=str(body))
        return httpx.MockTransport(handler)
    return build
