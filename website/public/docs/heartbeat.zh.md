# Heartbeat

Heartbeat 是当前运行时自带的主动循环。

它和 research runtime 的主动 workflow cycle 是分开的。Heartbeat 仍然是更轻量的 check-in 机制；research runtime 负责 workflow 执行、blocker reminder 和 remediation action。

## 查询内容来自哪里

运行时会按这个顺序读取：

1. 如果存在，则优先读取 `md_files/HEARTBEAT.md`
2. 否则读取 working dir 根目录下的 `HEARTBEAT.md`

## 推荐配置结构

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

旧的顶层 heartbeat 字段仍然兼容，但只是 fallback。

## 运行时行为

- 能解析 `30m`、`1h`、`2h30m` 这类间隔
- 可以受 active hours 约束
- 当 `target` 为 `last` 时，可以向上一次活跃通道回推
- 会把状态写入 `heartbeat.json`

## 相关主动循环

除了 heartbeat 之外，运行时还包括：

- paper digest
- deadline reminder
- research workflow proactive cycle

## 运维提示

Heartbeat 更适合做轻量 check-in 和提醒。真正的 project/workflow 自动推进应该交给 Research OS 的结构化 workflow loop。
