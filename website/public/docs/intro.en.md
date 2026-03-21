# Introduction

ResearchClaw is a self-hosted Research OS rather than a simple chat wrapper.

## What Exists Today

- a FastAPI service with a built-in control plane
- a web console and CLI
- multi-agent routing with per-agent workspaces and bindings
- a persistent research state for projects, workflows, notes, claims, evidences, experiments, artifacts, and drafts
- channel runtime for `console`, `telegram`, `discord`, `dingtalk`, `feishu`, `imessage`, `qq`, and `voice`
- provider management with multiple providers, multiple models per provider, and fallback chains
- standard `SKILL.md` skills, MCP clients, and custom channels
- automation triggers, cron jobs, heartbeat, and runtime observability
- structured research workflow execution, blocker remediation, project dashboards, and claim-graph APIs
- research utilities for papers, BibTeX, LaTeX, data analysis, browser use, file editing, and memory

## Current Status

The codebase is already strong on platform/runtime concerns:

- runtime bootstrapping
- control-plane APIs
- channels
- providers
- skills and MCP

The research workflow layer is now present, but still incomplete:

- there is a minimal workflow runtime, not a final evidence-matrix engine
- there is a claim/evidence graph, but not a strict validator yet
- there is experiment execution and remediation, but not every external executor is integrated
- there is draft and review flow support, but not a full submission bundle pipeline yet

## Runtime Building Blocks

- **Gateway Lite**: internal runtime boundary for runner, channels, cron, MCP, and automation state
- **Research runtime**: project/workflow/task state, stage workers, reminders, and remediation actions
- **Runner layer**: multi-agent manager plus per-agent workspaces
- **Control plane**: status, usage, channels, agents, sessions, and automation observability
- **Workspace model**: local working dir plus separate secret dir

## Read Next

- [Quick Start](./quickstart.md)
- [Deployment](./deployment.md)
- [Console](./console.md)
- [Config & Working Dir](./config.md)
