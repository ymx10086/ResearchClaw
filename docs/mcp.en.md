# MCP (Model Context Protocol)

ResearchClaw supports the MCP protocol, allowing integration with external tools and services.

## What is MCP

MCP (Model Context Protocol) is a standardized protocol that allows AI assistants to interact with external tools. Through MCP, you can connect more tools and data sources to ResearchClaw.

## Configure MCP Servers

Configure MCP servers in `mcp.yaml`:

```yaml
servers:
  - name: "my-mcp-server"
    url: "http://localhost:3000"
    enabled: true
```

## Use Cases

- Connect local knowledge bases
- Query databases
- Call custom API services
- Extend file system capabilities

## Notes

- MCP servers need to be deployed and running separately
- Ensure MCP server ports are accessible
- Recommended for use in secure network environments
