# Heartbeat 心跳

Heartbeat 是 ResearchClaw 的周期调度机制，用于执行主动任务。

## 主要用途

- 执行技能中配置的 cron prompt
- 执行内置周期任务
- 向已配置频道进行主动投递

## 配置位置

心跳配置来自 `config.json`（并兼容旧字段回退）：

```json
{
  "agents": {
    "defaults": {
      "heartbeat": {
        "enabled": true,
        "every": "30m",
        "target": "last"
      }
    }
  }
}
```

也可通过环境变量设置默认值：

- `RESEARCHCLAW_HEARTBEAT_ENABLED`
- `RESEARCHCLAW_HEARTBEAT_INTERVAL`（分钟）

## 运维建议

- 心跳间隔建议设为 `30m` 或 `1h` 这类实用值。
- 主动消息投递需保证至少有一个可用频道。
- 通过 `/api/control/status` 观察 cron/heartbeat 运行状态。
