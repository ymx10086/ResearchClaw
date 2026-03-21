# 项目介绍

ResearchClaw 现在更像一个自托管的 Research OS，而不是一个简单的聊天壳。

## 目前已经落地的部分

- 带控制面的 FastAPI 服务
- Web Console 和 CLI
- 基于 binding 的多 Agent 路由与独立 workspace
- 持久化的 research state，覆盖 project、workflow、note、claim、evidence、experiment、artifact、draft
- `console`、`telegram`、`discord`、`dingtalk`、`feishu`、`imessage`、`qq`、`voice` 等通道运行时
- 多 provider / 多模型 / fallback 的模型管理
- 标准 `SKILL.md` skills、MCP 客户端、自定义通道
- automation trigger、cron、heartbeat、运行态观测
- 结构化 research workflow 执行、blocker remediation、project dashboard、claim graph API
- 面向论文、BibTeX、LaTeX、数据分析、浏览器、文件编辑、记忆的工具

## 当前状态

代码层面已经比较强的是平台与运行时：

- runtime bootstrapping
- control-plane API
- channels
- providers
- skills / MCP

科研闭环已经进入 Alpha 阶段，但还没做完：

- 已有最小 workflow runtime，但还不是最终的 evidence matrix 系统
- 已有 claim/evidence graph，但还没有严格 validator
- 已有 experiment execution / remediation，但还没有接完所有外部执行器
- 已有 draft / review 阶段，但还没有完整 submission bundle

## 运行模块

- **Gateway Lite**：runner、channels、cron、MCP、automation state 的统一边界
- **Research runtime**：project/workflow/task 状态、stage worker、reminder、remediation
- **Runner 层**：multi-agent manager 与每个 agent 独立 workspace
- **控制面**：status、usage、channels、agents、sessions、automation 等观测接口
- **目录模型**：本地 working dir 与独立 secret dir

## 下一步阅读

- [快速开始](./quickstart.md)
- [部署指南](./deployment.md)
- [控制台](./console.md)
- [配置与工作目录](./config.md)
