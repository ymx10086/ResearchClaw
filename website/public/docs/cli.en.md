# CLI

ResearchClaw provides a command-line interface for setup, runtime, and operations.

## Basic Usage

```bash
researchclaw [global-options] <command> [sub-command/options]
```

## Global Options

| Option       | Description                                                         |
| ------------ | ------------------------------------------------------------------- |
| `--host`     | Default API host used by CLI commands that call the running service |
| `--port`     | Default API port used by CLI commands that call the running service |
| `--version`  | Show version                                                        |
| `-h, --help` | Show help                                                           |

## Core Commands

| Command     | Purpose                                   |
| ----------- | ----------------------------------------- |
| `init`      | Initialize workspace and bootstrap files  |
| `app`       | Run the FastAPI service                   |
| `models`    | Manage model providers and local models   |
| `channels`  | Manage channel configuration              |
| `env`       | Manage persisted environment variables    |
| `skills`    | List/configure enabled skills             |
| `cron`      | Manage scheduled jobs via HTTP API        |
| `daemon`    | Runtime management (status/restart/logs)  |
| `papers`    | Search and manage papers                  |
| `chats`     | Manage chat sessions via HTTP API         |
| `clean`     | Clear working directory                   |
| `uninstall` | Remove local installation/runtime wrapper |

## Common Examples

```bash
researchclaw init --defaults --accept-security
researchclaw app --host 0.0.0.0 --port 8088
researchclaw models list
researchclaw channels list
researchclaw env set OPENAI_API_KEY sk-...
researchclaw cron list
researchclaw daemon status
```

## Notes

- Commands like `cron`, `daemon`, `chats` call the running HTTP API, so `researchclaw app` must be up first.
- For deployment-oriented startup options, see [Deployment](./deployment.md).
