# Skills

ResearchClaw uses a `SKILL.md`-first skill system.

## What a Skill Is

A skill can be either:

- a doc-only operational playbook
- a Python-backed capability with executable tools

The preferred standard format is:

```text
my-skill/
├── SKILL.md
├── references/
├── scripts/
└── __init__.py or main.py   # optional
```

## Built-in Skills

The repository currently ships these built-in skills:

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

## Discovery Locations

The runtime scans:

- `skills/`
- `.agents/skills/`
- `.researchclaw/skills/`
- `~/.agents/skills/`
- `~/.researchclaw/skills/`

Built-in skills are also synced into the active skill area.

## Runtime Storage

- enabled skills live under `active_skills/`
- local custom copies live under `customized_skills/`

## How to Manage Skills

CLI:

```bash
researchclaw skills list
researchclaw skills config
```

API:

- `GET /api/skills`
- `GET /api/skills/active`
- `POST /api/skills/enable`
- `POST /api/skills/disable`
- `POST /api/skills/install`
- `GET /api/skills/hub/search`

Agent tools:

- `skills_list()`
- `skills_activate(name)`
- `skills_read_file(name, path)`

The runtime also ships a dedicated `research_workflows` skill module that exposes structured tools for:

- projects and dashboards
- workflows and tasks
- notes, claims, evidence, and experiments
- remediation lookup and task execution

## Notes

- `SKILL.md` is the current contract; do not rely on old `skill.json`-only docs
- optional `references/` and `scripts/` files are readable through runtime skill tools
- some bundled research skills are still lightweight wrappers, but `research_workflows` is now the stateful bridge into the Research OS layer
