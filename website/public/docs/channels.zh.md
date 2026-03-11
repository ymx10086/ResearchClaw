# 频道配置

频道用于把同一个 ResearchClaw Agent 接入多个消息入口。

## 内置频道

| 频道       | 说明                  |
| ---------- | --------------------- |
| `console`  | 内置 Web 控制台频道   |
| `telegram` | Telegram Bot          |
| `discord`  | Discord Bot           |
| `dingtalk` | 钉钉机器人            |
| `feishu`   | 飞书机器人            |
| `qq`       | QQ 频道集成           |
| `imessage` | 仅支持 macOS 本地部署 |
| `voice`    | Twilio 语音频道       |

## 通过 CLI 配置

```bash
researchclaw channels config
researchclaw channels list
```

## 通过 `config.json` 配置

频道配置位于 `~/.researchclaw/config.json` 的 `channels` 字段：

```json
{
  "channels": {
    "console": { "enabled": true, "bot_prefix": "[BOT] " },
    "dingtalk": {
      "enabled": true,
      "client_id": "your-client-id",
      "client_secret": "your-client-secret",
      "bot_prefix": "[BOT] "
    },
    "available": ["console", "dingtalk"]
  }
}
```

## 多账号频道

可以通过 `channel_accounts` 配置同一频道的多个账号实例。
运行时会将账号实例化为 `channel:account_id` 形式。

```json
{
  "channels": {
    "telegram": { "enabled": true, "bot_prefix": "[BOT] " },
    "available": ["console", "telegram", "telegram:lab"]
  },
  "channel_accounts": {
    "telegram": {
      "lab": { "enabled": true, "bot_prefix": "[LAB] " }
    }
  }
}
```

## 多渠道投递

自动化触发 API 支持一对多投递：

- 显式 `dispatches`
- `fanout_channels`
- `last_dispatch` 回退

请在部署时设置 `RESEARCHCLAW_AUTOMATION_TOKEN`，详见 [部署指南](./deployment.md)。

## 注意事项

- 频道凭证调整后可通过控制面热重载（`POST /api/control/reload`）即时生效。
- 需确保平台侧回调/webhook 配置和权限正确。
- 密钥建议放在密钥目录或环境变量，不要提交到公开仓库。

## 控制面相关 API

- `GET /api/control/channels`
- `GET /api/control/channels/runtime`
- `GET /api/control/channels/catalog`
- `GET /api/control/channels/custom`
- `POST /api/control/channels/custom/install`
- `DELETE /api/control/channels/custom/{key}`
- `GET /api/control/channels/accounts`
- `PUT /api/control/channels/accounts`
