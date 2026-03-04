# Configuration & Working Directory

## Working Directory

All ResearchClaw data and configuration files are stored in the working directory. The default is `~/.researchclaw/`.

### Directory Structure

```
~/.researchclaw/
├── config.yaml          # Main config file
├── channels.yaml        # Channel configuration
├── mcp.yaml             # MCP configuration
├── PROFILE.md           # Assistant persona
├── skills/              # Skills folder
│   ├── built_in/        # Built-in skills
│   └── custom/          # Custom skills
├── memory/              # Conversation memory
└── logs/                # Log files
```

## Configuration Files

### config.yaml

Main configuration file with LLM, Memory, Heartbeat, etc.:

```yaml
llm:
  provider: openai
  model: gpt-4o
  api_key: "sk-xxx"

memory:
  compact:
    enabled: true
    max_messages: 50

heartbeat:
  enabled: true
  interval: 60

server:
  host: "0.0.0.0"
  port: 8088
```

### PROFILE.md

Defines the AI assistant's persona and behavior style. You can customize the assistant's personality, expertise areas, and response style.

## Environment Variables

Sensitive configurations can be set via environment variables:

| Variable | Description |
|----------|-------------|
| `RESEARCHCLAW_WORKING_DIR` | Working directory path |
| `OPENAI_API_KEY` | OpenAI API Key |
| `ANTHROPIC_API_KEY` | Anthropic API Key |

## CLI Configuration

Manage configuration using CLI commands:

```bash
researchclaw config show     # Show current config
researchclaw config set key value  # Set a config value
```
