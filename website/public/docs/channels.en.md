# Channels

Channels bridge ResearchClaw to external IM platforms. By configuring channels, you can interact with the AI assistant from your favorite messaging tools.

## Supported Channels

| Channel      | Description                                              |
| ------------ | -------------------------------------------------------- |
| DingTalk     | Enterprise IM, supports group and private chat           |
| Feishu       | Bytedance IM, supports group and private chat            |
| QQ           | Based on QQ Open Platform, supports channels and DMs     |
| Discord      | Popular overseas IM, supports bot integration            |
| iMessage     | macOS native messaging, requires local deployment on Mac |
| WeChat (WIP) | WeChat integration (in development)                      |

## Configuration

### Via Console

1. Open Console → Settings → Channels
2. Enable the target channel
3. Fill in required credentials (App Key, Secret, etc.)
4. Save and restart

### Via Config File

Edit `channels.yaml`:

```yaml
dingtalk:
  enabled: true
  app_key: "your-app-key"
  app_secret: "your-app-secret"
```

## Notes

- Each channel requires creating a Bot application on the respective platform
- iMessage channel is macOS only
- Service restart is required after changing channel configuration
