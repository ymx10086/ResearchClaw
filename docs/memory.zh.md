# Memory 记忆系统

ResearchClaw 的 Memory 系统管理对话历史和上下文信息，确保 AI 助手能够理解对话的连续性。

## 工作原理

每次对话都会被记录到 Memory 中。当新消息到来时，系统会加载相关的历史消息作为上下文，帮助模型更好地理解和回答。

## 消息存储

对话消息存储在工作目录的 `memory/` 文件夹中，按会话 ID 组织：

```
working/
└── memory/
    ├── session_001.json
    ├── session_002.json
    └── ...
```

## 上下文窗口

由于 LLM 的上下文窗口有限，Memory 系统会自动管理消息的截取和压缩。

相关功能：
- [Compact 压缩](./compact.md) — 对话压缩机制
- [命令系统](./commands.md) — 管理 Memory 的命令
