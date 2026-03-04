# MCP (Model Context Protocol)

ResearchClaw 支持 MCP 协议，允许接入外部工具和服务。

## 什么是 MCP

MCP（Model Context Protocol）是一个标准化协议，允许 AI 助手与外部工具进行交互。通过 MCP，你可以为 ResearchClaw 接入更多工具和数据源。

## 配置 MCP 服务

在 `mcp.yaml` 中配置 MCP 服务器：

```yaml
servers:
  - name: "my-mcp-server"
    url: "http://localhost:3000"
    enabled: true
```

## 使用场景

- 接入本地知识库
- 连接数据库进行数据查询
- 调用自定义 API 服务
- 扩展文件系统操作能力

## 注意事项

- MCP 服务器需要独立部署和运行
- 确保 MCP 服务器的端口可访问
- 建议在安全的网络环境中使用
