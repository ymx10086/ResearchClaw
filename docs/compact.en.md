# Compact (Conversation Compression)

When conversation history becomes too long, the Compact mechanism automatically compresses old messages, retaining key information while saving context window space.

## How It Works

1. When message count or token count exceeds the threshold, Compact is triggered
2. The system uses the LLM to summarize old messages
3. The summary replaces original messages, freeing context space
4. New messages continue to accumulate in the compressed context

## Configuration

Configure Compact parameters in `config.yaml`:

```yaml
memory:
  compact:
    enabled: true
    max_messages: 50
    summary_prompt: "Summarize the key points of the conversation above"
```

## Manual Trigger

You can also manually trigger compression in chat:

```
/compact
```

## Notes

- Compact calls the LLM to generate summaries, incurring additional API costs
- Compressed summaries may lose some detail
- Adjust thresholds based on your use case
