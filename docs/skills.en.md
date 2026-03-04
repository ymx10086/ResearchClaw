# Skills

Skills are ResearchClaw's extensible capability system, providing the AI assistant with specialized research abilities.

## Built-in Skills

ResearchClaw includes several research-related skills:

- **Paper Search**: Search papers on ArXiv, Semantic Scholar, and more
- **Paper Tracking**: Periodically track new papers in specified fields or keywords
- **Reference Management**: Manage BibTeX files, generate citations
- **Weather**: Check weather info (daily utility)

## Skill Structure

Each Skill is an independent Python module:

```
my_skill/
├── __init__.py
├── skill.json          # Skill metadata
├── handler.py          # Main logic
└── requirements.txt    # Dependencies (optional)
```

### skill.json

```json
{
  "name": "my_skill",
  "version": "1.0.0",
  "description": "A custom research skill",
  "author": "Your Name",
  "tags": ["research", "papers"]
}
```

## Installing Skills

### From GitHub

Send in chat:

```
Install skill https://github.com/user/repo
```

### Manual Install

Place the skill folder in the `skills/` directory under your working directory.

## Cron Tasks

Skills support cron-based scheduling:

```python
# Configure in skill.json
{
  "cron": "0 9 * * *",  # Run daily at 9 AM
  "cron_prompt": "Search for LLM Agent papers published yesterday"
}
```

## Custom Development

See [CONTRIBUTING](./contributing.md) for how to develop custom skills.
