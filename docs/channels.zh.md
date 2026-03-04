# 频道

频道是 ResearchClaw 与外部 IM 平台的连接桥梁。通过配置频道，你可以在常用的即时通讯工具中与 AI 助手交互。

## 支持的频道

| 频道 | 说明 |
|------|------|
| 钉钉 | 企业级 IM，支持群消息和私聊 |
| 飞书 | 字节跳动旗下IM，支持群组和私聊 |
| QQ | 基于 QQ 开放平台，支持频道和私聊 |
| Discord | 海外常用 IM，支持 Bot 方式接入 |
| iMessage | macOS 原生消息，需本地部署在 Mac 上 |
| WeChat (WIP) | 微信接入（开发中） |

## 配置方式

### 在控制台中配置

1. 打开控制台 → 设置 → 频道
2. 启用目标频道
3. 填入所需的凭证信息（App Key、Secret 等）
4. 保存并重启

### 在配置文件中配置

编辑 `channels.yaml` 文件：

```yaml
dingtalk:
  enabled: true
  app_key: "your-app-key"
  app_secret: "your-app-secret"
```

## 注意事项

- 每个频道需要在对应平台创建 Bot 应用并获取凭证
- iMessage 频道仅支持 macOS
- 频道配置变更后需重启服务
