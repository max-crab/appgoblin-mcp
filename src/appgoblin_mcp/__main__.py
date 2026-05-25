"""stdio entry point: `python -m appgoblin_mcp` or `appgoblin-mcp` (after install).

For a remote/HTTP deploy later, build a FastAPI app and mount
`mcp.streamable_http_app()` — the same `mcp` instance from
`appgoblin_mcp.tools` already has every tool registered.
"""
from appgoblin_mcp.tools import mcp


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
