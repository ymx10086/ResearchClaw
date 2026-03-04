# Heartbeat 心跳

Heartbeat 是 ResearchClaw 的定时心跳机制，用于执行周期性任务。

## 工作原理

Heartbeat 按照配置的间隔定期运行，检查并执行以下任务：

- Skill 定时任务（Cron 触发）
- 频道连接状态检查
- 内存清理

## 配置

在 `config.yaml` 中配置心跳参数：

```yaml
heartbeat:
  enabled: true
  interval: 60  # 秒
```

## Cron 任务

Heartbeat 是 Skill Cron 任务的驱动引擎。每次心跳时，系统检查所有 Skill 的 Cron 表达式，执行到期的任务。

示例场景：
- 每天早上 9 点推送最新论文
- 每周一生成文献追踪报告
- 每小时检查 ArXiv 上的新论文

## 注意事项

- 心跳间隔不宜设置过短，避免不必要的资源消耗
- Cron 任务会在心跳触发时执行，实际执行时间可能有少量延迟
