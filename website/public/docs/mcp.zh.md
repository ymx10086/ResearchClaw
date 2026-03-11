# MCP (Model Context Protocol)

ResearchClaw 支持 MCP 客户端接入，使 Agent 可以调用外部工具与数据服务。

## MCP 配置位置

MCP 客户端定义位于 `~/.researchclaw/config.json` 的 `mcp.clients` 字段。

## 示例

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

## 支持的传输类型

- `stdio`
- `streamable_http`（兼容 `http` 别名）
- `sse`

## 运维说明

- MCP 服务需要独立部署，不与 ResearchClaw 进程绑定。
- MCP 配置更新后，运行时客户端会热重载。
- 建议将 MCP 凭证放到密钥环境变量中管理。
