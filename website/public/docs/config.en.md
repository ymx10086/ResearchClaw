# Configuration & Working Directory

ResearchClaw keeps runtime data in a workspace directory and secrets in a separate secret directory.

## Default Paths

- Working directory: `~/.researchclaw`
- Secret directory: `~/.researchclaw.secret`

You can override both with environment variables:

- `RESEARCHCLAW_WORKING_DIR`
- `RESEARCHCLAW_SECRET_DIR`

## Working Directory Layout

```text
~/.researchclaw/
├── config.json            # Main runtime config
├── jobs.json              # Persistent cron jobs
├── chats.json             # Chat/session history
├── PROFILE.md             # User/research profile
├── HEARTBEAT.md           # Heartbeat checklist
├── active_skills/         # Enabled skills
├── customized_skills/     # Local custom skills
├── papers/                # Cached/downloaded papers
├── references/            # References/BibTeX related data
├── experiments/           # Experiment tracking data
├── memory/                # Memory artifacts
└── researchclaw.log       # Runtime logs
```

## Secret Directory Layout

```text
~/.researchclaw.secret/
├── envs.json              # Persisted env vars
└── providers.json         # Model provider configs
```

## Key Runtime Config (`config.json`)

```json
{
  "language": "en",
  "show_tool_details": true,
  "channels": {
    "console": { "enabled": true, "bot_prefix": "[BOT] " },
    "dingtalk": { "enabled": false },
    "feishu": { "enabled": false },
    "available": ["console"]
  },
  "channel_accounts": {
    "telegram": {
      "lab": { "enabled": true, "bot_prefix": "[LAB] " }
    }
  },
  "bindings": [
    {
      "agent_id": "research",
      "match": { "channel": "telegram", "account_id": "lab" }
    }
  ],
  "model_fallbacks": [
    { "provider": "anthropic", "model_name": "claude-sonnet-4-20250514" }
  ],
  "agents": {
    "defaults": {
      "heartbeat": {
        "enabled": false,
        "every": "30m",
        "target": "last"
      }
    }
  },
  "mcp": {
    "clients": {}
  }
}
```

## CLI for Configuration

```bash
researchclaw init
researchclaw channels config
researchclaw models config
researchclaw env list
researchclaw env set OPENAI_API_KEY sk-...
```

## Important Advanced Keys

- `channel_accounts`: per-channel account overrides; each account becomes `channel:account_id`.
- `bindings`: routing rules to map channel/account/user/session to different agent instances.
- `model_fallbacks`: backup provider/model chain used when the primary model call fails.

## Deployment-related Environment Variables

| Variable                        | Purpose                                |
| ------------------------------- | -------------------------------------- |
| `RESEARCHCLAW_HOST`             | Default host for `researchclaw app`    |
| `RESEARCHCLAW_PORT`             | Default port for `researchclaw app`    |
| `RESEARCHCLAW_AUTOMATION_TOKEN` | Auth token for automation trigger APIs |
| `RESEARCHCLAW_CORS_ORIGINS`     | CORS allow-list                        |
| `RESEARCHCLAW_DOCS_ENABLED`     | Enable FastAPI docs (`/docs`)          |
| `RESEARCHCLAW_LOG_LEVEL`        | Runtime log level                      |

See [Deployment](./deployment.md) for production setup.
