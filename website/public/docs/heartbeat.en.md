# Heartbeat

Heartbeat is the built-in proactive loop for the current runtime.

It is separate from the research runtime's proactive workflow cycle. Heartbeat is still the lighter-weight check-in mechanism; the research runtime handles workflow execution, blocker reminders, and remediation actions.

## Where the Query Comes From

The runtime reads:

1. `md_files/HEARTBEAT.md` if it exists
2. otherwise `HEARTBEAT.md` at the working-dir root

## Preferred Config Shape

```json
{
  "agents": {
    "defaults": {
      "heartbeat": {
        "enabled": true,
        "every": "30m",
        "target": "last",
        "active_hours": {
          "start": "08:00",
          "end": "22:00"
        }
      }
    }
  }
}
```

Legacy top-level heartbeat keys are still accepted as a fallback.

## Runtime Behavior

- parses intervals like `30m`, `1h`, or `2h30m`
- can respect active hours
- can dispatch to the last active channel target when `target` is `last`
- writes status to `heartbeat.json`

## Related Proactive Loops

Separately from heartbeat, the runtime also includes:

- paper digest
- deadline reminder
- research workflow proactive cycle

## Operational Tip

Heartbeat is useful for lightweight check-ins and reminders. It should be treated as complementary to the Research OS workflow loop, not as a replacement for structured project/workflow automation.
