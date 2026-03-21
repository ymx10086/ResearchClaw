# Contributing to ResearchClaw

ResearchClaw is currently strongest in runtime infrastructure, control-plane features, channels, providers, and skills compatibility. Contributions in those areas, plus docs and bug fixes, are welcome.

## Development Setup

### Backend

```bash
git clone https://github.com/MingxinYang/ResearchClaw.git
cd ResearchClaw
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

If you prefer not to install the package editable, set `PYTHONPATH=src` when running tests or local scripts.

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

## Checks Before Opening a PR

Backend tests:

```bash
PYTHONPATH=src pytest -q
```

Console build:

```bash
npm --prefix console run build
```

Website build:

```bash
corepack pnpm --dir website run build
```

Repo-wide helper:

```bash
scripts/check-ci.sh --skip-install
```

If you changed formatting-sensitive frontend files, also run:

```bash
npm --prefix console run format
corepack pnpm --dir website run format
```

## Documentation Changes

The docs surface is split across several places:

- root project docs: `README.md`, `README_zh.md`, `ROADMAP.md`, `CONTRIBUTING*.md`
- website docs: `website/public/docs/*.en.md` and `website/public/docs/*.zh.md`
- architecture notes under `docs/`

Rules for doc changes:

- keep English and Chinese pages aligned
- do not edit generated output under `website/dist/`
- if you add a new docs slug, update `website/src/pages/Docs.tsx`
- FAQ pages are parsed from `###` headings, so do not switch them to `<details>` blocks
- website builds regenerate `website/public/search-index.json`

## Skills Contributions

ResearchClaw now uses a standard `SKILL.md`-first workflow.

Preferred skill structure:

```text
my-skill/
├── SKILL.md
├── references/
├── scripts/
└── __init__.py or main.py   # optional, only if the skill executes code
```

Key points:

- `SKILL.md` is the primary metadata and operating-playbook file
- `references/` and `scripts/` are optional
- doc-only skills are supported
- project-local discovery includes `skills/`, `.agents/skills/`, and `.researchclaw/skills/`
- user-level discovery includes `~/.agents/skills/` and `~/.researchclaw/skills/`

Do not add new docs that describe `skill.json` as the required format. That is no longer the current contract.

## Pull Requests

Use Conventional Commits for both commits and PR titles:

```text
<type>(<scope>): <subject>
```

Examples:

```text
feat(models): add provider preset for x
fix(channels): avoid duplicate session batching
docs(readme): align quick start with current runtime
```

Keep PRs focused. If you change console or website UX, include screenshots or a short screen recording.

## Where to Start

Good contribution areas:

- docs that drifted behind the code
- control-plane bugs and observability gaps
- provider, channel, or MCP compatibility fixes
- tests around multi-agent routing, automation, and channel reliability
- small workflow improvements that do not assume a full research state machine already exists
