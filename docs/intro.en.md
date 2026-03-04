# Introduction

ResearchClaw is an AI-powered research assistant that helps researchers track papers, manage references, log experiments, and analyze data.

## Key Features

- **Paper Search & Tracking**: Search ArXiv, Semantic Scholar, and more. Auto-track new publications in your fields.
- **Reference Management**: BibTeX management, citation formatting, literature search.
- **Experiments & Analysis**: Experiment logging, data analysis, visualization.
- **Multi-Channel Support**: DingTalk, Feishu, QQ, Discord, iMessage, and more.
- **Skills**: Built-in research skills, customizable extensions, and cron tasks.
- **Local Control**: Data stored locally, cloud deployment optional.

## Architecture

ResearchClaw consists of the following modules:

- **Agent Engine**: A ReAct-based agent that understands user intent and invokes tools.
- **Skills System**: An extensible skill framework supporting custom research skills.
- **Channel Layer**: A unified messaging interface supporting multiple IM platforms.
- **Console**: A web management UI for configuration and monitoring.
- **Memory**: Conversation memory and context management.

## Quick Start

```bash
pip install researchclaw
researchclaw init --defaults
researchclaw app
```

After installation, visit `http://localhost:8088` to access the console.

See [Quick Start](./quickstart.md) for detailed setup instructions.
