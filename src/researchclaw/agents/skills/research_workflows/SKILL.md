---
name: research-workflows
description: "Manage project-centric research workflows, claims, evidence, notes, and experiments. Use when the task should be persisted into ResearchClaw's structured research graph instead of remaining a transient chat reply."
emoji: "🧭"
triggers:
  - workflow
  - research workflow
  - project dashboard
  - claim evidence
  - experiment tracking
  - structured notes
---

# Research Workflows

Use this skill when the user is working on a long-running project and the result should be persisted into the structured research system.

## Tools

- `research_projects_list`
- `research_project_create`
- `research_project_dashboard`
- `research_workflows_list`
- `research_workflow_create`
- `research_workflow_get`
- `research_workflow_add_task`
- `research_workflow_update_task`
- `research_workflow_tick`
- `research_note_create`
- `research_notes_search`
- `research_claim_create`
- `research_claim_attach_evidence`
- `research_claim_graph`
- `research_experiment_log`
- `research_experiment_compare`

## Guidance

- Prefer storing durable work in the structured graph when it will matter beyond the current turn.
- Use `research_workflow_get` before updating a workflow task.
- When making a substantive claim, attach evidence instead of leaving it implicit.
- When logging an experiment, include metrics or archived outputs whenever possible.
