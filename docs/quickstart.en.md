# Quick Start

## Requirements

- Python 3.10+
- pip or uv

## Installation

### Option 1: pip install (Recommended)

```bash
pip install researchclaw
```

### Option 2: One-click install script (macOS / Linux)

```bash
curl -fsSL https://researchclaw.dev/install.sh | bash
```

### Option 3: Docker

```bash
docker pull researchclaw/researchclaw:latest
docker run -p 8088:8088 -v researchclaw-data:/app/working researchclaw/researchclaw:latest
```

## Initialize

Before first use, initialize the working directory:

```bash
researchclaw init --defaults
```

This creates default configuration files and the working directory.

## Start

```bash
researchclaw app
```

Visit `http://localhost:8088` to access the console.

## Configure LLM

Configure your LLM provider and API key in the console:

1. Open Console → Settings
2. Select a model provider (OpenAI, Claude, Qwen, etc.)
3. Enter your API Key
4. Save and start using

## Next Steps

- [Channels](./channels.md) — Connect DingTalk, Feishu, and other IM platforms
- [Skills](./skills.md) — Learn about and extend research skills
- [Config & Working Dir](./config.md) — Detailed configuration guide
