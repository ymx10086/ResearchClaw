# MCP (Model Context Protocol)

ResearchClaw supports MCP clients so the agent can use external tools and data services.

## Where MCP Config Lives

MCP client definitions are stored in `~/.researchclaw/config.json` under `mcp.clients`.

## Example

```json
{
  "mcp": {
    "clients": {
      "local-tools": {
        "name": "Local Tools",
        "enabled": true,
        "transport": "stdio",
        "command": "python",
        "args": ["/opt/mcp/server.py"],
        "env": {
          "API_KEY": "xxx"
        }
      },
      "http-tools": {
        "name": "HTTP Tools",
        "enabled": true,
        "transport": "streamable_http",
        "url": "http://127.0.0.1:3000"
      }
    }
  }
}
```

## Supported Transport Types

- `stdio`
- `streamable_http` (also accepts `http` alias)
- `sse`

## Operational Notes

- MCP services are deployed separately from ResearchClaw.
- When MCP config changes, runtime clients are hot-reloaded.
- Keep MCP credentials in secret env vars where possible.
