# Skills

ResearchClaw 当前采用 `SKILL.md` 优先的技能系统。

## Skill 是什么

一个 skill 可以是：

- 纯文档型操作手册
- 带 Python 可执行能力的技能模块

当前推荐的标准结构是：

```text
my-skill/
├── SKILL.md
├── references/
├── scripts/
└── __init__.py 或 main.py   # 可选
```

## 仓库内置 Skills

当前仓库自带这些 skills：

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

## 发现目录

运行时会扫描：

- `skills/`
- `.agents/skills/`
- `.researchclaw/skills/`
- `~/.agents/skills/`
- `~/.researchclaw/skills/`

仓库内置 skills 也会被同步到 active skill 区域。

## 运行时存储

- 已启用的 skills 位于 `active_skills/`
- 本地自定义拷贝位于 `customized_skills/`

## 如何管理 Skills

CLI：

```bash
researchclaw skills list
researchclaw skills config
```

API：

- `GET /api/skills`
- `GET /api/skills/active`
- `POST /api/skills/enable`
- `POST /api/skills/disable`
- `POST /api/skills/install`
- `GET /api/skills/hub/search`

Agent tools：

- `skills_list()`
- `skills_activate(name)`
- `skills_read_file(name, path)`

运行时现在还内置了一个专门的 `research_workflows` skill 模块，用来暴露结构化工具，覆盖：

- projects 与 dashboard
- workflows 与 tasks
- notes、claims、evidence、experiments
- remediation 查询与 task 执行

## 说明

- 当前契约是 `SKILL.md`，不要再依赖旧的 `skill.json` 文档
- 可选的 `references/` 和 `scripts/` 可以通过运行时 skill tools 读取
- 一些科研 skill 目前仍然只是轻量封装，但 `research_workflows` 已经是接入 Research OS 状态层的核心桥接模块
