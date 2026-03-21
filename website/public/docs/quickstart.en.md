# Quick Start

## Requirements

- Python 3.10+
- `pip`
- a model provider account or a reachable local model runtime

## Install From This Repository

```bash
git clone https://github.com/MingxinYang/ResearchClaw.git
cd ResearchClaw
pip install -e .
```

## Initialize the Workspace

```bash
researchclaw init --defaults --accept-security
```

By default this creates:

- working dir: `~/.researchclaw`
- secret dir: `~/.researchclaw.secret`

It also writes the bootstrap Markdown files the agent expects, such as `SOUL.md`, `AGENTS.md`, `PROFILE.md`, and `HEARTBEAT.md`.

## Configure a Provider

```bash
researchclaw models config
```

Or add one directly:

```bash
researchclaw models add openai --type openai --model gpt-5 --api-key sk-...
```

The first provider added through the CLI is enabled automatically.

## Start the Service

```bash
researchclaw app --host 127.0.0.1 --port 8088
```

Open `http://127.0.0.1:8088`.

If the browser shows `Console not found`, build the console once:

```bash
cd console
npm install
npm run build
```

## First Things To Click

After the service is up:

- open the **Research** page in the console
- create a project
- inspect workflows, execution health, and recent blockers
- use the Papers page or APIs to start seeding literature into that project

## Next

- [Console](./console.md)
- [Channels](./channels.md)
- [Config & Working Dir](./config.md)
- [Deployment](./deployment.md)
