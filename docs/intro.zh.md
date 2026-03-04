# ResearchClaw 项目介绍

ResearchClaw 是一款基于 AI 的科研助手工具，帮助研究人员追踪论文、管理文献、记录实验、分析数据。

## 核心特性

- **论文搜索与追踪**：支持 ArXiv、Semantic Scholar 等论文源，自动追踪研究领域最新成果
- **文献管理**：BibTeX 管理、引用格式化、文献库检索
- **实验与分析**：实验记录、数据分析、可视化
- **多频道支持**：钉钉、飞书、QQ、Discord、iMessage 等
- **Skills 扩展**：内置科研技能，支持自定义扩展和定时任务
- **本地掌控**：数据本地存储，支持云端部署

## 架构概览

ResearchClaw 由以下模块组成：

- **Agent 引擎**：基于 ReAct 模式的智能体，负责理解用户意图并调用工具
- **Skills 系统**：可扩展的技能框架，支持自定义科研技能
- **频道层**：统一的消息收发接口，支持多种 IM 平台
- **控制台**：Web 管理界面，用于配置和监控
- **Memory**：对话记忆与上下文管理

## 快速开始

```bash
pip install researchclaw
researchclaw init --defaults
researchclaw app
```

安装完成后，访问 `http://localhost:8088` 即可进入控制台。

详细的安装与配置请参阅 [快速开始](./quickstart.md) 文档。
