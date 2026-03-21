# Chat Commands

ResearchClaw parses slash commands inside chat messages.

## Main Commands

| Command                 | Behavior                                             |
| ----------------------- | ---------------------------------------------------- |
| `/new` or `/start`      | start a new research session                         |
| `/compact`              | compact conversation memory                          |
| `/clear`                | clear memory, summaries, discussed papers, and notes |
| `/history`              | show memory statistics                               |
| `/papers`               | list recently discussed papers                       |
| `/refs`                 | summarize the current BibTeX library                 |
| `/skills`               | list active skills                                   |
| `/skills debug [query]` | inspect skill-selection details                      |
| `/compact_str`          | show the current compact summary                     |
| `/help`                 | show command help                                    |

## Daemon-Style Commands

The chat parser also recognizes daemon-style commands:

- `/daemon status`
- `/daemon logs [n]`
- `/daemon reload-config`
- `/daemon version`

Short aliases are also parsed:

- `/status`
- `/logs`
- `/reload-config`
- `/version`

## Important Note About Restart

`/daemon restart` is recognized, but the chat path does not own the app lifecycle. In practice it returns restart guidance rather than force-restarting the service.
