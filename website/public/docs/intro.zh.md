# 项目介绍

ResearchClaw 是面向科研工作流的 AI 助手，聚焦论文检索、实验追踪和多渠道协作。

## 核心能力

- 论文检索与追踪（ArXiv、Semantic Scholar 等）
- 文献管理与 BibTeX 工作流
- 论文总结与研究记忆沉淀
- 实验记录与周期提醒
- 多渠道消息触达与自动化触发

## 运行模块

- **Agent 运行时**：Scholar 助手与工具/技能编排
- **控制面**：状态、会话、cron、自动化任务可观测
- **频道层**：控制台 + 外部 IM 渠道
- **目录模型**：本地工作目录 + 独立密钥目录

## 最小启动流程

```bash
researchclaw init --defaults --accept-security
researchclaw models config
researchclaw app --host 127.0.0.1 --port 8088
```

启动后访问 `http://127.0.0.1:8088`。

## 下一步阅读

- [快速开始](./quickstart.md)
- [部署指南](./deployment.md)
- [配置与工作目录](./config.md)
