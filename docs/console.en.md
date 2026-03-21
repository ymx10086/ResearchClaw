# Console

ResearchClaw ships a runtime console that is served by the backend when `console/dist` is available.

## Access

Start the service and open:

```text
http://127.0.0.1:8088
```

## Main Pages

- **Chat**: primary conversation UI
- **Papers**: paper search, local paper library, BibTeX references
- **Research**: project dashboards, workflows, execution health, blockers, claim graph, and remediation actions
- **Channels**: channel catalog, enablement, account mappings, bindings
- **Sessions**: inspect and delete routed sessions
- **Cron Jobs**: inspect, create, run, pause, resume, stop jobs
- **Heartbeat**: view heartbeat settings and current state
- **Status**: runtime health, usage, queue stats, automation counters
- **Workspace**: inspect working-dir files and key relations
- **Skills**: list, enable, disable, install from hub
- **Agent Config**: inspect current agent-facing settings
- **Models**: configure providers, active model, model presets, local downloads
- **Environments**: manage persisted environment variables
- **MCP**: add, edit, toggle, and delete MCP clients

## Research Page Highlights

The Research page is the main UI for the current Research OS layer. It includes:

- project overview and aggregated counts
- workflow lists and manual workflow execution
- execution health across workflows, experiments, bundles, and remediation pressure
- recent blockers with task-level and workflow-level actions
- remediation detail panels with per-task dispatch/execute and batch operations
- claim graph viewing for evidence inspection

## Development Mode

Run the backend first, then:

```bash
cd console
npm install
npm run dev
```

The dev server proxies `/api` to `http://127.0.0.1:8088`.

## Related APIs

- `GET /api/control/status`
- `GET /api/control/usage`
- `GET /api/research/projects/{project_id}/dashboard`
- `POST /api/research/projects/{project_id}/blockers/dispatch`
- `POST /api/research/projects/{project_id}/blockers/execute`
- `POST /api/research/projects/{project_id}/blockers/resume`
- `POST /api/research/workflows/{workflow_id}/execute`
- `GET /api/providers`
- `GET /api/skills`
- `GET /api/mcp`
- `GET /api/workspace`
