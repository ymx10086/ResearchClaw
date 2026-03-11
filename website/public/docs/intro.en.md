# Introduction

ResearchClaw is an AI research assistant focused on paper workflows, experiment tracking, and multi-channel collaboration.

## What It Helps With

- Paper search and tracking (ArXiv, Semantic Scholar, etc.)
- Reference and BibTeX workflows
- Summarization and research-note memory
- Experiment logging and periodic reminders
- Multi-channel delivery and automation triggers

## Runtime Building Blocks

- **Agent runtime**: Scholar agent + tool/skill orchestration
- **Control plane**: status, sessions, cron, and automation run observability
- **Channel layer**: console + external messaging platforms
- **Workspace model**: local working dir plus separate secret dir

## Minimal Startup

```bash
researchclaw init --defaults --accept-security
researchclaw models config
researchclaw app --host 127.0.0.1 --port 8088
```

Then open `http://127.0.0.1:8088`.

## Read Next

- [Quick Start](./quickstart.md)
- [Deployment](./deployment.md)
- [Config & Working Dir](./config.md)
