# 贡献指南

这是仓库级贡献文档的简版摘要。

## 环境准备

### 后端

```bash
git clone https://github.com/MingxinYang/ResearchClaw.git
cd ResearchClaw
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

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

## 建议检查项

```bash
PYTHONPATH=src pytest -q
npm --prefix console run build
corepack pnpm --dir website run build
scripts/check-ci.sh --skip-install
```

## 文档规则

- `*.en.md` 和 `*.zh.md` 尽量保持同步
- 不要手改 `website/dist/`
- 新增 docs slug 时记得更新 `website/src/pages/Docs.tsx`
- FAQ 页面使用 `###` 标题，不使用 `<details>`

## Skills 规则

当前 skill 契约以 `SKILL.md` 为主，不要再写把 `skill.json` 说成必需格式的新文档。

## PR 标题

建议使用 Conventional Commits 风格：

```text
docs(readme): align quick start with current runtime
fix(channels): avoid duplicate batching
feat(models): add provider preset
```

更完整的版本见仓库级 [贡献指南](./contributing.md)。
