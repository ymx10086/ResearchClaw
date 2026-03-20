<div align="center">

# 🔬 ResearchClaw

**Your AI-Powered Research Assistant**

An intelligent agent-based assistant designed specifically for academic researchers — powered by LLMs, grounded in the scientific workflow.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

[English](README.md) | [中文](README_zh.md)

</div>

---

## ✨ What is ResearchClaw?

ResearchClaw is an AI research assistant that runs on **your own machine**. Built on the [AgentScope](https://github.com/modelscope/agentscope) framework, it uses a ReAct agent with specialized research tools to help you:

- 📄 **Search & discover papers** — ArXiv, Semantic Scholar, Google Scholar
- 📚 **Manage references** — BibTeX import/export, citation graph exploration
- 🔍 **Read & summarize papers** — Extract key findings from PDFs
- 📊 **Analyze data** — Statistical analysis, visualization, experiment tracking
- ✍️ **Write & review** — LaTeX assistance, literature review generation
- ⏰ **Stay updated** — Daily paper digests, deadline reminders, citation alerts
- 🧠 **Build knowledge** — Persistent research notes and memory across sessions

## 🚀 Quick Start

### 1) Install (from this repository)

```bash
pip install -e ".[dev]"
```

Run this in the repository root.

### 2) Initialize workspace

```bash
researchclaw init --defaults --accept-security
```

This creates `~/.researchclaw` and bootstrap files.

### 3) Configure your model provider

```bash
researchclaw models config
# or:
researchclaw models add openai --type openai --model gpt-4o --api-key sk-...
```

The first provider you add is activated automatically. If you add more later,
switch the active one from the Models page or rerun `researchclaw models config`.

### 4) Start service

```bash
researchclaw app --host 127.0.0.1 --port 8088
```

Open [http://127.0.0.1:8088](http://127.0.0.1:8088).

### 5) Frontend (Console) development

Run backend first:

```bash
researchclaw app
```

In another terminal, start the frontend dev server:

```bash
cd console
npm install
npm run dev
```

Then open the Vite URL (usually [http://localhost:5173](http://localhost:5173)).
The frontend dev server proxies `/api` requests to `http://127.0.0.1:8088`.

To build production frontend assets:

```bash
cd console
npm run build
```

`console/dist` will be served automatically by the backend when available.

### 6) One-liner install (macOS / Linux)

```bash
curl -fsSL https://researchclaw.github.io/install.sh | bash
```

### Local CI checks

Run the same checks used by GitHub Actions before pushing:

```bash
scripts/check-ci.sh
```

If dependencies are already installed, use:

```bash
scripts/check-ci.sh --skip-install
```

## 🚢 Deployment

### Single-machine deployment (recommended baseline)

1. Set persistent paths and bind address.
2. Start with a process manager.

```bash
export RESEARCHCLAW_WORKING_DIR=/data/researchclaw
export RESEARCHCLAW_SECRET_DIR=/data/researchclaw.secret
export RESEARCHCLAW_HOST=0.0.0.0
export RESEARCHCLAW_PORT=8088
export RESEARCHCLAW_AUTOMATION_TOKEN=change-me

researchclaw app --host 0.0.0.0 --port 8088
```

Health check endpoint: `GET /api/health`

### Docker deployment (self-build)

```bash
docker build -f deploy/Dockerfile -t researchclaw:local .
docker run -d \
  --name researchclaw \
  -p 8088:8088 \
  -e PORT=8088 \
  -e RESEARCHCLAW_WORKING_DIR=/app/working \
  -e RESEARCHCLAW_SECRET_DIR=/app/working.secret \
  -e RESEARCHCLAW_AUTOMATION_TOKEN=change-me \
  -v researchclaw-working:/app/working \
  -v researchclaw-secret:/app/working.secret \
  researchclaw:local
```

### Production checklist

- Put ResearchClaw behind Nginx/Caddy and enable HTTPS.
- Persist both working dir and secret dir.
- Set `RESEARCHCLAW_AUTOMATION_TOKEN` before exposing automation APIs.
- Restrict inbound IPs for admin/internal endpoints when possible.
- Monitor `/api/health` and `/api/control/status`.

## 📝 Recent Updates

### 2026-03-11

- Added automation trigger APIs for external systems:
  token-protected `/api/automation/triggers/agent` supports async execution, stored run history, and optional multi-channel fan-out delivery (`dispatches` / `fanout_channels`).
- Expanded control-plane observability:
  `/api/control/status` now includes runtime snapshots for runner sessions, channel queues/workers, cron runtime stats, and automation success/failure counters.
- Added model fallback + usage observability:
  streaming and non-streaming chat now support fallback chains, and control plane exposes usage/fallback counters via `/api/control/usage` and `runtime.runner.usage`.
- Upgraded Console Status page with operational metrics:
  registered channel count, queue backlog, in-progress keys, and automation success/failure cards.
- Added channel operations APIs and console controls:
  custom channel plugin install/remove (`/api/control/channels/custom/*`), account mapping management (`/api/control/channels/accounts`), and routing bindings management (`/api/control/bindings`).
- Added a richer model/provider configuration UI:
  multiple preset platforms, per-provider `base_url`, selectable preset models, and manual model entry in the same card.
- Extended provider storage and APIs to support multiple models per provider while keeping backward compatibility with the old single-model format.
- Improved web console stability:
  fixed `/models` static asset fallback handling, `HEAD /` support, provider names containing `/`, and a React rendering error on object-valued workspace fields.
- Hardened skill compatibility and routing:
  `SKILL.md` now recognizes OpenClaw/ClawHub-style metadata such as `user-invocable` and `disable-model-invocation`, and Python skills can be loaded from normalized runtime exports like `tools`, `TOOLS`, `register()`, and `get_tools()`.
- Fixed experiment tracker skill argument compatibility so extra fields such as `status` and alternate `experiment_id` casing no longer crash tool execution.
- Refreshed README and website docs to match current runtime behavior, with a dedicated deployment guide (single-machine, Docker self-build, and production checklist).

## 🏗️ Architecture

```
User ─→ Console (Web UI) / CLI / Slack / Email
          │
          ▼
     ResearchClaw App (FastAPI + Uvicorn)
          │
          ▼
     ScholarAgent (ReActAgent)
     ├── Research Tools: ArXiv, Semantic Scholar, PDF Reader, BibTeX, LaTeX
     ├── Data Tools: pandas, matplotlib, scipy analysis
     ├── General Tools: Shell, File I/O, Browser, Memory Search
     ├── Skills: Paper Summarizer, Literature Review, Experiment Tracker, ...
     ├── Memory: Research Memory + Knowledge Base + Auto-compaction
     ├── Model: OpenAI / Anthropic / Gemini / DashScope / Local models
     └── Crons: Daily Paper Digest, Deadline Reminder, Citation Alerts
```

## 🔧 Built-in Research Tools

| Tool | Description |
|------|-------------|
| `arxiv_search` | Search and download papers from ArXiv |
| `semantic_scholar_search` | Query Semantic Scholar for papers, authors, citations |
| `paper_reader` | Extract text, figures, and tables from PDF papers |
| `bibtex_manager` | Parse, generate, and manage BibTeX references |
| `latex_helper` | LaTeX syntax assistance and template generation |
| `data_analysis` | Statistical analysis with pandas, numpy, scipy |
| `plot_generator` | Create publication-quality figures with matplotlib |
| `shell` | Execute shell commands |
| `file_io` | Read, write, and edit files |
| `browser_control` | Web browsing and information gathering |
| `memory_search` | Search through research notes and conversation history |
| `get_current_time` | Get current date and time |

## 📦 Extensible Skills

ResearchClaw ships with research-focused skills that can be customized:

- **arxiv** — Advanced ArXiv search with category filters and alerts
- **paper_summarizer** — Multi-level paper summarization (abstract → detailed)
- **literature_review** — Generate structured literature reviews
- **citation_network** — Explore citation graphs and find related work
- **experiment_tracker** — Log experiments, parameters, and results
- **figure_generator** — Create publication-ready figures
- **research_notes** — Structured note-taking with tagging
- **pdf** — Advanced PDF processing and annotation

### Standard Skill Support

ResearchClaw now supports standard SKILL-based skills beyond its built-ins.

- Preferred skill format: one directory per skill, with a required `SKILL.md`
- Optional extra files: `references/` and `scripts/`
- Supported discovery locations:
  - project-local `skills/` (OpenClaw-style)
  - project-local `.agents/skills/`
  - project-local `.researchclaw/skills/`
  - user-level `~/.agents/skills/`
  - user-level `~/.researchclaw/skills/`
- Built-in Python skills now also ship with `SKILL.md` so they follow the same contract

At runtime, ResearchClaw discovers these skills, syncs them into `active_skills/`, and exposes:

- `skills_list()` to inspect available skills
- `skills_activate(name)` to load the full `SKILL.md` plus bundled file inventory
- `skills_read_file(name, path)` to read `SKILL.md`, `references/*`, or `scripts/*`

## ⚙️ Configuration

ResearchClaw stores all data locally in `~/.researchclaw/`:

```
~/.researchclaw/
├── config.json          # Main configuration
├── .env                 # API keys and environment variables
├── jobs.json            # Scheduled tasks (paper digests, reminders)
├── chats.json           # Conversation history
├── active_skills/       # Currently active skills
├── customized_skills/   # Your custom skills
├── memory/              # Research notes and knowledge base
├── papers/              # Downloaded papers cache
├── references/          # BibTeX library
└── experiments/         # Experiment tracking data
```

### LLM Provider Setup

ResearchClaw supports multiple LLM providers:

```bash
# Set up with OpenAI
researchclaw models add openai --type openai --model gpt-4o --api-key sk-...

# Or Anthropic
researchclaw models add anthropic --type anthropic --model claude-3-5-sonnet --api-key sk-ant-...

# Or Google Gemini (Gemini API / AI Studio key)
researchclaw models add gemini --type gemini --model gemini-2.5-flash --api-key AIza... --base-url https://generativelanguage.googleapis.com/v1beta/openai/

# Or use local models via Ollama
researchclaw models add ollama --type ollama --model qwen3:8b --base-url http://localhost:11434/v1
```

The web UI also includes a `Google Gemini` preset in the Models page.
The first provider added via CLI becomes the active provider automatically.

## 🤖 Agent Commands

In the chat interface, use these commands:

| Command | Description |
|---------|-------------|
| `/new` | Start a new conversation |
| `/compact` | Compress conversation memory |
| `/clear` | Clear all history |
| `/history` | Show conversation statistics |
| `/papers` | List recently discussed papers |
| `/refs` | Show current reference library |

## 📋 CLI Reference

```bash
researchclaw init          # Interactive setup wizard
researchclaw app           # Start the web server
researchclaw models list   # List model providers
researchclaw channels list # List channel configuration
researchclaw env list      # List persisted environment variables
researchclaw skills list   # List available skills
researchclaw cron list     # List scheduled jobs via API
researchclaw daemon status # Runtime status from control plane
```

## 🛡️ Privacy & Security

- **All data stays local** — your papers, notes, and API keys never leave your machine
- **No telemetry** — ResearchClaw does not collect usage data
- **You control the LLM** — choose your provider, use local models for sensitive research

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgements

ResearchClaw's channel, scheduling, and console interaction design are inspired by the architecture of [CoPaw](https://github.com/agentscope-ai/CoPaw).
Thanks to the CoPaw project for providing a practical and well-validated reference implementation.

![微信二维码](imgs/wx-20260317.jpg)
