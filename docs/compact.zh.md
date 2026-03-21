# Compact

Compact 用来压缩较早的对话上下文，同时保留摘要。

## 手动触发

在对话中执行：

```text
/compact
```

查看当前摘要：

```text
/compact_str
```

## 自动触发

当前实现采用一个简单启发式：

- 用 `message_count * 300` 估算 token
- 再与 `max_input_tokens * RESEARCHCLAW_MEMORY_COMPACT_RATIO` 比较
- 超过阈值就执行 compact

## 当前配置入口

Compact 不是通过 `config.yaml` 配置的。

当前相关环境变量是：

- `RESEARCHCLAW_MEMORY_COMPACT_KEEP_RECENT`
- `RESEARCHCLAW_MEMORY_COMPACT_RATIO`

代码默认值为：

- 保留最近消息数：`3`
- 比例：`0.7`

## Compact 实际会做什么

- 保留最近的消息
- 将更早的消息折叠成 compact summary
- 把摘要保存到持久化 memory state 中

当前实现是启发式、本地式的压缩，还不是完整的证据保真摘要流水线。
