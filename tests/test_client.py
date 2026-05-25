"""AppGoblinClient: header auth, endpoint paths, error wrapping."""
from __future__ import annotations

import httpx
import pytest

from appgoblin_mcp.client import AppGoblinClient, AppGoblinError


def test_api_key_required():
    with pytest.raises(ValueError):
        AppGoblinClient(api_key="")


def test_sends_x_api_key_header():
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(req.headers)
        captured["path"] = req.url.path
        return httpx.Response(200, json={"ok": True})

    with AppGoblinClient(api_key="abc123", transport=httpx.MockTransport(handler)) as c:
        c.get_app("com.foo")

    assert captured["headers"].get("x-api-key") == "abc123"
    assert captured["path"] == "/api/v1/apps/com.foo"


def test_get_app_ranks_path(mock_transport_factory):
    routes = {("GET", "/api/v1/apps/553834731/ranks"): (200, [{"country": "US", "rank": 5}])}
    with AppGoblinClient(api_key="k", transport=mock_transport_factory(routes)) as c:
        out = c.get_app_ranks("553834731")
    assert out == [{"country": "US", "rank": 5}]


def test_get_app_sdks_path(mock_transport_factory):
    routes = {("GET", "/api/v1/apps/com.king.candycrushsaga/sdks"): (200, {"sdks": ["unity"]})}
    with AppGoblinClient(api_key="k", transport=mock_transport_factory(routes)) as c:
        out = c.get_app_sdks("com.king.candycrushsaga")
    assert out == {"sdks": ["unity"]}


def test_list_companies_path(mock_transport_factory):
    routes = {("GET", "/api/v1/companies"): (200, [{"name": "Unity"}])}
    with AppGoblinClient(api_key="k", transport=mock_transport_factory(routes)) as c:
        out = c.list_companies()
    assert out == [{"name": "Unity"}]


def test_get_company_with_category_query():
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["path"] = req.url.path
        captured["query"] = dict(req.url.params)
        return httpx.Response(200, json={"company_domain": "unity.com"})

    with AppGoblinClient(api_key="k", transport=httpx.MockTransport(handler)) as c:
        c.get_company("unity.com", category="games")

    assert captured["path"] == "/api/v1/companies/unity.com"
    assert captured["query"] == {"category": "games"}


def test_get_company_without_category_omits_param():
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["query"] = dict(req.url.params)
        return httpx.Response(200, json={})

    with AppGoblinClient(api_key="k", transport=httpx.MockTransport(handler)) as c:
        c.get_company("unity.com")

    assert captured["query"] == {}


def test_error_response_raises_with_rate_limit_headers(mock_transport_factory):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"detail": "rate limited"},
            headers={
                "X-RateLimit-Limit": "30",
                "X-RateLimit-Remaining": "0",
                "Retry-After": "12",
            },
        )

    with AppGoblinClient(api_key="k", transport=httpx.MockTransport(handler)) as c:
        with pytest.raises(AppGoblinError) as exc:
            c.get_app("com.foo")

    assert exc.value.status_code == 429
    assert exc.value.body == {"detail": "rate limited"}
    # Only X-RateLimit-* headers are captured; Retry-After is on the response object.
    assert exc.value.rate_limit.get("x-ratelimit-limit") == "30"
    assert exc.value.rate_limit.get("x-ratelimit-remaining") == "0"


def test_from_env_reads_key(monkeypatch):
    monkeypatch.setenv("APPGOBLIN_API_KEY", "env-key-xyz")
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["auth"] = req.headers.get("x-api-key")
        return httpx.Response(200, json={})

    with AppGoblinClient.from_env(transport=httpx.MockTransport(handler)) as c:
        c.get_app("com.foo")

    assert captured["auth"] == "env-key-xyz"


def test_from_env_missing_key(monkeypatch):
    monkeypatch.delenv("APPGOBLIN_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="APPGOBLIN_API_KEY"):
        AppGoblinClient.from_env()
