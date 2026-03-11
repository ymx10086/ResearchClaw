# Channels

Channels connect ResearchClaw to messaging platforms so the same agent can be reached from multiple entry points.

## Built-in Channels

| Channel    | Notes                        |
| ---------- | ---------------------------- |
| `console`  | Built-in web console channel |
| `telegram` | Telegram bot                 |
| `discord`  | Discord bot                  |
| `dingtalk` | DingTalk bot                 |
| `feishu`   | Feishu bot                   |
| `qq`       | QQ channel integration       |
| `imessage` | macOS-only local deployment  |
| `voice`    | Twilio voice channel         |

## Configure via CLI

```bash
researchclaw channels config
researchclaw channels list
```

## Configure via `config.json`

Channel config lives under `channels` in `~/.researchclaw/config.json`:

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

## Multi-account Channels

You can configure per-channel account aliases with `channel_accounts`.
Each account is materialized as `channel:account_id` at runtime.

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

## Multi-channel Delivery

Automation trigger API supports one-to-many delivery:

- explicit `dispatches`
- `fanout_channels`
- fallback to `last_dispatch`

See [Deployment](./deployment.md) and protect automation routes with `RESEARCHCLAW_AUTOMATION_TOKEN`.

## Notes

- Channel credential changes can be applied via Control hot reload (`POST /api/control/reload`).
- Validate each platform's callback/webhook settings and permissions.
- Keep channel secrets in the secret store / envs, not in public repos.

## Control APIs

- `GET /api/control/channels`
- `GET /api/control/channels/runtime`
- `GET /api/control/channels/catalog`
- `GET /api/control/channels/custom`
- `POST /api/control/channels/custom/install`
- `DELETE /api/control/channels/custom/{key}`
- `GET /api/control/channels/accounts`
- `PUT /api/control/channels/accounts`
