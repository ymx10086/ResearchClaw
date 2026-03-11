# Console

ResearchClaw includes a built-in web console for day-to-day operations.

## Access

After service startup, open `http://<host>:<port>` (default `http://127.0.0.1:8088`).

## Core Areas

### Chat

- Talk with the Scholar agent
- Manage multi-session conversations
- Review message history

### Settings

- Configure model providers and models
- Manage channel enablement and credentials
- Manage persisted environment variables
- Manage skills (enable/disable)

### Status / Control Plane

- Runtime health and uptime
- Model usage metrics (requests / success / fallback / token estimate)
- Channel runtime queue/worker stats
- Cron runtime stats
- Automation run statistics (queued/running/succeeded/failed)
- Agent list and session observability

## Related APIs

- `GET /api/control/status`
- `GET /api/control/usage`
- `GET /api/control/channels/runtime`
- `GET /api/control/automation/runs`
- `GET /api/control/agents`
- `GET /api/control/sessions`
- `POST /api/control/reload`

For production access patterns, see [Deployment](./deployment.md).
