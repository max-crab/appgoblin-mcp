# appgoblin-mcp

An MCP server that exposes the [AppGoblin public v1 API](https://appgoblin.info/api-docs) as
tools, so Claude (Desktop, Code, or any MCP client) can fetch app metadata,
rankings, SDKs, and company data in conversation.

Each teammate runs the server locally over stdio and uses their own AppGoblin
API key. The code is structured so the same tools can be served over HTTP later
without rewriting (see [Remote deploy](#remote-deploy-later)).

## Tools

| Tool             | Endpoint                          | Notes                              |
|------------------|-----------------------------------|------------------------------------|
| `get_app`        | `GET /api/v1/apps/{store_id}`     | App metadata + MAU/installs/revenue |
| `get_app_ranks`  | `GET /api/v1/apps/{store_id}/ranks` | 90-day best ranks across countries  |
| `get_app_sdks`   | `GET /api/v1/apps/{store_id}/sdks`  | Detected SDKs, permissions, SKAdNet |
| `list_companies` | `GET /api/v1/companies`           | Index, with client-side filter/sort |
| `get_company`    | `GET /api/v1/companies/{domain}`  | Company overview (paid tier)        |

`store_id` is a Google Play package name (e.g. `com.king.candycrushsaga`) or an
Apple App Store numeric ID (e.g. `553834731`).

## Setup

Requires Python 3.11+.

```powershell
git clone https://github.com/max-crab/appgoblin-mcp.git
cd appgoblin-mcp
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
```

Get an AppGoblin API token from <https://appgoblin.info/account/api-keys> and
set it in your environment:

```powershell
# PowerShell (user-scoped, persists)
[Environment]::SetEnvironmentVariable("APPGOBLIN_API_KEY", "your-token-here", "User")
```

```bash
# macOS / Linux
export APPGOBLIN_API_KEY=your-token-here
```

Verify locally:

```powershell
.\.venv\Scripts\python -m pytest
```

## Use with Claude Desktop

Add this to your Claude Desktop config
(`%APPDATA%\Claude\claude_desktop_config.json` on Windows,
`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "appgoblin": {
      "command": "C:\\path\\to\\appgoblin-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "appgoblin_mcp"],
      "env": {
        "APPGOBLIN_API_KEY": "your-token-here"
      }
    }
  }
}
```

Restart Claude Desktop. The five tools above will show up under the `appgoblin`
server. Try: *"Pull AppGoblin metadata and SDKs for com.king.candycrushsaga."*

## Use with Claude Code

```powershell
claude mcp add appgoblin -- C:\path\to\appgoblin-mcp\.venv\Scripts\python.exe -m appgoblin_mcp
```

Then set `APPGOBLIN_API_KEY` in your shell before launching `claude`.

## Rate limits

Free keys: 30 req/min, 1000 req/day. Errors propagate with status and any
`X-RateLimit-*` headers so the assistant can back off or tell you to upgrade.
Company endpoints require a paid tier (free-tier `get_company` calls return a
structured 403 payload, not an exception).

## Environment

| Variable                    | Default                | Notes                          |
|-----------------------------|------------------------|--------------------------------|
| `APPGOBLIN_API_KEY`         | *(required)*           | Your token                     |
| `APPGOBLIN_BASE_URL`        | `https://appgoblin.info` | Override for staging/proxy   |
| `APPGOBLIN_TIMEOUT_SECONDS` | `30`                   | httpx timeout                  |

## Remote deploy (later)

The `mcp` instance in `src/appgoblin_mcp/tools.py` is a `FastMCP` object — the
same one used in stdio mode. To serve it over HTTP, mount
`mcp.streamable_http_app()` on a FastAPI/Starlette app with a bearer-auth
middleware (so teammates don't need a local clone). All five tools are already
registered; only the transport changes.

## Layout

```
src/appgoblin_mcp/
  client.py     # httpx wrapper, X-API-Key auth, error wrapping
  tools.py      # FastMCP instance + 5 @mcp.tool functions
  __main__.py   # stdio entry: `python -m appgoblin_mcp`
tests/
  conftest.py   # MockTransport fixture
  test_client.py
  test_tools.py
```
