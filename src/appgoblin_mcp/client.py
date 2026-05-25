"""Thin httpx wrapper around the AppGoblin public v1 API.

The five endpoints share auth, base URL, and error handling, so they live on a
single client class. Tests pass in an `httpx.MockTransport` via the optional
`transport` arg; production code constructs the client from environment vars.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://appgoblin.info"
DEFAULT_TIMEOUT = 30.0


class AppGoblinError(Exception):
    """Wraps non-2xx responses. Carries status, response body, and rate-limit
    headers so MCP tools can surface them to the assistant."""

    def __init__(self, status_code: int, body: Any, rate_limit: dict[str, str] | None = None):
        self.status_code = status_code
        self.body = body
        self.rate_limit = rate_limit or {}
        super().__init__(f"AppGoblin API {status_code}: {body!r}")


class AppGoblinClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"X-API-Key": api_key, "Accept": "application/json"},
            timeout=timeout,
            transport=transport,
        )

    @classmethod
    def from_env(cls, transport: httpx.BaseTransport | None = None) -> "AppGoblinClient":
        key = os.environ.get("APPGOBLIN_API_KEY", "").strip()
        if not key:
            raise RuntimeError(
                "APPGOBLIN_API_KEY is not set. Get a token at "
                "https://appgoblin.info/account/api-keys and export it."
            )
        base = os.environ.get("APPGOBLIN_BASE_URL", DEFAULT_BASE_URL)
        try:
            timeout = float(os.environ.get("APPGOBLIN_TIMEOUT_SECONDS", DEFAULT_TIMEOUT))
        except ValueError:
            timeout = DEFAULT_TIMEOUT
        return cls(api_key=key, base_url=base, timeout=timeout, transport=transport)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "AppGoblinClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ---- endpoints --------------------------------------------------------

    def get_app(self, store_id: str) -> dict[str, Any]:
        return self._get(f"/api/v1/apps/{store_id}")

    def get_app_ranks(self, store_id: str) -> list[dict[str, Any]] | dict[str, Any]:
        return self._get(f"/api/v1/apps/{store_id}/ranks")

    def get_app_sdks(self, store_id: str) -> dict[str, Any]:
        return self._get(f"/api/v1/apps/{store_id}/sdks")

    def list_companies(self) -> list[dict[str, Any]]:
        return self._get("/api/v1/companies")

    def get_company(
        self, company_domain: str, category: str | None = None
    ) -> dict[str, Any]:
        params = {"category": category} if category else None
        return self._get(f"/api/v1/companies/{company_domain}", params=params)

    # ---- internals --------------------------------------------------------

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        r = self._http.get(path, params=params)
        rate = {k: v for k, v in r.headers.items() if k.lower().startswith("x-ratelimit")}
        if r.status_code >= 400:
            try:
                body = r.json()
            except ValueError:
                body = r.text
            raise AppGoblinError(r.status_code, body, rate_limit=rate)
        return r.json()
