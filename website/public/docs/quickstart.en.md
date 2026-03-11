# Quick Start

## Requirements

- Python 3.10+
- pip or uv

## Install

### Option 1: Install from source (recommended for contributors)

```bash
git clone https://github.com/ymx10086/ResearchClaw.git
cd ResearchClaw
pip install -e ".[dev]"
```

### Option 2: Install from package

```bash
pip install researchclaw
```

## Initialize Workspace

```bash
researchclaw init --defaults --accept-security
```

This creates your working directory at `~/.researchclaw` by default.

## Configure Model Provider

```bash
researchclaw models config
# or directly:
researchclaw models add openai --type openai --model gpt-4o --api-key sk-...
```

## Start Service

```bash
researchclaw app --host 127.0.0.1 --port 8088
```

Visit `http://127.0.0.1:8088`.

## Deployment Next Step

If you want server deployment (Docker/systemd/Nginx), see [Deployment](./deployment.md).

## Next

- [Console](./console.md) — UI overview and operations
- [Channels](./channels.md) — multi-channel setup
- [Config & Working Dir](./config.md) — files, env vars, and persistence
