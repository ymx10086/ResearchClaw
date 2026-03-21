# 记忆系统

ResearchClaw 会为当前运行时维护一套持久化研究记忆。

## 它会记录什么

- 最近的对话消息
- session 数量
- 讨论过的论文
- 研究笔记
- 对更早对话上下文的 compact summary
- 以及一套独立的结构化 research state，用于保存 project、workflow、claim、experiment、artifact

## 存储位置

当前实现把记忆状态放在 working dir 下面：

```text
~/.researchclaw/
└── memory/
    ├── memory_state.json
    └── *.md                # 可选的 notes / memory markdown 文件
```

这和更早的旧文档里“每个 session 一个 JSON 文件”的描述不同。

结构化的 Research OS 状态会单独存放：

```text
~/.researchclaw/
└── research/
    └── state.json
```

## 相关运行时能力

- `/history` 用于查看记忆统计
- `/papers` 用于列出最近讨论论文
- `/refs` 用于汇总 BibTeX 文献库
- `memory_search()` 用于搜索记忆层
- workspace API 可以列出和读取 memory 下的 markdown 文件
- Research API 负责管理 paper note、experiment note、writing note、decision log 等结构化 notes

## 说明

- memory 绑定在当前 runtime workspace 上
- 压缩逻辑单独见 [Compact](./compact.md)
- chat/session memory 和结构化 research state 有关联，但不是同一层存储
