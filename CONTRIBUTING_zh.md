# 为 ResearchClaw 贡献代码

ResearchClaw 当前最成熟的部分是运行时基础设施、控制面、通道、provider 和 skills 兼容层。欢迎围绕这些能力，以及文档和 bug 修复提交改动。

## 开发环境

### 后端

```bash
git clone https://github.com/MingxinYang/ResearchClaw.git
cd ResearchClaw
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

如果你不想做 editable install，那么运行测试和本地脚本时请显式设置 `PYTHONPATH=src`。

### Console

```bash
cd console
npm install
```

### Website

```bash
cd website
corepack pnpm install
```

## 提交 PR 前建议执行

后端测试：

```bash
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

如果改动涉及前端格式化敏感文件，也建议执行：

```bash
npm --prefix console run format
corepack pnpm --dir website run format
```

## 文档修改说明

文档主要分布在几个位置：

- 根目录项目文档：`README.md`、`README_zh.md`、`ROADMAP.md`、`CONTRIBUTING*.md`
- website 文档页：`website/public/docs/*.en.md` 与 `website/public/docs/*.zh.md`
- `docs/` 下的架构说明

文档改动请遵循：

- 中英文页面尽量保持同步
- 不要手改 `website/dist/` 下的生成产物
- 新增 docs slug 时，记得同步更新 `website/src/pages/Docs.tsx`
- FAQ 页面依赖 `###` 标题解析，不要改回 `<details>` 结构
- website 构建时会重新生成 `website/public/search-index.json`

## Skills 贡献方式

ResearchClaw 当前采用 `SKILL.md` 优先的标准技能结构。

推荐目录结构：

```text
my-skill/
├── SKILL.md
├── references/
├── scripts/
└── __init__.py 或 main.py   # 只有需要执行代码时才需要
```

关键点：

- `SKILL.md` 是主要的元数据和操作说明文件
- `references/`、`scripts/` 是可选目录
- 支持纯文档型 skill
- 项目级发现目录包括 `skills/`、`.agents/skills/`、`.researchclaw/skills/`
- 用户级发现目录包括 `~/.agents/skills/`、`~/.researchclaw/skills/`

请不要再新增把 `skill.json` 写成“必需格式”的文档，因为这已经不是当前代码契约。

## Pull Request 规范

提交信息和 PR 标题都建议遵循 Conventional Commits：

```text
<type>(<scope>): <subject>
```

例如：

```text
feat(models): add provider preset for x
fix(channels): avoid duplicate session batching
docs(readme): align quick start with current runtime
```

尽量让 PR 聚焦。如果改动涉及 console 或 website 的可视界面，建议附上截图或短录屏。

## 从哪里开始比较合适

比较适合的贡献方向：

- 代码已经变了但文档没跟上的部分
- 控制面和可观测性的缺口或 bug
- provider、channel、MCP 兼容性修复
- 多 agent 路由、automation、通道可靠性的测试补充
- 不依赖完整科研状态机的小型 workflow 改进
