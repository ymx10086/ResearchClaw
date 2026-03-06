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

### Installation

```bash
pip install researchclaw
```

### Initialize

```bash
researchclaw init --defaults
```

This sets up your working directory (`~/.researchclaw`) and configures your LLM provider.

### Launch

```bash
researchclaw app
```

Open [http://127.0.0.1:8088/](http://127.0.0.1:8088/) in your browser.

### One-liner Install

```bash
curl -fsSL https://researchclaw.github.io/install.sh | bash
```

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
     ├── Model: OpenAI / Anthropic / DashScope / Local models
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
researchclaw env set OPENAI_API_KEY=sk-...

# Or Anthropic
researchclaw env set ANTHROPIC_API_KEY=sk-ant-...

# Or use local models via Ollama
researchclaw providers add ollama
```

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
researchclaw papers search # Search for papers from CLI
researchclaw papers list   # List saved papers
researchclaw skills list   # List available skills
researchclaw skills add    # Install a skill from the hub
researchclaw env list      # List environment variables
researchclaw providers     # Manage LLM providers
researchclaw cron          # Manage scheduled tasks
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
