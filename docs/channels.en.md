# Channels

Channels let the same runtime reach users from multiple entry points.

## Built-in Channels

| Channel    | Notes                        |
| ---------- | ---------------------------- |
| `console`  | built-in web console channel |
| `telegram` | Telegram bot                 |
| `discord`  | Discord bot                  |
| `dingtalk` | DingTalk bot                 |
| `feishu`   | Feishu bot                   |
| `imessage` | macOS-only local integration |
| `qq`       | QQ channel integration       |
| `voice`    | Twilio voice channel         |

## Basic Config Shape

Channel configuration lives in `config.json`:

```json
{
  "channels": {
    "console": { "enabled": true, "bot_prefix": "[BOT] " },
    "telegram": { "enabled": false, "bot_token": "" },
    "available": ["console"]
  }
}
```

## Channel Accounts

The runtime also supports per-channel account aliases through `channel_accounts`.

```json
{
  "channel_accounts": {
    "telegram": {
      "lab": { "enabled": true, "bot_prefix": "[LAB] " }
    }
  }
}
```

At runtime that can materialize as `telegram:lab`.

## Multi-Agent Routing

Bindings route traffic to a specific agent by channel, account, user, or session match.

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

## Custom Channels

You can add custom channels in two ways:

- CLI: `researchclaw channels install` / `researchclaw channels remove`
- control-plane APIs: `/api/control/channels/custom/*`

The runtime loads custom channel code from `custom_channels/`.

## Operational Notes

- `last_dispatch` is persisted and reused by heartbeat or automation fan-out fallbacks
- channel changes can be applied via control reload
- keep credentials in the secret store or persisted envs whenever possible
