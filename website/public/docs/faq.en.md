# FAQ

This FAQ reflects the current repository state.

### What is already production-like today?

The strongest parts today are the runtime platform pieces and the stateful research foundation:

- app bootstrapping and control-plane APIs
- channels, providers, skills, MCP, automation, and the console
- project/workflow/task state
- claim/evidence graph
- experiment tracking, result-bundle ingestion, and blocker remediation

What is still incomplete is the higher-level research quality layer: evidence matrix scoring, stronger claim validators, richer external execution adapters, and submission packaging.

### Which providers are supported?

Provider types in code today are `openai`, `anthropic`, `gemini`, `ollama`, `dashscope`, `deepseek`, `minimax`, `other`, and `custom`.

### Which channels are built in?

`console`, `telegram`, `discord`, `dingtalk`, `feishu`, `imessage`, `qq`, and `voice`.

### Where is my data stored?

- working data: `~/.researchclaw`
- secrets: `~/.researchclaw.secret`

The secret dir stores `envs.json` and `providers.json`.

The research workflow state is stored under `~/.researchclaw/research/state.json` unless you override the research path.

### Why does `/` show `Console not found`?

The backend can start without prebuilt console assets. Build them once:

```bash
cd console
npm install
npm run build
```

### How do I secure automation triggers?

Set `RESEARCHCLAW_AUTOMATION_TOKEN` on the server. Requests must send the same token via `Authorization: Bearer <token>`, `x-researchclaw-token`, or `x-researchclaw-automation-token`.

### Why can plain `pytest` fail in a fresh checkout?

If the package is not installed editable yet, Python may not find `researchclaw`. Either run:

```bash
pip install -e ".[dev]"
```

or:

```bash
PYTHONPATH=src pytest -q
```

### Does the console include research workflow controls?

Yes. The current console includes a dedicated Research page with:

- project dashboards
- workflow execution
- execution health
- recent blockers
- remediation drill-down and batch actions
