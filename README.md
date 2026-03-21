<div align="center">

# ResearchClaw

Local-first Research OS for papers, workflows, experiments, channels, and automation.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

[English](README.md) | [中文](README_zh.md)

</div>

## What It Is

ResearchClaw is not just a chat wrapper. The current codebase is a local-first FastAPI application that combines:

- a long-running app runtime with control-plane APIs
- a web console for chat, papers, research, channels, sessions, cron jobs, models, skills, workspace, environments, and MCP
- multi-agent routing with per-agent workspaces and binding rules
- a persistent research state layer for projects, workflows, tasks, notes, claims, evidences, experiments, artifacts, and drafts
- built-in channels for `console`, `telegram`, `discord`, `dingtalk`, `feishu`, `imessage`, `qq`, and `voice`
- model/provider management with multiple providers, multiple models per provider, and fallback chains
- standard `SKILL.md` support, Skills Hub search/install APIs, MCP client management, and custom channels
- automation triggers, cron jobs, heartbeat, proactive reminders, and runtime observability
- paper search/download, BibTeX utilities, LaTeX helpers, data analysis, browser/file tools, and structured research memory

It is still an Alpha project, but it is no longer just a platform shell. The code now includes a minimal research workflow runtime, claim/evidence graph, experiment tracking, blocker remediation, and project dashboard. The biggest remaining gaps are evidence-matrix quality, stronger claim-evidence validation, richer external execution adapters, and submission/reproducibility packaging.

## Quick Start

### 1) Clone and install from source

```bash
git clone https://github.com/MingxinYang/ResearchClaw.git
cd ResearchClaw
pip install -e .
```

### 2) Initialize the workspace

```bash
researchclaw init --defaults --accept-security
```

This creates:

- working dir: `~/.researchclaw`
- secret dir: `~/.researchclaw.secret`
- bootstrap Markdown files such as `SOUL.md`, `AGENTS.md`, `PROFILE.md`, and `HEARTBEAT.md`

### 3) Configure a model provider

```bash
researchclaw models config
```

Or add one directly:

```bash
researchclaw models add openai --type openai --model gpt-5 --api-key sk-...
```

Supported provider types in code today: `openai`, `anthropic`, `gemini`, `ollama`, `dashscope`, `deepseek`, `minimax`, `other`, `custom`.

### 4) Start the service

```bash
researchclaw app --host 127.0.0.1 --port 8088
```

Open [http://127.0.0.1:8088](http://127.0.0.1:8088).

If the page says `Console not found`, build the frontend once:

```bash
cd console
npm install
npm run build
```

The backend automatically serves `console/dist` when it exists.

### 5) Open the Research page

After startup, open the **Research** page in the console to:

- create a project
- inspect workflows, claims, and reminders
- view execution health and recent blockers
- dispatch, execute, or resume remediation work

## What You Get Today

### Runtime and control plane

- FastAPI app with `/api/health`, `/api/version`, `/api/control/*`, `/api/automation/*`, `/api/providers`, `/api/skills`, `/api/mcp`, `/api/workspace`, and more
- gateway-style runtime bootstrapping for runner, channels, cron, MCP, automation store, and config watcher
- runtime status snapshots for agents, sessions, channels, cron, heartbeat, skills, automation runs, and research services

### Research OS core

- project abstraction with persistent `project -> workflow -> task -> artifact` relationships
- workflow stages for `literature_search`, `paper_reading`, `note_synthesis`, `hypothesis_queue`, `experiment_plan`, `experiment_run`, `result_analysis`, `writing_tasks`, and `review_and_followup`
- structured notes including paper notes, idea notes, experiment notes, writing notes, and decision logs
- claim/evidence graph that can link papers, notes, experiments, PDF chunks, citations, generated tables, and artifacts
- experiment tracking with execution bindings, heartbeat/result ingestion, contract validation, result bundle validation, and compare APIs
- proactive workflow reminders plus remediation tasks for missing metrics, outputs, or artifact types
- project dashboards and blocker panels, including batch dispatch/execute/resume actions in the console and APIs

### Research tools and skills

Built-in tools registered by the agent include:

- `semantic_scholar_search`
- `bibtex_search`, `bibtex_add_entry`, `bibtex_export`
- `latex_template`, `latex_compile_check`
- `data_describe`, `data_query`
- `run_shell`, `read_file`, `write_file`, `edit_file`, `append_file`
- `browse_url`, `browser_use`, `send_file`, `memory_search`
- `skills_list`, `skills_activate`, `skills_read_file`

Bundled skills currently shipped in `src/researchclaw/agents/skills/` include:

- `arxiv`
- `browser_visible`
- `citation_network`
- `cron`
- `dingtalk_channel`
- `docx`
- `experiment_tracker`
- `figure_generator`
- `file_reader`
- `himalaya`
- `literature_review`
- `news`
- `paper_summarizer`
- `pdf`
- `pptx`
- `research_notes`
- `research_workflows`
- `xlsx`

### Workspace model

Runtime data lives under the working directory, while secrets are stored separately:

```text
~/.researchclaw/
├── config.json
├── jobs.json
├── chats.json
├── research/
│   └── state.json
├── sessions/
├── active_skills/
├── customized_skills/
├── papers/
├── references/
├── experiments/
├── memory/
├── md_files/
├── custom_channels/
└── researchclaw.log

~/.researchclaw.secret/
├── envs.json
└── providers.json
```

Provider credentials and persisted environment variables are intentionally kept out of the working directory.

## Development

Backend checks:

```bash
pip install -e ".[dev]"
PYTHONPATH=src pytest -q
```

Console build:

```bash
npm --prefix console run build
```

Website build:

```bash
corepack pnpm --dir website run build
```

Repo-wide helper:

```bash
scripts/check-ci.sh --skip-install
```

## Docs

Main documentation files in this repository:

- [Quick start](website/public/docs/quickstart.en.md)
- [Deployment](website/public/docs/deployment.en.md)
- [Console](website/public/docs/console.en.md)
- [Channels](website/public/docs/channels.en.md)
- [Skills](website/public/docs/skills.en.md)
- [MCP](website/public/docs/mcp.en.md)
- [Memory](website/public/docs/memory.en.md)
- [Config and working dir](website/public/docs/config.en.md)
- [CLI](website/public/docs/cli.en.md)
- [FAQ](website/public/docs/faq.en.md)
- [Roadmap](ROADMAP.md)

## Status

The current codebase is best described as:

- already strong on runtime infrastructure, control plane, channels, and provider/skill compatibility
- already usable for persistent research projects, workflow execution, experiment tracking, claim/evidence linking, and blocker handling
- still incomplete as a full autonomous research platform: evidence-matrix quality, rigorous validators, deeper execution backends, and submission packaging remain ahead
