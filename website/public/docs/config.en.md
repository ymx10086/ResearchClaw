# Configuration & Working Directory

ResearchClaw keeps runtime data and secrets in different places.

## Default Paths

- working dir: `~/.researchclaw`
- secret dir: `~/.researchclaw.secret`

Override with:

- `RESEARCHCLAW_WORKING_DIR`
- `RESEARCHCLAW_SECRET_DIR`
- `RESEARCHCLAW_RESEARCH_DIR`
- `RESEARCHCLAW_RESEARCH_STATE_FILE`

## Working Directory Layout

```text
~/.researchclaw/
├── config.json
├── jobs.json
├── chats.json
├── research/
│   └── state.json
├── PROFILE.md
├── SOUL.md
├── AGENTS.md
├── HEARTBEAT.md
├── md_files/
├── sessions/
├── active_skills/
├── customized_skills/
├── papers/
├── references/
├── experiments/
├── memory/
├── custom_channels/
└── researchclaw.log
```

Additional runtime artifacts such as `heartbeat.json`, digests, reminders, project research state, or agent-specific workspaces can appear over time.

## Research State

The Research OS layer keeps its structured state separately from chat/session memory:

- default directory: `~/.researchclaw/research/`
- default file: `state.json`

That state contains projects, workflows, tasks, claims, evidences, notes, experiments, artifacts, and drafts.

## Secret Directory Layout

```text
~/.researchclaw.secret/
├── envs.json
└── providers.json
```

`providers.json` is the canonical provider store. `envs.json` is the canonical persisted environment-variable store.

## Bootstrap Markdown Files

The init/bootstrap flow expects these files to exist and be customized:

- `SOUL.md`
- `AGENTS.md`
- `PROFILE.md`
- `HEARTBEAT.md`

Those files shape agent behavior more than many legacy config knobs do.

## Example `config.json`

```json
{
  "language": "en",
  "show_tool_details": true,
  "channels": {
    "console": { "enabled": true, "bot_prefix": "[BOT] " },
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
  "agents": {
    "defaults": {
      "agent_id": "main",
      "heartbeat": {
        "enabled": true,
        "every": "1h",
        "target": "last",
        "active_hours": { "start": "08:00", "end": "22:00" }
      }
    },
    "list": [
      { "id": "main", "enabled": true },
      {
        "id": "research",
        "workspace": "agents/research",
        "enabled": true,
        "autostart": true
      }
    ]
  },
  "mcp": {
    "clients": {}
  },
  "automation": {
    "mappings": {}
  }
}
```

## Notes

- active provider credentials usually come from `providers.json`, not from `config.json`
- `bindings` can also be stored under `agents.bindings`; the runtime accepts both forms
- heartbeat still has legacy fallback keys, but `agents.defaults.heartbeat` is the preferred shape
- the gateway runtime exports `RESEARCHCLAW_RESEARCH_STATE_PATH` internally so research APIs, skills, and runners share the same state file
