# 频道配置

频道用于让同一个运行时从多个入口触达用户。

## 内置频道

| 频道       | 说明                |
| ---------- | ------------------- |
| `console`  | 内置 Web 控制台频道 |
| `telegram` | Telegram Bot        |
| `discord`  | Discord Bot         |
| `dingtalk` | 钉钉机器人          |
| `feishu`   | 飞书机器人          |
| `imessage` | 仅限 macOS 本地集成 |
| `qq`       | QQ 频道集成         |
| `voice`    | Twilio 语音频道     |

## 基础配置结构

频道配置位于 `config.json`：

```json
{
  "channels": {
    "console": { "enabled": true, "bot_prefix": "[BOT] " },
    "telegram": { "enabled": false, "bot_token": "" },
    "available": ["console"]
  }
}
```

## 频道账号映射

运行时还支持通过 `channel_accounts` 配置同一频道的多个账号别名。

```json
{
  "channel_accounts": {
    "telegram": {
      "lab": { "enabled": true, "bot_prefix": "[LAB] " }
    }
  }
}
```

运行时中它可能表现为 `telegram:lab`。

## 多 Agent 路由

`bindings` 可以按 channel、account、user、session 等条件，把消息路由到指定 agent。

```json
{
  "bindings": [
    {
      "agent_id": "research",
      "match": {
        "channel": "telegram",
        "account_id": "lab"
      }
    }
  ]
}
```

## 自定义频道

可以通过两种方式添加自定义频道：

- CLI：`researchclaw channels install` / `researchclaw channels remove`
- 控制面 API：`/api/control/channels/custom/*`

运行时代码会从 `custom_channels/` 加载这些自定义频道。

## 运维说明

- `last_dispatch` 会被持久化，heartbeat 和 automation fallback 会复用它
- 频道配置变更后可通过 control reload 应用
- 凭证尽量放在 secret store 或持久化 env 中管理
