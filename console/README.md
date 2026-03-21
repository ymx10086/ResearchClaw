# ResearchClaw Console

React + Vite web console for the running ResearchClaw service.

## Current Pages

The console currently ships these main pages:

- Chat
- Papers
- Research
- Channels
- Sessions
- Cron Jobs
- Heartbeat
- Status
- Workspace
- Skills
- Agent Config
- Models
- Environments
- MCP

## Research Page

The Research page is the runtime UI for the current Research OS layer. It now includes:

- project dashboards
- workflow and stage summaries
- execution health
- recent blockers
- claim graph inspection
- remediation detail panels
- batch dispatch / execute / resume actions for blocker handling

## Development

Start the backend first:

```bash
researchclaw app
```

Then start the console dev server:

```bash
cd console
npm install
npm run dev
```

The Vite dev server proxies `/api` requests to `http://127.0.0.1:8088`.

## Production Build

```bash
cd console
npm run build
```

Build output is written to `console/dist`.

The backend automatically serves `console/dist` when the directory exists.

## Notes

- Do not edit `console/dist` manually.
- Use `npm run format` before committing large UI changes.
- The console is for the runtime service only; the marketing/docs website lives under `website/`.
