<div align="center">
  <img src="console/public/researchclaw-logo.png" alt="ResearchClaw logo" width="340">

# ResearchClaw

> Local-first Research OS for papers, workflows, experiments, channels, and automation.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-2563eb.svg?style=flat-square)](https://python.org)
![FastAPI Runtime](https://img.shields.io/badge/runtime-FastAPI-0f766e.svg?style=flat-square)
![Web Console](https://img.shields.io/badge/interface-Web%20Console-f97316.svg?style=flat-square)
![Skills + MCP](https://img.shields.io/badge/extensibility-Skills%20%2B%20MCP-111827.svg?style=flat-square)
![Status Alpha](https://img.shields.io/badge/status-Alpha-b45309.svg?style=flat-square)
[![License](https://img.shields.io/badge/license-Apache%202.0-16a34a.svg?style=flat-square)](LICENSE)

[English](README.md) | [中文](README_zh.md) | [Docs](website/public/docs/intro.en.md) | [Roadmap](ROADMAP.md) | [Research-Equality Ecosystem](https://github.com/orgs/Research-Equality/repositories)

Part of the [Research-Equality](https://github.com/orgs/Research-Equality/repositories) ecosystem for AI-native research workflows.

Persistent research state · Multi-agent runtime · Skills + MCP · Automation + channels

[Why ResearchClaw](#why-researchclaw) • [Quick Start](#quick-start) • [Research-Equality Ecosystem](#research-equality-ecosystem) • [What You Get Today](#what-you-get-today) • [Docs](#docs)

</div>

<a id="why-researchclaw"></a>
## Why ResearchClaw

ResearchClaw is the runtime and workspace layer of the broader Research-Equality stack. It keeps long-horizon research work durable: projects, workflows, claims, evidence, experiments, artifacts, reminders, channels, and automation all live in one local-first system instead of dissolving across chat threads, terminals, and scattered folders.

| Common AI research workflow pain | What ResearchClaw does instead |
| --- | --- |
| Research work disappears into one-off chats or shell history | Persists `project -> workflow -> task -> artifact` state with notes, claims, evidence, drafts, and reminders |
| Tools for search, execution, writing, and follow-up are split apart | Puts console, automation, channels, APIs, papers, experiments, and memory into one runtime |
| It is hard to hand work over between web, terminal, and messaging surfaces | Exposes the same research state through the web console, IM channels, cron jobs, sessions, and control-plane APIs |
| Skills, providers, and external tools are glued together ad hoc | Standardizes `SKILL.md`, MCP, provider routing, fallback chains, and per-agent workspace rules |

Under the hood, the current codebase combines:

- a long-running app runtime with control-plane APIs
- a web console for chat, papers, research, channels, sessions, cron jobs, models, skills, workspace, environments, and MCP
- multi-agent routing with per-agent workspaces and binding rules
- a persistent research state layer for projects, workflows, tasks, notes, claims, evidence, experiments, artifacts, and drafts
- built-in channels for `console`, `telegram`, `discord`, `dingtalk`, `feishu`, `imessage`, `qq`, and `voice`
- model/provider management with multiple providers, multiple models per provider, and fallback chains
- standard `SKILL.md` support, Skills Hub search/install APIs, MCP client management, and custom channels
- automation triggers, cron jobs, heartbeat, proactive reminders, and runtime observability
- paper search/download, BibTeX utilities, LaTeX helpers, data analysis, browser/file tools, and structured research memory

It is still an Alpha project, but it is no longer just a platform shell. The code now includes a minimal research workflow runtime, claim/evidence graph, experiment tracking, blocker remediation, and project dashboard. The biggest remaining gaps are evidence-matrix quality, stronger claim-evidence validation, richer external execution adapters, and submission/reproducibility packaging.

<a id="quick-start"></a>
## Quick Start

### 1. Clone and install from source

```bash
git clone https://github.com/MingxinYang/ResearchClaw.git
cd ResearchClaw
pip install -e .
```

### 2. Initialize the workspace

```bash
researchclaw init --defaults --accept-security
```

This creates:

- working dir: `~/.researchclaw`
- secret dir: `~/.researchclaw.secret`
- bootstrap Markdown files such as `SOUL.md`, `AGENTS.md`, `PROFILE.md`, and `HEARTBEAT.md`

### 3. Configure a model provider

```bash
researchclaw models config
```

Or add one directly:

```bash
researchclaw models add openai --type openai --model gpt-5 --api-key sk-...
```

Supported provider types in code today: `openai`, `anthropic`, `gemini`, `ollama`, `dashscope`, `deepseek`, `minimax`, `other`, `custom`.

### 4. Start the service

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

### 5. Open the Research page

After startup, open the **Research** page in the console to:

- create a project
- inspect workflows, claims, and reminders
- view execution health and recent blockers
- dispatch, execute, or resume remediation work

<a id="research-equality-ecosystem"></a>
## Research-Equality Ecosystem

ResearchClaw works best as the persistent runtime and workspace in a larger skill ecosystem. The companion repositories below cover stage-specific research work, while the awesome repository maps the wider AI scientist and AI-for-research landscape.

Browse the full organization here: [Research-Equality repositories](https://github.com/orgs/Research-Equality/repositories)

| Repository | Role next to ResearchClaw | Use it when |
| --- | --- | --- |
| [RE-idea-generation](https://github.com/Research-Equality/RE-idea-generation) | authoritative skills for idea generation, problem discovery, and direction exploration | you need to turn vague interests into defensible research directions |
| [RE-literature-discovery](https://github.com/Research-Equality/RE-literature-discovery) | authoritative skills for literature discovery, authority-aware ranking, evidence synthesis, and survey writing | you want auditable paper search, filtering, and review workflows |
| [RE-research-design](https://github.com/Research-Equality/RE-research-design) | authoritative skills for research design, method formalization, experiment planning, and evaluation design | you need a stronger design layer before implementation starts |
| [RE-experiment](https://github.com/Research-Equality/RE-experiment) | authoritative skills for experiment planning, implementation, validation, and analysis | you are reproducing baselines, running ablations, or tightening experiment traceability |
| [RE-paper-writing](https://github.com/Research-Equality/RE-paper-writing) | authoritative skills for paper planning, drafting, revision, LaTeX workflows, and submission QA | you want the writing and submission stack to stay connected to real artifacts |
| [awesome-ai-scientists](https://github.com/Research-Equality/awesome-ai-scientists) | the `Awesome-AI-Research` landscape map for AI-native research systems, workflow modules, benchmarks, surveys, datasets, and meta-resources | you want a broader map of AI scientist systems and AI research tooling beyond this project |

A practical pairing is `ResearchClaw` plus one or two `RE-*` repositories for the stage you are actively pushing, with `awesome-ai-scientists` as the discovery layer for adjacent tools, systems, and benchmarks.

<a id="what-you-get-today"></a>
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

<a id="docs"></a>
## Docs

Main documentation files in this repository:

- [Intro](website/public/docs/intro.en.md)
- [Quick start](website/public/docs/quickstart.en.md)
- [Deployment](website/public/docs/deployment.en.md)
- [Console](website/public/docs/console.en.md)
- [Channels](website/public/docs/channels.en.md)
- [Skills](website/public/docs/skills.en.md)
- [MCP](website/public/docs/mcp.en.md)
- [Memory](website/public/docs/memory.en.md)
- [Config and working dir](website/public/docs/config.en.md)
- [Commands](website/public/docs/commands.en.md)
- [CLI](website/public/docs/cli.en.md)
- [Heartbeat](website/public/docs/heartbeat.en.md)
- [Community](website/public/docs/community.en.md)
- [Contributing](website/public/docs/contributing.en.md)
- [FAQ](website/public/docs/faq.en.md)
- [Roadmap](ROADMAP.md)

## Status

The current codebase is best described as:

- already strong on runtime infrastructure, control plane, channels, and provider/skill compatibility
- already usable for persistent research projects, workflow execution, experiment tracking, claim/evidence linking, and blocker handling
- still incomplete as a full autonomous research platform: evidence-matrix quality, rigorous validators, deeper execution backends, and submission packaging remain ahead
