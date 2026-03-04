# Compact 对话压缩

当对话历史过长时，Compact 机制会自动压缩旧消息，保留关键信息同时节省上下文窗口空间。

## 工作原理

1. 当消息数量或 Token 数超过阈值时，触发 Compact
2. 系统使用 LLM 对旧消息进行摘要
3. 摘要替换原始消息，释放上下文空间
4. 新消息继续在压缩后的上下文中积累

## 配置

在 `config.yaml` 中配置 Compact 参数：

```yaml
memory:
  compact:
    enabled: true
    max_messages: 50
    summary_prompt: "请总结以上对话的关键内容"
```

## 手动触发

你也可以在对话中手动触发压缩：

```
/compact
```

## 注意事项

- Compact 会调用 LLM 生成摘要，产生额外的 API 费用
- 压缩后的摘要可能丢失部分细节信息
- 建议根据使用场景调整阈值
