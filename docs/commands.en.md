# Commands

ResearchClaw supports commands in chat to control system behavior.

## Available Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help information |
| `/compact` | Manually trigger conversation compression |
| `/clear` | Clear current session's conversation history |
| `/reset` | Reset assistant state |
| `/skills` | List installed skills |
| `/install <url>` | Install a skill from GitHub |
| `/uninstall <name>` | Uninstall a skill |

## Usage

In any channel's chat, type a command starting with `/`:

```
/help
```

```
/install https://github.com/user/my-skill
```

## Commands vs. Natural Language

Besides commands, you can also describe your needs in natural language, and the AI assistant will understand and perform the corresponding action:

```
Install this skill: https://github.com/user/my-skill
```

This is equivalent to `/install https://github.com/user/my-skill`.
