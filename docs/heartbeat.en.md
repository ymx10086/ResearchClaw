# Heartbeat

Heartbeat is ResearchClaw's periodic timer mechanism for executing scheduled tasks.

## How It Works

Heartbeat runs at configured intervals, checking and executing:

- Skill cron tasks
- Channel connection status checks
- Memory cleanup

## Configuration

Configure heartbeat parameters in `config.yaml`:

```yaml
heartbeat:
  enabled: true
  interval: 60  # seconds
```

## Cron Tasks

Heartbeat drives skill cron tasks. On each heartbeat, the system checks all skill cron expressions and executes due tasks.

Example scenarios:
- Push latest papers every morning at 9 AM
- Generate literature tracking reports every Monday
- Check ArXiv for new papers every hour

## Notes

- Don't set the heartbeat interval too short to avoid unnecessary resource consumption
- Cron tasks execute at heartbeat time; actual execution may have slight delays
