<div align="center">

# 🔬 ResearchClaw

**你的 AI 科研助手**

专为学术研究者设计的智能 Agent 助手 —— 由大语言模型驱动，深耕科研工作流。

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

[English](README.md) | [中文](README_zh.md)

</div>

---

## ✨ 什么是 ResearchClaw？

ResearchClaw 是一个运行在**你自己机器上**的 AI 科研助手。基于 [AgentScope](https://github.com/modelscope/agentscope) 框架构建，使用 ReAct Agent + 专业科研工具，帮助你：

- 📄 **搜索与发现论文** — ArXiv、Semantic Scholar、Google Scholar
- 📚 **管理参考文献** — BibTeX 导入/导出、引用网络探索
- 🔍 **阅读与总结论文** — 从 PDF 中提取关键发现
- 📊 **数据分析** — 统计分析、可视化、实验追踪
- ✍️ **写作与审阅** — LaTeX 辅助、文献综述生成
- ⏰ **保持更新** — 每日论文摘要、截止日提醒、引用提醒
- 🧠 **构建知识** — 跨会话的持久化研究笔记和记忆

## 🚀 快速开始

### 1) 安装（基于当前仓库）

```bash
pip install -e ".[dev]"
```

请在仓库根目录执行该命令。

### 2) 初始化工作目录

```bash
researchclaw init --defaults --accept-security
```

这会创建 `~/.researchclaw` 及默认引导文件。

### 3) 配置模型提供商

```bash
researchclaw models config
# 或：
researchclaw models add openai --type openai --model gpt-4o --api-key sk-...
```

首次通过 CLI 添加 provider 时会自动设为当前激活 provider。之后如果新增多个
provider，可在前端“模型配置”页面切换，或重新执行 `researchclaw models config`。

### 4) 启动服务

```bash
researchclaw app --host 127.0.0.1 --port 8088
```

在浏览器中打开 [http://127.0.0.1:8088](http://127.0.0.1:8088)。

### 5) 前端（Console）开发

先启动后端：

```bash
researchclaw app
```

在另一个终端启动前端开发服务器：

```bash
cd console
npm install
npm run dev
```

然后打开 Vite 地址（通常是 [http://localhost:5173](http://localhost:5173)）。
前端开发服务器会将 `/api` 请求代理到 `http://127.0.0.1:8088`。

构建生产前端资源：

```bash
cd console
npm run build
```

当 `console/dist` 存在时，后端会自动托管该目录。

### 6) 一键安装（macOS / Linux）

```bash
curl -fsSL https://researchclaw.github.io/install.sh | bash
```

### 本地 CI 检查

推送前可直接运行与 GitHub Actions 对齐的检查：

```bash
scripts/check-ci.sh
```

如果依赖已经安装好，可跳过安装阶段：

```bash
scripts/check-ci.sh --skip-install
```

## 🚢 部署指南

### 单机部署（推荐基线）

```bash
export RESEARCHCLAW_WORKING_DIR=/data/researchclaw
export RESEARCHCLAW_SECRET_DIR=/data/researchclaw.secret
export RESEARCHCLAW_HOST=0.0.0.0
export RESEARCHCLAW_PORT=8088
export RESEARCHCLAW_AUTOMATION_TOKEN=change-me

researchclaw app --host 0.0.0.0 --port 8088
```

健康检查接口：`GET /api/health`

### Docker 自建镜像部署

```bash
docker build -f deploy/Dockerfile -t researchclaw:local .
docker run -d \
  --name researchclaw \
  -p 8088:8088 \
  -e PORT=8088 \
  -e RESEARCHCLAW_WORKING_DIR=/app/working \
  -e RESEARCHCLAW_SECRET_DIR=/app/working.secret \
  -e RESEARCHCLAW_AUTOMATION_TOKEN=change-me \
  -v researchclaw-working:/app/working \
  -v researchclaw-secret:/app/working.secret \
  researchclaw:local
```

### 生产部署清单

- 建议放在 Nginx/Caddy 后并启用 HTTPS。
- `working_dir` 和 `secret_dir` 都要做持久化。
- 对外开放自动化接口前，务必设置 `RESEARCHCLAW_AUTOMATION_TOKEN`。
- 视网络环境限制内部管理接口来源 IP。
- 监控 `/api/health` 与 `/api/control/status`。

## 📝 更新记录

### 2026-03-11

- 新增自动化触发 API（面向外部系统）：
  通过 token 保护的 `/api/automation/triggers/agent` 支持异步执行、触发记录留存，以及可选的多频道 fan-out 投递（`dispatches` / `fanout_channels`）。
- 增强控制面可观测性：
  `/api/control/status` 新增 runner 会话、频道队列/worker、cron 运行态、自动化成功/失败计数等运行时快照。
- 新增模型回退与用量可观测：
  流式与非流式对话均支持回退链，控制面通过 `/api/control/usage` 与 `runtime.runner.usage` 暴露请求量/回退次数等指标。
- 升级 Console 状态页运维指标：
  可直接查看注册频道数、队列积压、处理中键数量，以及自动化成功/失败卡片。
- 新增频道运维接口与控制台入口：
  支持自定义频道插件安装/卸载（`/api/control/channels/custom/*`）、账号映射管理（`/api/control/channels/accounts`）和路由绑定管理（`/api/control/bindings`）。
- 增强了模型与提供商配置界面：
  支持主流平台预设、按 provider 配置 `base_url`、预置模型下拉，以及同一卡片内手动新增模型。
- 扩展了 provider 的存储与接口：
  现在一个 provider 可以同时配置多个模型，并兼容旧的单模型数据格式。
- 提升了 Web Console 的稳定性：
  修复了 `/models` 静态资源缺失时的回退处理、`HEAD /` 请求、名称包含 `/` 的 provider 路由，以及工作区页面对象值直接渲染导致的 React 报错。
- 强化了 skills 的兼容与触发逻辑：
  `SKILL.md` 现已兼容 OpenClaw / ClawHub 风格元数据，如 `user-invocable`、`disable-model-invocation`；同时统一了 Python skill 的运行时接入接口，支持 `tools`、`TOOLS`、`register()`、`get_tools()` 等导出形式。
- 修复了实验追踪 skill 的参数兼容问题：
  `status`、不同大小写的 `experiment_id` 等额外字段不再导致 tool 调用崩溃。
- README 与 website 文档已按当前运行时行为完成刷新，并新增独立部署指南（单机、Docker 自建、生产检查清单）。

## 🏗️ 架构

```
用户 ─→ 控制台 (Web UI) / CLI / Slack / 邮件
          │
          ▼
     ResearchClaw App (FastAPI + Uvicorn)
          │
          ▼
     ScholarAgent (ReActAgent)
     ├── 科研工具：ArXiv、Semantic Scholar、PDF 阅读器、BibTeX、LaTeX
     ├── 数据工具：pandas、matplotlib、scipy 分析
     ├── 通用工具：Shell、文件 I/O、浏览器、记忆搜索
     ├── 技能：论文总结、文献综述、实验追踪……
     ├── 记忆：研究记忆 + 知识库 + 自动压缩
     ├── 模型：OpenAI / Anthropic / Gemini / DashScope / 本地模型
     └── 定时任务：每日论文摘要、截止日提醒、引用提醒
```

## 🔧 内置科研工具

| 工具 | 描述 |
|------|------|
| `arxiv_search` | 搜索和下载 ArXiv 论文 |
| `semantic_scholar_search` | 查询 Semantic Scholar |
| `paper_reader` | 从 PDF 论文中提取文本、图表 |
| `bibtex_manager` | 解析和管理 BibTeX 参考文献 |
| `latex_helper` | LaTeX 语法辅助和模板生成 |
| `data_analysis` | 使用 pandas、numpy、scipy 统计分析 |
| `plot_generator` | 创建出版级图表 |
| `shell` | 执行 Shell 命令 |
| `file_io` | 读写和编辑文件 |
| `browser_control` | 网页浏览和信息收集 |
| `memory_search` | 搜索研究笔记和对话历史 |

## 📦 可扩展技能

ResearchClaw 内置了面向科研的技能，且支持自定义扩展：

- **arxiv** — 高级 ArXiv 搜索与分类过滤
- **paper_summarizer** — 多级论文总结
- **literature_review** — 生成结构化文献综述
- **citation_network** — 探索引用图谱
- **experiment_tracker** — 记录实验参数和结果
- **figure_generator** — 创建出版级图表
- **research_notes** — 结构化笔记与标签管理
- **pdf** — 高级 PDF 处理

### 标准 Skill 支持

ResearchClaw 现在不仅支持内置技能，也支持按标准 `SKILL.md` 结构加载外部 skill。

- 推荐格式：一个 skill 一个目录，并且必须包含 `SKILL.md`
- 可选附属目录：`references/`、`scripts/`
- 当前支持的发现位置：
  - 项目内 `skills/`（兼容 OpenClaw 风格）
  - 项目内 `.agents/skills/`
  - 项目内 `.researchclaw/skills/`
  - 用户级 `~/.agents/skills/`
  - 用户级 `~/.researchclaw/skills/`
- 仓库内置的 Python skill 现在也都补齐了 `SKILL.md`，统一走同一套契约

运行时会自动发现这些 skill，同步到 `active_skills/`，并提供：

- `skills_list()`：查看可用 skill
- `skills_activate(name)`：加载完整 `SKILL.md` 与附属文件清单
- `skills_read_file(name, path)`：读取 `SKILL.md`、`references/*` 或 `scripts/*`

## ⚙️ 配置

ResearchClaw 将所有数据存储在本地 `~/.researchclaw/`：

```
~/.researchclaw/
├── config.json          # 主配置
├── .env                 # API 密钥
├── jobs.json            # 定时任务
├── chats.json           # 对话历史
├── active_skills/       # 激活的技能
├── customized_skills/   # 自定义技能
├── memory/              # 研究笔记和知识库
├── papers/              # 论文缓存
├── references/          # BibTeX 文献库
└── experiments/         # 实验追踪数据
```

### 模型提供商配置示例

```bash
# OpenAI
researchclaw models add openai --type openai --model gpt-4o --api-key sk-...

# Anthropic
researchclaw models add anthropic --type anthropic --model claude-3-5-sonnet --api-key sk-ant-...

# Google Gemini（Gemini API / AI Studio key）
researchclaw models add gemini --type gemini --model gemini-2.5-flash --api-key AIza... --base-url https://generativelanguage.googleapis.com/v1beta/openai/

# Ollama（本地模型）
researchclaw models add ollama --type ollama --model qwen3:8b --base-url http://localhost:11434/v1
```

前端“模型配置”页面现在也提供了 `Google Gemini` 预设。
通过 CLI 首次添加的 provider 会自动成为当前激活 provider。

## 🤖 聊天命令

在控制台或接入的聊天频道中，可直接输入以下 `/` 命令：

| 命令 | 说明 |
|------|------|
| `/new` | 开始新的会话 |
| `/start` | `/new` 的别名 |
| `/compact` | 压缩当前对话记忆 |
| `/clear` | 清空历史与摘要 |
| `/history` | 查看当前会话统计 |
| `/compact_str` | 查看当前压缩摘要 |
| `/papers` | 列出最近讨论过的论文 |
| `/refs` | 查看当前参考文献库摘要 |
| `/skills` | 查看当前启用的技能 |
| `/skills debug <query>` | 查看某个 query 的 skill 路由调试信息 |
| `/help` | 显示命令帮助 |

另外还支持一组运行时命令：

| 命令 | 说明 |
|------|------|
| `/daemon status` | 查看运行状态 |
| `/daemon reload-config` | 重载配置 |
| `/daemon version` | 查看版本 |
| `/daemon logs [n]` | 查看最近 `n` 行日志，默认 `100` |

## 📋 CLI 参考

```bash
researchclaw init          # 交互式初始化
researchclaw app           # 启动服务
researchclaw models list   # 查看模型提供商
researchclaw channels list # 查看频道配置
researchclaw env list      # 查看持久化环境变量
researchclaw skills list   # 查看技能状态
researchclaw cron list     # 查看定时任务
researchclaw daemon status # 查看运行状态
```

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING_zh.md](CONTRIBUTING_zh.md)。

## 📄 许可证

Apache License 2.0 — 详见 [LICENSE](LICENSE)。

## 🙏 致谢

ResearchClaw 在通道、定时任务与控制台交互等设计上参考了 [CoPaw](https://github.com/agentscope-ai/CoPaw) 的架构。
感谢 CoPaw 项目提供了可落地、经过验证的实现思路。
