<div align="center">
  <img src="console/public/researchclaw-logo.png" alt="ResearchClaw logo" width="340">

# ResearchClaw

> 本地优先的 Research OS，覆盖论文、工作流、实验、消息通道与自动化。

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-2563eb.svg?style=flat-square)](https://python.org)
![FastAPI Runtime](https://img.shields.io/badge/runtime-FastAPI-0f766e.svg?style=flat-square)
![Web Console](https://img.shields.io/badge/interface-Web%20Console-f97316.svg?style=flat-square)
![Skills + MCP](https://img.shields.io/badge/extensibility-Skills%20%2B%20MCP-111827.svg?style=flat-square)
![Status Alpha](https://img.shields.io/badge/status-Alpha-b45309.svg?style=flat-square)
[![License](https://img.shields.io/badge/license-Apache%202.0-16a34a.svg?style=flat-square)](LICENSE)

[English](README.md) | [中文](README_zh.md) | [文档](website/public/docs/intro.zh.md) | [路线图](ROADMAP.md) | [Research-Equality 生态](https://github.com/orgs/Research-Equality/repositories)

ResearchClaw 是 [Research-Equality](https://github.com/orgs/Research-Equality/repositories) 生态中的运行时与工作台层。

持久化科研状态 · 多 Agent 运行时 · Skills + MCP · 自动化 + 通道

[为什么是 ResearchClaw](#zh-why-researchclaw) • [快速开始](#zh-quick-start) • [Research-Equality 生态](#zh-research-equality-ecosystem) • [现在已经有的东西](#zh-what-you-get-today) • [文档入口](#zh-docs)

</div>

<a id="zh-why-researchclaw"></a>
## 为什么是 ResearchClaw

ResearchClaw 更像整个 Research-Equality 技术栈里的运行时和工作台，而不是一个一次性的科研聊天工具。它把长期科研任务真正沉淀成可持续推进的本地状态：project、workflow、claim、evidence、experiment、artifact、reminder、channel、automation 都在一套系统里，而不是散落在聊天记录、终端历史和文件夹里。

| 常见 AI 科研工具形态 | ResearchClaw 的做法 |
| --- | --- |
| 任务随着一次性对话结束而丢失上下文 | 持久化 `project -> workflow -> task -> artifact` 状态，并保留 notes、claims、evidence、drafts、reminders |
| 检索、执行、写作、跟进分散在多套工具里 | 把 console、automation、channels、APIs、papers、experiments、memory 放进同一个 runtime |
| Web、终端、IM 之间难以接力 | 同一份 research state 同时暴露给 web console、消息通道、cron、sessions 和 control plane API |
| skills、provider、外部工具是临时拼接的 | 用标准 `SKILL.md`、MCP、provider routing、fallback chain 和 per-agent workspace rules 统一管理 |

当前代码层面，它已经把下面这些能力放进同一套运行时：

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

<a id="zh-quick-start"></a>
## 快速开始

### 1. 从源码安装

```bash
git clone https://github.com/MingxinYang/ResearchClaw.git
cd ResearchClaw
pip install -e .
```

### 2. 初始化工作目录

```bash
researchclaw init --defaults --accept-security
```

这一步会创建：

- 工作目录：`~/.researchclaw`
- 密钥目录：`~/.researchclaw.secret`
- 引导 Markdown 文件：`SOUL.md`、`AGENTS.md`、`PROFILE.md`、`HEARTBEAT.md` 等

### 3. 配置模型提供商

```bash
researchclaw models config
```

也可以直接添加：

```bash
researchclaw models add openai --type openai --model gpt-5 --api-key sk-...
```

当前代码支持的 provider type 为：`openai`、`anthropic`、`gemini`、`ollama`、`dashscope`、`deepseek`、`minimax`、`other`、`custom`。

### 4. 启动服务

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

### 5. 打开 Research 页面

启动后可以直接进入 Console 的 **Research** 页面，用来：

- 创建 project
- 查看 workflow、claim、reminder
- 查看 execution health 与 recent blockers
- 对 remediation task 做 dispatch、execute、resume

<a id="zh-research-equality-ecosystem"></a>
## Research-Equality 生态

ResearchClaw 最适合放在整个生态的中心位置，作为持久 runtime 和 workspace 使用。配套的 `RE-*` 仓库负责分阶段的 skills 供给，而 `awesome-ai-scientists` 则更适合作为 AI Scientist 系统和 AI 科研工具版图入口。

完整仓库导航见：[Research-Equality repositories](https://github.com/orgs/Research-Equality/repositories)

| 仓库 | 与 ResearchClaw 的配套角色 | 什么时候用 |
| --- | --- | --- |
| [RE-idea-generation](https://github.com/Research-Equality/RE-idea-generation) | 研究想法生成、问题发现、方向探索的权威 skills 仓库 | 当你要把模糊兴趣点收敛成可辩护的研究方向 |
| [RE-literature-discovery](https://github.com/Research-Equality/RE-literature-discovery) | 文献发现、权威性排序、证据综合、综述写作的权威 skills 仓库 | 当你需要可审计的论文检索、筛选和 review 流水线 |
| [RE-research-design](https://github.com/Research-Equality/RE-research-design) | 研究设计、方法形式化、实验规划、评测设计的权威 skills 仓库 | 当你在真正实现前需要更扎实的研究设计层 |
| [RE-experiment](https://github.com/Research-Equality/RE-experiment) | 实验规划、实现、验证、分析的权威 skills 仓库 | 当你在做 baseline 复现、ablation 或强化实验可追溯性 |
| [RE-paper-writing](https://github.com/Research-Equality/RE-paper-writing) | 论文规划、写作、修改、LaTeX、投稿检查的权威 skills 仓库 | 当你要把真实产物接入写作与投稿工作流 |
| [awesome-ai-scientists](https://github.com/Research-Equality/awesome-ai-scientists) | `Awesome-AI-Research` 地图仓库，汇总 AI-native research systems、workflow modules、benchmarks、surveys、datasets、meta-resources | 当你想看更广的 AI Scientist 系统和 AI 科研工具生态，而不只盯着当前项目 |

一个很自然的搭配方式是：用 `ResearchClaw` 承载长期 workspace 和控制面，再按当前阶段挂上 1 到 2 个 `RE-*` 仓库；如果要扩展视野、找同类系统、基准或周边工具，就从 `awesome-ai-scientists` 进去。

<a id="zh-what-you-get-today"></a>
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

<a id="zh-docs"></a>
## 文档入口

仓库中的主要文档：

- [项目介绍](website/public/docs/intro.zh.md)
- [快速开始](website/public/docs/quickstart.zh.md)
- [部署指南](website/public/docs/deployment.zh.md)
- [控制台](website/public/docs/console.zh.md)
- [频道配置](website/public/docs/channels.zh.md)
- [Skills](website/public/docs/skills.zh.md)
- [MCP](website/public/docs/mcp.zh.md)
- [记忆系统](website/public/docs/memory.zh.md)
- [配置与工作目录](website/public/docs/config.zh.md)
- [命令说明](website/public/docs/commands.zh.md)
- [CLI](website/public/docs/cli.zh.md)
- [Heartbeat](website/public/docs/heartbeat.zh.md)
- [社区](website/public/docs/community.zh.md)
- [贡献指南](website/public/docs/contributing.zh.md)
- [FAQ](website/public/docs/faq.zh.md)
- [路线图](ROADMAP.md)

## 当前定位

如果按现在的代码来定义，ResearchClaw 更准确的状态是：

- 运行时基础设施、控制面、通道、provider/skill 兼容层已经比较成熟
- 已经可以作为带 project/workflow/experiment/claim 状态的科研运行平台使用
- 离真正的全自动科研平台还有距离：evidence matrix 质量、严格 validator、更深的执行后端、submission packaging 还在后面
