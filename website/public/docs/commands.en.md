# Chat Commands

ResearchClaw supports slash commands inside chat messages.

## Available Commands

| Command                 | Description                      |
| ----------------------- | -------------------------------- |
| `/new` or `/start`      | Start a new session              |
| `/compact`              | Compact conversation memory      |
| `/clear`                | Clear history and summaries      |
| `/history`              | Show conversation statistics     |
| `/papers`               | List recently discussed papers   |
| `/refs`                 | Show reference library summary   |
| `/skills`               | List active skills               |
| `/skills debug [query]` | Show skill routing debug details |
| `/compact_str`          | Show current compact summary     |
| `/daemon status`        | Show runtime daemon status       |
| `/daemon logs [n]`      | Show daemon logs                 |
| `/help`                 | Show command help                |

## Usage

Type slash commands directly in any conversation:

```text
/help
/skills
/skills debug summarize arxiv papers this week
```

## Notes

- Unknown slash commands fall back to normal natural-language handling.
- `/daemon restart` is intentionally restricted in chat path; use CLI instead.
