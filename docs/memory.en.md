# Memory System

ResearchClaw's Memory system manages conversation history and context, ensuring the AI assistant understands conversational continuity.

## How It Works

Every conversation is recorded in Memory. When a new message arrives, the system loads relevant history as context to help the model understand and respond better.

## Message Storage

Messages are stored in the `memory/` folder under the working directory, organized by session ID:

```
working/
└── memory/
    ├── session_001.json
    ├── session_002.json
    └── ...
```

## Context Window

Due to LLM context window limitations, the Memory system automatically manages message truncation and compression.

Related:
- [Compact](./compact.md) — Conversation compression
- [Commands](./commands.md) — Memory management commands
