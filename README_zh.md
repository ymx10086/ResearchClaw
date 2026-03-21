<div align="center">

# ResearchClaw

本地优先的 Research OS，覆盖论文、工作流、实验、消息通道与自动化。

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

[English](README.md) | [中文](README_zh.md)

</div>

## 它现在是什么

ResearchClaw 现在已经不是一个“只会问答的科研聊天机器人”，而是一个本地优先的 FastAPI 应用，把下面这些能力放进同一套运行时：

- 常驻运行的 app runtime 与控制面 API
- 用于 chat、papers、research、channels、sessions、cron、models、skills、workspace、environments、MCP 的 Web Console
- 基于绑定规则的多 Agent 路由，以及每个 Agent 独立 workspace
- 持久化的研究状态层，覆盖 project、workflow、task、note、claim、evidence、experiment、artifact、draft
- `console`、`telegram`、`discord`、`dingtalk`、`feishu`、`imessage`、`qq`、`voice` 等内置通道
- 多 provider / 多 model 配置、启用切换、fallback 链和用量统计
- 标准 `SKILL.md` 支持、Skills Hub 搜索安装、MCP 客户端管理、自定义通道
- automation trigger、cron、heartbeat、主动提醒、运行态观测
- 论文检索/下载、BibTeX、LaTeX 辅助、数据分析、浏览器/文件工具、结构化研究记忆

它仍然是 Alpha 阶段，但已经不只是平台壳子。当前代码已经包含最小可用的 research workflow runtime、claim/evidence graph、experiment tracking、blocker remediation 和 project dashboard。当前最大的缺口已经变成 evidence matrix 质量、更严格的 claim-evidence 校验、更丰富的外部执行适配器，以及 submission / reproducibility 打包。

## 快速开始

### 1) 从源码安装

```bash
git clone https://github.com/MingxinYang/ResearchClaw.git
cd ResearchClaw
pip install -e .
```

### 2) 初始化工作目录

```bash
researchclaw init --defaults --accept-security
```

这一步会创建：

- 工作目录：`~/.researchclaw`
- 密钥目录：`~/.researchclaw.secret`
- 引导 Markdown 文件：`SOUL.md`、`AGENTS.md`、`PROFILE.md`、`HEARTBEAT.md` 等

### 3) 配置模型提供商

```bash
researchclaw models config
```

也可以直接添加：

```bash
researchclaw models add openai --type openai --model gpt-5 --api-key sk-...
```

当前代码支持的 provider type 为：`openai`、`anthropic`、`gemini`、`ollama`、`dashscope`、`deepseek`、`minimax`、`other`、`custom`。

### 4) 启动服务

```bash
researchclaw app --host 127.0.0.1 --port 8088
```

浏览器打开 [http://127.0.0.1:8088](http://127.0.0.1:8088)。

如果页面提示 `Console not found`，先构建一次前端：

```bash
cd console
npm install
npm run build
```

只要 `console/dist` 存在，后端就会自动托管它。

### 5) 打开 Research 页面

启动后可以直接进入 Console 的 **Research** 页面，用来：

- 创建 project
- 查看 workflow、claim、reminder
- 查看 execution health 与 recent blockers
- 对 remediation task 做 dispatch、execute、resume

## 现在已经有的东西

### 运行时与控制面

- FastAPI app，提供 `/api/health`、`/api/version`、`/api/control/*`、`/api/automation/*`、`/api/providers`、`/api/skills`、`/api/mcp`、`/api/workspace` 等接口
- gateway 风格的 runtime bootstrapping，负责 runner、channels、cron、MCP、automation store、config watcher
- 面向 agents、sessions、channels、cron、heartbeat、skills、automation runs、research services 的运行态快照

### Research OS 核心

- project 抽象，以及持久化的 `project -> workflow -> task -> artifact` 关系
- `literature_search`、`paper_reading`、`note_synthesis`、`hypothesis_queue`、`experiment_plan`、`experiment_run`、`result_analysis`、`writing_tasks`、`review_and_followup` 等 workflow stage
- paper note、idea note、experiment note、writing note、decision log 等结构化 notes
- 能把论文、笔记、实验、PDF chunk、citation、生成表格和 artifact 连起来的 claim/evidence graph
- 带 execution binding、heartbeat/result ingest、contract validation、result bundle validation、compare API 的 experiment tracking
- 针对缺 metric / output / artifact 的 remediation task 和主动提醒
- project dashboard 与 blocker panel，并且 Console / API 都支持批量 dispatch、execute、resume

### 工具与 Skills

当前 Agent 注册的内置 tools 包括：

- `semantic_scholar_search`
- `bibtex_search`、`bibtex_add_entry`、`bibtex_export`
- `latex_template`、`latex_compile_check`
- `data_describe`、`data_query`
- `run_shell`、`read_file`、`write_file`、`edit_file`、`append_file`
- `browse_url`、`browser_use`、`send_file`、`memory_search`
- `skills_list`、`skills_activate`、`skills_read_file`

当前仓库内置的 Skills 位于 `src/researchclaw/agents/skills/`，包括：

- `arxiv`
- `browser_visible`
- `citation_network`
- `cron`
- `dingtalk_channel`
- `docx`
- `experiment_tracker`
- `figure_generator`
- `file_reader`
- `himalaya`
- `literature_review`
- `news`
- `paper_summarizer`
- `pdf`
- `pptx`
- `research_notes`
- `research_workflows`
- `xlsx`

### 工作目录模型

运行数据和密钥数据分开存储：

```text
~/.researchclaw/
├── config.json
├── jobs.json
├── chats.json
├── research/
│   └── state.json
├── sessions/
├── active_skills/
├── customized_skills/
├── papers/
├── references/
├── experiments/
├── memory/
├── md_files/
├── custom_channels/
└── researchclaw.log

~/.researchclaw.secret/
├── envs.json
└── providers.json
```

provider 凭证和持久化环境变量默认不会放进 working dir。

## 开发与检查

后端检查：

```bash
pip install -e ".[dev]"
PYTHONPATH=src pytest -q
```

Console 构建：

```bash
npm --prefix console run build
```

Website 构建：

```bash
corepack pnpm --dir website run build
```

仓库级检查脚本：

```bash
scripts/check-ci.sh --skip-install
```

## 文档入口

仓库中的主要文档：

- [快速开始](website/public/docs/quickstart.zh.md)
- [部署指南](website/public/docs/deployment.zh.md)
- [控制台](website/public/docs/console.zh.md)
- [频道配置](website/public/docs/channels.zh.md)
- [Skills](website/public/docs/skills.zh.md)
- [MCP](website/public/docs/mcp.zh.md)
- [记忆系统](website/public/docs/memory.zh.md)
- [配置与工作目录](website/public/docs/config.zh.md)
- [CLI](website/public/docs/cli.zh.md)
- [FAQ](website/public/docs/faq.zh.md)
- [路线图](ROADMAP.md)

## 当前定位

如果按现在的代码来定义，ResearchClaw 更准确的状态是：

- 运行时基础设施、控制面、通道、provider/skill 兼容层已经比较成熟
- 已经可以作为带 project/workflow/experiment/claim 状态的科研运行平台使用
- 离真正的全自动科研平台还有距离：evidence matrix 质量、严格 validator、更深的执行后端、submission packaging 还在后面
