# Contributing

This page is the short version of the repository contributor guide.

## Setup

### Backend

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

## Recommended Checks

```bash
PYTHONPATH=src pytest -q
npm --prefix console run build
corepack pnpm --dir website run build
scripts/check-ci.sh --skip-install
```

## Docs Rules

- keep `*.en.md` and `*.zh.md` in sync
- do not edit `website/dist/`
- update `website/src/pages/Docs.tsx` when adding a new docs slug
- FAQ pages use `###` headings, not `<details>`

## Skills Rules

Use `SKILL.md` as the primary skill contract. Do not write new docs that make `skill.json` sound mandatory.

## PR Titles

Use Conventional Commits style:

```text
docs(readme): align quick start with current runtime
fix(channels): avoid duplicate batching
feat(models): add provider preset
```

For the full version, see the repository-level [Contributing Guide](./contributing.md).
