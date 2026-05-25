"""FastMCP tool surface for the AppGoblin public v1 API.

The `mcp` instance defined here is the single source of truth and is imported
by both the stdio entry point (`python -m appgoblin_mcp`) and, later, by an
HTTP/remote wrapper. Tools construct the client lazily so import-time has no
side effects and `APPGOBLIN_API_KEY` is only required at first call.
"""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from appgoblin_mcp.client import AppGoblinClient, AppGoblinError

mcp = FastMCP("AppGoblin")


def _format_error(e: AppGoblinError) -> dict[str, Any]:
    """Surface API errors as structured payloads so the assistant can react
    (e.g. tell the user to upgrade for company endpoints, or back off on 429)."""
    return {
        "error": True,
        "status_code": e.status_code,
        "body": e.body,
        "rate_limit": e.rate_limit,
    }


@mcp.tool(description=(
    "Get public metadata for a single app: stable store fields plus MAU, "
    "recent installs, and estimated revenue signals.\n\n"
    "`store_id` is the platform's app identifier: a package name for Google "
    "Play (e.g. 'com.king.candycrushsaga') or a numeric ID for the Apple App "
    "Store (e.g. '553834731' for Candy Crush). The endpoint auto-detects which."
))
def get_app(store_id: str) -> dict[str, Any]:
    try:
        with AppGoblinClient.from_env() as c:
            return c.get_app(store_id)
    except AppGoblinError as e:
        return _format_error(e)


@mcp.tool(description=(
    "Get flat best-rank records for an app across countries, collections, and "
    "categories over the last 90 days. Useful for spotting where an app ranks "
    "highest and how that has shifted recently.\n\n"
    "`store_id`: Google package name or Apple numeric ID."
))
def get_app_ranks(store_id: str) -> Any:
    try:
        with AppGoblinClient.from_env() as c:
            return c.get_app_ranks(store_id)
    except AppGoblinError as e:
        return _format_error(e)


@mcp.tool(description=(
    "Get an app's public SDK findings: detected SDKs, declared permissions, "
    "package queries, SKAdNetwork entries, and unmapped evidence. Useful for "
    "understanding monetization stack, analytics, ad networks, etc.\n\n"
    "`store_id`: Google package name or Apple numeric ID."
))
def get_app_sdks(store_id: str) -> dict[str, Any]:
    try:
        with AppGoblinClient.from_env() as c:
            return c.get_app_sdks(store_id)
    except AppGoblinError as e:
        return _format_error(e)


@mcp.tool(description=(
    "List companies from the public index with latest trend snapshot fields "
    "(market share, market-share change, total apps, apps added/lost).\n\n"
    "The raw index is large; this tool filters and trims results client-side "
    "to keep responses usable in conversation:\n"
    "  - `name_contains` (optional): case-insensitive substring match against "
    "    company name OR domain. Pass 'unity', 'meta', 'google' etc.\n"
    "  - `limit` (default 25, max 200): cap the number of rows returned.\n"
    "  - `sort_by` (optional): one of 'installs_d30', 'total_app_count', "
    "    'google_sdk_latest_pct_market_share', 'apple_sdk_latest_pct_market_share'. "
    "    Sorts descending. Default: returned order (matches API)."
))
def list_companies(
    name_contains: str | None = None,
    limit: int = 25,
    sort_by: str | None = None,
) -> dict[str, Any]:
    limit = max(1, min(200, limit))
    allowed_sort = {
        "installs_d30",
        "total_app_count",
        "google_sdk_latest_pct_market_share",
        "apple_sdk_latest_pct_market_share",
    }
    try:
        with AppGoblinClient.from_env() as c:
            rows = c.list_companies()
    except AppGoblinError as e:
        return _format_error(e)
    if not isinstance(rows, list):
        return {"error": True, "body": "Unexpected response shape", "raw": rows}
    if name_contains:
        needle = name_contains.lower()
        rows = [
            r for r in rows
            if needle in str(r.get("name", "")).lower()
            or needle in str(r.get("company_domain", "")).lower()
        ]
    if sort_by in allowed_sort:
        rows = sorted(rows, key=lambda r: (r.get(sort_by) or 0), reverse=True)
    total = len(rows)
    return {"total_matches": total, "returned": min(total, limit), "companies": rows[:limit]}


@mcp.tool(description=(
    "Get the public overview for a single company by domain: mapping status, "
    "company types, key metrics, latest-trends summary, and dataset "
    "availability.\n\n"
    "Note: company endpoints require a paid AppGoblin subscription tier — "
    "free keys get a 403 here.\n\n"
    "  - `company_domain` (required): e.g. 'unity.com', 'meta.com'.\n"
    "  - `category` (optional): narrow the trends slice to a specific category."
))
def get_company(company_domain: str, category: str | None = None) -> dict[str, Any]:
    try:
        with AppGoblinClient.from_env() as c:
            return c.get_company(company_domain, category=category)
    except AppGoblinError as e:
        return _format_error(e)
