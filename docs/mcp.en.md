# MCP

ResearchClaw supports MCP clients so the agent can call external tools and services.

## Config Location

MCP clients are stored under `config.json`:

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
      }
    }
  }
}
```

## Supported Transports

- `stdio`
- `streamable_http`
- `http` alias
- `sse`

## Management Surfaces

Console:

- the `MCP` page can add, edit, toggle, and delete clients

API:

- `GET /api/mcp`
- `POST /api/mcp`
- `PUT /api/mcp/{client_key}`
- `PATCH /api/mcp/{client_key}/toggle`
- `DELETE /api/mcp/{client_key}`

## Runtime Behavior

- MCP config changes are saved and then hot-reloaded
- the runner refreshes MCP clients after changes
- MCP servers are external processes or services; ResearchClaw only manages the client definitions

## Notes

- keep sensitive MCP env vars in the secret env store where possible
- if an MCP client fails, check both the MCP server process and the ResearchClaw runtime logs
