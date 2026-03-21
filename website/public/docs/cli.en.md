# CLI

ResearchClaw ships a CLI for setup, runtime startup, and local operations.

## Global Usage

```bash
researchclaw [--host HOST] [--port PORT] <command> ...
```

## Top-Level Commands

| Command     | Purpose                                               |
| ----------- | ----------------------------------------------------- |
| `init`      | initialize the workspace and bootstrap Markdown files |
| `app`       | run the FastAPI service                               |
| `models`    | manage providers and local models                     |
| `channels`  | manage channel config and custom channels             |
| `env`       | manage persisted environment variables                |
| `skills`    | list and configure enabled skills                     |
| `papers`    | search or download papers                             |
| `cron`      | manage scheduled jobs through the running API         |
| `chats`     | manage chat sessions through the running API          |
| `daemon`    | inspect local runtime metadata and logs               |
| `clean`     | clear the working dir                                 |
| `uninstall` | remove the local environment                          |

## Common Subcommands

### `models`

- `researchclaw models list`
- `researchclaw models config`
- `researchclaw models add ...`
- `researchclaw models remove ...`
- `researchclaw models download ...`
- `researchclaw models local`

### `channels`

- `researchclaw channels list`
- `researchclaw channels config`
- `researchclaw channels install <path-or-key>`
- `researchclaw channels remove <key>`

### `skills`

- `researchclaw skills list`
- `researchclaw skills config`

### `env`

- `researchclaw env list`
- `researchclaw env set KEY VALUE`
- `researchclaw env delete KEY`

### `cron`

- `researchclaw cron list`
- `researchclaw cron get JOB_ID`
- `researchclaw cron create ...`
- `researchclaw cron pause JOB_ID`
- `researchclaw cron resume JOB_ID`
- `researchclaw cron run JOB_ID`
- `researchclaw cron state JOB_ID`
- `researchclaw cron delete JOB_ID`

## Notes

- `cron` and `chats` expect the HTTP service to be running
- `models`, `channels`, `skills`, `env`, and `papers` are primarily local workflows
- `daemon restart` does not directly own the app process; it prints restart guidance unless a restart callback is attached by the runtime
