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

### 安装

```bash
pip install researchclaw
```

### 初始化

```bash
researchclaw init --defaults
```

这将设置你的工作目录 (`~/.researchclaw`) 并配置 LLM 提供商。

### 启动

```bash
researchclaw app
```

在浏览器中打开 [http://127.0.0.1:8088/](http://127.0.0.1:8088/)。

### 一键安装

```bash
curl -fsSL https://researchclaw.github.io/install.sh | bash
```

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
     ├── 模型：OpenAI / Anthropic / DashScope / 本地模型
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

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING_zh.md](CONTRIBUTING_zh.md)。

## 📄 许可证

Apache License 2.0 — 详见 [LICENSE](LICENSE)。

## 🙏 致谢

ResearchClaw 在通道、定时任务与控制台交互等设计上参考了 [CoPaw](https://github.com/agentscope-ai/CoPaw) 的架构。  
感谢 CoPaw 项目提供了可落地、经过验证的实现思路。
