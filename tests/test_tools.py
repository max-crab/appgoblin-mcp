"""MCP tools: invoke them as plain Python functions with the client patched
to a mock transport. We don't drive them through the MCP protocol — the
behavior we care about is the tool body, and FastMCP just wires it up.
"""
from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from appgoblin_mcp import client as client_module
from appgoblin_mcp import tools


@pytest.fixture()
def patched_client(monkeypatch, mock_transport_factory) -> Callable[[dict], None]:
    """Returns `install(routes)` that monkeypatches `AppGoblinClient.from_env`
    to always return a client wired to a MockTransport for `routes`."""
    monkeypatch.setenv("APPGOBLIN_API_KEY", "test-key")

    def install(routes: dict) -> None:
        transport = mock_transport_factory(routes)
        monkeypatch.setattr(
            client_module.AppGoblinClient,
            "from_env",
            classmethod(
                lambda cls, transport=None, _t=transport: cls(api_key="test-key", transport=_t)
            ),
        )

    return install


def _call(tool_fn, **kwargs):
    """FastMCP may wrap the function; the original callable is on `.fn`."""
    target = getattr(tool_fn, "fn", tool_fn)
    return target(**kwargs)


def test_get_app(patched_client):
    patched_client({("GET", "/api/v1/apps/com.foo"): (200, {"name": "Foo"})})
    assert _call(tools.get_app, store_id="com.foo") == {"name": "Foo"}


def test_get_app_ranks(patched_client):
    patched_client({("GET", "/api/v1/apps/com.foo/ranks"): (200, [{"country": "US"}])})
    assert _call(tools.get_app_ranks, store_id="com.foo") == [{"country": "US"}]


def test_get_app_sdks(patched_client):
    patched_client({("GET", "/api/v1/apps/com.foo/sdks"): (200, {"sdks": []})})
    assert _call(tools.get_app_sdks, store_id="com.foo") == {"sdks": []}


def test_list_companies_filters_by_name(patched_client):
    rows = [
        {"name": "Unity", "company_domain": "unity.com", "installs_d30": 100},
        {"name": "Meta", "company_domain": "meta.com", "installs_d30": 500},
        {"name": "Google", "company_domain": "google.com", "installs_d30": 1000},
        {"name": "Unity Ads", "company_domain": "unityads.unity3d.com", "installs_d30": 50},
    ]
    patched_client({("GET", "/api/v1/companies"): (200, rows)})
    out = _call(tools.list_companies, name_contains="unity")
    assert out["total_matches"] == 2
    assert {c["name"] for c in out["companies"]} == {"Unity", "Unity Ads"}


def test_list_companies_limit_caps_results(patched_client):
    rows = [{"name": f"co{i}", "company_domain": f"co{i}.com"} for i in range(50)]
    patched_client({("GET", "/api/v1/companies"): (200, rows)})
    out = _call(tools.list_companies, limit=5)
    assert out["total_matches"] == 50
    assert out["returned"] == 5
    assert len(out["companies"]) == 5


def test_list_companies_sort_by_installs(patched_client):
    rows = [
        {"name": "A", "installs_d30": 100},
        {"name": "B", "installs_d30": 999},
        {"name": "C", "installs_d30": 500},
    ]
    patched_client({("GET", "/api/v1/companies"): (200, rows)})
    out = _call(tools.list_companies, sort_by="installs_d30")
    assert [c["name"] for c in out["companies"]] == ["B", "C", "A"]


def test_list_companies_ignores_unknown_sort(patched_client):
    rows = [{"name": "A"}, {"name": "B"}]
    patched_client({("GET", "/api/v1/companies"): (200, rows)})
    out = _call(tools.list_companies, sort_by="not_a_field")
    assert [c["name"] for c in out["companies"]] == ["A", "B"]


def test_get_company_without_category(patched_client):
    patched_client(
        {("GET", "/api/v1/companies/unity.com"): (200, {"company_domain": "unity.com"})}
    )
    out = _call(tools.get_company, company_domain="unity.com")
    assert out["company_domain"] == "unity.com"


def test_tool_returns_structured_error_on_403(patched_client):
    """Company endpoints 403 on free tier — tool surfaces that without raising."""
    patched_client(
        {("GET", "/api/v1/companies/unity.com"): (403, {"detail": "paid tier only"})}
    )
    out = _call(tools.get_company, company_domain="unity.com")
    assert out == {
        "error": True,
        "status_code": 403,
        "body": {"detail": "paid tier only"},
        "rate_limit": {},
    }


def test_tool_returns_structured_error_on_429_with_rate_limit(monkeypatch):
    monkeypatch.setenv("APPGOBLIN_API_KEY", "k")

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"detail": "slow down"},
            headers={"X-RateLimit-Limit": "30", "X-RateLimit-Remaining": "0"},
        )

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        client_module.AppGoblinClient,
        "from_env",
        classmethod(lambda cls, transport=None, _t=transport: cls(api_key="k", transport=_t)),
    )

    out = _call(tools.get_app, store_id="com.foo")
    assert out["error"] is True
    assert out["status_code"] == 429
    assert out["rate_limit"]["x-ratelimit-limit"] == "30"


def test_get_company_passes_category_query(monkeypatch):
    monkeypatch.setenv("APPGOBLIN_API_KEY", "k")
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["query"] = dict(req.url.params)
        return httpx.Response(200, json={"company_domain": "unity.com"})

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        client_module.AppGoblinClient,
        "from_env",
        classmethod(lambda cls, transport=None, _t=transport: cls(api_key="k", transport=_t)),
    )

    _call(tools.get_company, company_domain="unity.com", category="games")
    assert captured["query"] == {"category": "games"}
