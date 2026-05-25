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

### Recommended: install the `.mcpb` extension

1. Download the latest `appgoblin-mcp-<version>.mcpb` from the
   [Releases page](https://github.com/max-crab/appgoblin-mcp/releases).
2. Open Claude Desktop → Settings → Extensions → drag the `.mcpb` in (or
   double-click it).
3. When prompted, paste your AppGoblin API key. Done.

Claude Desktop will use its bundled `uv` to set up Python deps on first launch —
no manual `pip install`, no path editing, no JSON config. The five tools appear
under the `appgoblin` server. Try: *"Pull AppGoblin metadata and SDKs for
com.king.candycrushsaga."*

### Manual JSON config (fallback)

If you'd rather run from a local clone, edit
`%APPDATA%\Claude\claude_desktop_config.json` (Windows) or
`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

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

## Building the `.mcpb`

The `.mcpb` is rebuilt automatically by
[`.github/workflows/release.yml`](.github/workflows/release.yml) on every tag
push: tag a release (`git tag v0.1.1 && git push --tags`) and the workflow
attaches a fresh `appgoblin-mcp-<version>.mcpb` to the GitHub Release.

To build one locally (requires Node and `uv`):

```powershell
npx --yes @anthropic-ai/mcpb pack . appgoblin-mcp.mcpb
```

`manifest.json` and `.mcpbignore` at the repo root control what goes in.

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
