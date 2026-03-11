# Heartbeat

Heartbeat is the periodic scheduler loop used by ResearchClaw for proactive tasks.

## What It Drives

- Skill cron prompts (when configured in skills)
- Built-in periodic checks
- Delivery to configured channels

## Where to Configure

Heartbeat settings are read from `config.json` (with legacy fallback):

```json
{
  "agents": {
    "defaults": {
      "heartbeat": {
        "enabled": true,
        "every": "30m",
        "target": "last"
      }
    }
  }
}
```

Also available via env defaults:

- `RESEARCHCLAW_HEARTBEAT_ENABLED`
- `RESEARCHCLAW_HEARTBEAT_INTERVAL` (minutes)

## Operational Tips

- Keep interval practical (for example `30m` or `1h`).
- Ensure at least one dispatch channel is available for proactive messages.
- Use `/api/control/status` to inspect cron/heartbeat runtime state.
