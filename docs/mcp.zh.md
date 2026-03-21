# MCP

ResearchClaw 支持 MCP 客户端，使 agent 能调用外部工具和服务。

## 配置位置

MCP 客户端配置位于 `config.json`：

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

## 支持的传输类型

- `stdio`
- `streamable_http`
- `http` 别名
- `sse`

## 管理入口

Console：

- `MCP` 页面可以新增、编辑、开关、删除客户端

API：

- `GET /api/mcp`
- `POST /api/mcp`
- `PUT /api/mcp/{client_key}`
- `PATCH /api/mcp/{client_key}/toggle`
- `DELETE /api/mcp/{client_key}`

## 运行时行为

- MCP 配置变更会先保存，再热重载
- runner 会在配置变更后刷新 MCP clients
- MCP server 本身是外部进程或服务，ResearchClaw 只管理 client definition

## 说明

- 敏感 MCP 环境变量尽量放到 secret env store 中
- MCP 客户端异常时，需要同时排查 MCP server 和 ResearchClaw 运行日志
