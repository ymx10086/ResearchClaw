# Compact

Compaction reduces old conversation context while keeping a summary.

## Manual Trigger

In chat:

```text
/compact
```

You can inspect the current summary with:

```text
/compact_str
```

## Automatic Trigger

The current implementation uses a simple heuristic:

- estimate tokens as `message_count * 300`
- compare that with `max_input_tokens * RESEARCHCLAW_MEMORY_COMPACT_RATIO`
- compact when the estimate crosses the threshold

## Current Config Surface

Compaction is not configured through `config.yaml`.

Relevant env vars today are:

- `RESEARCHCLAW_MEMORY_COMPACT_KEEP_RECENT`
- `RESEARCHCLAW_MEMORY_COMPACT_RATIO`

Defaults in code are:

- keep recent messages: `3`
- ratio: `0.7`

## What Compaction Does

- preserves the most recent messages
- folds older messages into a compact summary
- keeps the summary in persistent memory state

The current implementation is heuristic and local; it is not a full evidence-preserving summarization pipeline.
