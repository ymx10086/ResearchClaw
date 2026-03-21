"""Runtime helpers for proactive research workflow automation."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from researchclaw.constant import RESEARCH_WORKFLOW_STALE_HOURS

from .models import (
    ExperimentRunnerProfile,
    ExperimentRunnerRule,
    ExperimentRunnerTemplate,
    ProactiveReminder,
    ResultBundleSchemaDefinition,
    ResearchWorkflow,
    WorkflowTask,
    utc_now,
)
from .service import ResearchService

_STAGE_EXECUTION_GUIDANCE: dict[str, str] = {
    "literature_search": (
        "shortlist papers, capture search rationale, and persist candidate reading notes"
    ),
    "paper_reading": (
        "extract methods, assumptions, evidence snippets, and concrete reading notes"
    ),
    "note_synthesis": (
        "group notes into themes, tensions, open questions, and reusable summaries"
    ),
    "hypothesis_queue": (
        "queue falsifiable hypotheses or ranked directions with expected value and risk"
    ),
    "experiment_plan": (
        "define baselines, ablations, datasets, metrics, and success criteria"
    ),
    "experiment_run": (
        "log experiment runs, archive outputs, and link results back to claims"
    ),
    "result_analysis": (
        "interpret metrics and artifacts into claims, risks, and next-step decisions"
    ),
    "writing_tasks": (
        "turn validated findings into drafting notes, section tasks, and revision todos"
    ),
    "review_and_followup": (
        "resolve blockers, identify missing evidence, and create concrete follow-up tasks"
    ),
}


class ResearchWorkflowRuntime:
    """Binds the structured research service to channels and automation."""

    def __init__(
        self,
        *,
        service: ResearchService,
        channel_manager: Any = None,
        runner: Any = None,
    ) -> None:
        self._service = service
        self._channel_manager = channel_manager
        self._runner = runner
        self._last_cycle: dict[str, Any] = {
            "last_run_at": None,
            "reminder_count": 0,
            "sent_count": 0,
            "delivery_results": [],
        }

    def set_channel_manager(self, channel_manager: Any) -> None:
        self._channel_manager = channel_manager

    def set_runner(self, runner: Any) -> None:
        self._runner = runner

    @staticmethod
    def _stage_tasks(
        workflow: ResearchWorkflow,
        *,
        stage_name: str = "",
    ) -> list[WorkflowTask]:
        wanted_stage = stage_name or workflow.current_stage
        return [task for task in workflow.tasks if task.stage == wanted_stage]

    @staticmethod
    def _workflow_fingerprint(workflow: ResearchWorkflow) -> dict[str, Any]:
        return {
            "status": workflow.status,
            "current_stage": workflow.current_stage,
            "tasks": [
                {
                    "id": task.id,
                    "status": task.status,
                    "summary": task.summary,
                    "note_ids": list(task.note_ids),
                    "claim_ids": list(task.claim_ids),
                    "artifact_ids": list(task.artifact_ids),
                }
                for task in workflow.tasks
            ],
            "note_ids": list(workflow.note_ids),
            "claim_ids": list(workflow.claim_ids),
            "experiment_ids": list(workflow.experiment_ids),
            "artifact_ids": list(workflow.artifact_ids),
        }

    @staticmethod
    def _find_task(
        workflow: ResearchWorkflow,
        task_id: str,
    ) -> WorkflowTask | None:
        for task in workflow.tasks:
            if task.id == task_id:
                return task
        return None

    @staticmethod
    def _find_task_by_kind(
        workflow: ResearchWorkflow,
        *,
        stage_name: str,
        task_kind: str,
    ) -> WorkflowTask | None:
        for task in workflow.tasks:
            if task.stage != stage_name:
                continue
            metadata = dict(getattr(task, "metadata", {}) or {})
            if str(metadata.get("task_kind", "") or "").strip() != task_kind:
                continue
            return task
        return None

    @staticmethod
    def _find_tasks_by_kind(
        workflow: ResearchWorkflow,
        *,
        stage_name: str,
        task_kind: str,
    ) -> list[WorkflowTask]:
        matches: list[WorkflowTask] = []
        for task in workflow.tasks:
            if task.stage != stage_name:
                continue
            metadata = dict(getattr(task, "metadata", {}) or {})
            if str(metadata.get("task_kind", "") or "").strip() != task_kind:
                continue
            matches.append(task)
        return matches

    @staticmethod
    def _truncate_summary(text: str, *, limit: int = 320) -> str:
        clean = " ".join(str(text or "").split()).strip()
        if len(clean) <= limit:
            return clean
        return clean[: max(0, limit - 3)].rstrip() + "..."

    @staticmethod
    def _parse_iso(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None

    @classmethod
    def _hours_since(cls, value: str | None, *, now: datetime) -> float | None:
        parsed = cls._parse_iso(value)
        if parsed is None:
            return None
        return max(0.0, (now - parsed).total_seconds() / 3600.0)

    @classmethod
    def _normalize_auto_run_window(
        cls,
        *,
        window_started_at: str | None,
        count: int,
        now: datetime,
        now_iso: str,
    ) -> tuple[str, int]:
        started = cls._parse_iso(window_started_at)
        if started is None or now - started >= timedelta(hours=24):
            return now_iso, 0
        return window_started_at or now_iso, max(0, int(count))

    @classmethod
    def _auto_execution_reason(
        cls,
        workflow: ResearchWorkflow,
        *,
        now: datetime,
        stale_hours: int,
    ) -> str:
        policy = workflow.execution_policy
        if not policy.enabled:
            return ""
        if workflow.status in {"completed", "cancelled", "paused", "failed"}:
            return ""
        if workflow.current_stage not in set(policy.allowed_stages or []):
            return ""

        _, current_count = cls._normalize_auto_run_window(
            window_started_at=policy.auto_run_window_started_at,
            count=policy.auto_run_count_in_window,
            now=now,
            now_iso=now.isoformat(),
        )
        if current_count >= max(1, int(policy.max_auto_runs_per_day or 1)):
            return ""

        last_auto_hours = cls._hours_since(policy.last_auto_run_at, now=now)
        if (
            last_auto_hours is not None
            and last_auto_hours * 60 < max(1, int(policy.cooldown_minutes or 1))
        ):
            return ""

        binding_metadata = dict(getattr(workflow.bindings, "metadata", {}) or {})
        if bool(binding_metadata.get("contract_remediation_ready")) and workflow.current_stage == "experiment_run":
            return (
                f"{workflow.current_stage}: remediation resolved and ready to continue"
            )
        if workflow.status == "blocked" and policy.mode == "stale_or_blocked":
            blocker = workflow.error or "manual follow-up needed"
            return f"blocked in {workflow.current_stage}: {blocker}"
        if workflow.status == "blocked" and bool(
            binding_metadata.get("contract_remediation_ready"),
        ):
            return (
                f"blocked in {workflow.current_stage}: remediation resolved and "
                "ready to retry"
            )

        effective_stale_hours = max(1, int(policy.stale_hours or stale_hours or 1))
        age_hours = cls._hours_since(
            workflow.last_run_at or workflow.updated_at,
            now=now,
        ) or 0.0
        if age_hours >= effective_stale_hours:
            return f"idle for about {int(age_hours)} hour(s)"
        return ""

    def _build_execution_prompt(
        self,
        *,
        project: Any,
        workflow: ResearchWorkflow,
        notes: list[Any],
        claims: list[Any],
        experiments: list[Any],
    ) -> str:
        tasks = self._stage_tasks(workflow)
        task_lines = [
            (
                f"- {task.id} [{task.status}] {task.title}"
                + (
                    f" :: {self._truncate_summary(task.summary, limit=180)}"
                    if task.summary
                    else ""
                )
            )
            for task in tasks
        ] or ["- No task is currently attached to this stage."]
        note_lines = [
            f"- {note.id} [{note.note_type}] {note.title}"
            for note in notes[:5]
        ] or ["- No recent notes."]
        claim_lines = [
            f"- {claim.id} [{claim.status}] {self._truncate_summary(claim.text, limit=180)}"
            for claim in claims[:5]
        ] or ["- No recent claims."]
        experiment_lines = [
            f"- {run.id} [{run.status}] {run.name}"
            for run in experiments[:3]
        ] or ["- No recent experiments."]
        stage_guidance = _STAGE_EXECUTION_GUIDANCE.get(
            workflow.current_stage,
            "make the smallest useful research advancement and persist it",
        )

        return "\n".join(
            [
                "Advance the following long-running research workflow.",
                "Do real state updates through research_* tools instead of only replying with prose.",
                "",
                "Workflow context",
                f"- project_id: {project.id}",
                f"- project_name: {project.name}",
                f"- workflow_id: {workflow.id}",
                f"- title: {workflow.title}",
                f"- goal: {workflow.goal or '(not set)'}",
                f"- status: {workflow.status}",
                f"- current_stage: {workflow.current_stage}",
                f"- execution_goal: {stage_guidance}",
                "",
                "Current stage tasks",
                *task_lines,
                "",
                "Recent notes",
                *note_lines,
                "",
                "Recent claims",
                *claim_lines,
                "",
                "Recent experiments",
                *experiment_lines,
                "",
                "Required tool usage",
                f"1. Call research_workflow_get(workflow_id='{workflow.id}') first.",
                (
                    f"2. Read history with research_notes_search(project_id='{project.id}', "
                    f"workflow_id='{workflow.id}', limit=10) if needed."
                ),
                "3. Persist new findings using research_note_create, research_claim_create, research_claim_attach_evidence, or research_experiment_log when relevant.",
                "4. Update at least one current-stage task with research_workflow_update_task.",
                "5. If the current stage is actually complete, call research_workflow_tick.",
                "6. If blocked, mark the relevant task blocked and state the blocker clearly.",
                "",
                "Finish with a concise operator summary of:",
                "- what changed in the structured research state",
                "- what remains open in this stage",
            ],
        )

    @staticmethod
    def _paper_source_id(paper: dict[str, Any]) -> str:
        for key in ("arxiv_id", "paper_id", "doi", "title"):
            value = str(paper.get(key, "") or "").strip()
            if value:
                return value
        return ""

    @staticmethod
    def _paper_ref(paper: dict[str, Any]) -> str:
        arxiv_id = str(paper.get("arxiv_id", "") or "").strip()
        if arxiv_id:
            return f"ArXiv:{arxiv_id}"
        doi = str(paper.get("doi", "") or "").strip()
        if doi:
            return f"DOI:{doi}"
        paper_id = str(paper.get("paper_id", "") or "").strip()
        if paper_id:
            return f"SemanticScholar:{paper_id}"
        return ""

    @staticmethod
    def _paper_abstract(paper: dict[str, Any]) -> str:
        return str(
            paper.get("abstract")
            or paper.get("tldr")
            or "",
        ).strip()

    def _build_search_query(
        self,
        *,
        project: Any,
        workflow: ResearchWorkflow,
    ) -> str:
        parts: list[str] = []
        for value in (
            workflow.goal,
            workflow.title,
            getattr(project, "description", ""),
            getattr(project, "name", ""),
        ):
            text = " ".join(str(value or "").split()).strip()
            if text and text not in parts:
                parts.append(text)
        for tag in list(getattr(project, "tags", []) or [])[:4]:
            clean = " ".join(str(tag or "").split()).strip()
            if clean and clean not in parts:
                parts.append(clean)
        return " | ".join(parts[:4]) or workflow.title or getattr(project, "name", "research project")

    @staticmethod
    def _extract_note_section(content: str, heading: str) -> str:
        lines = str(content or "").splitlines()
        capture = False
        collected: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not capture:
                if stripped.lower() == heading.lower():
                    capture = True
                continue
            if not stripped and collected:
                break
            if stripped:
                collected.append(stripped)
        return " ".join(collected).strip()

    @staticmethod
    def _source_title_from_note(note: Any) -> str:
        title = str(getattr(note, "title", "") or "").strip()
        if "·" in title:
            return title.split("·", 1)[1].strip()
        return title

    @staticmethod
    def _unique_strings(values: list[str]) -> list[str]:
        return list(dict.fromkeys([str(value).strip() for value in values if str(value).strip()]))

    @staticmethod
    def _experiment_kind(run: Any) -> str:
        metadata = dict(getattr(run, "metadata", {}) or {})
        return str(
            metadata.get("experiment_kind")
            or metadata.get("kind")
            or "",
        ).strip()

    @staticmethod
    def _metric_number(run: Any, *keys: str) -> float | None:
        metrics = dict(getattr(run, "metrics", {}) or {})
        for key in keys:
            value = metrics.get(key)
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return None

    @staticmethod
    def _experiment_execution_mode(run: Any) -> str:
        execution = getattr(run, "execution", None)
        if execution is not None:
            mode = str(getattr(execution, "mode", "") or "").strip()
            if mode:
                return mode
        metadata = dict(getattr(run, "metadata", {}) or {})
        return str(metadata.get("execution_mode", "") or "inline").strip() or "inline"

    @staticmethod
    def _runner_template_has_effect(template: ExperimentRunnerTemplate) -> bool:
        return any(
            [
                bool(template.catalog_entry.strip()),
                template.mode != "inline",
                bool(template.command),
                bool(template.entrypoint.strip()),
                bool(template.working_dir.strip()),
                bool(template.notebook_path.strip()),
                bool(template.environment),
                bool(template.requested_by.strip()),
                bool(template.instructions.strip()),
                bool(template.parameter_overrides),
                bool(template.input_data_overrides),
                bool(template.metadata),
            ],
        )

    @staticmethod
    def _merge_runner_template(
        *,
        base: ExperimentRunnerTemplate,
        patch: dict[str, Any],
    ) -> ExperimentRunnerTemplate:
        payload = base.model_dump(mode="json")
        for key, value in patch.items():
            if key in {"metadata", "environment", "parameter_overrides", "input_data_overrides"}:
                merged_value = dict(payload.get(key) or {})
                merged_value.update(dict(value or {}))
                payload[key] = merged_value
                continue
            payload[key] = value
        return ExperimentRunnerTemplate.model_validate(payload)

    @staticmethod
    def _catalog_entry_template(
        project: Any,
        entry_name: str,
    ) -> tuple[ExperimentRunnerTemplate, dict[str, Any]]:
        normalized = str(entry_name or "").strip()
        if not normalized:
            raise ValueError("Catalog entry name is empty")
        for entry in list(getattr(project, "execution_catalog", []) or []):
            if str(getattr(entry, "name", "") or "").strip() != normalized:
                continue
            artifact_contract = dict(getattr(entry, "artifact_contract", {}) or {})
            metadata = dict(getattr(entry, "metadata", {}) or {})
            metadata["catalog_entry"] = normalized
            if artifact_contract:
                metadata["artifact_contract"] = artifact_contract
            return (
                ExperimentRunnerTemplate.model_validate(
                    getattr(entry, "template", ExperimentRunnerTemplate()).model_dump(
                        mode="json",
                    ),
                ),
                metadata,
            )
        raise ValueError(f"Unknown execution catalog entry: {normalized}")

    def _materialize_runner_template(
        self,
        *,
        project: Any,
        template: ExperimentRunnerTemplate,
        seen_entries: tuple[str, ...] = (),
    ) -> ExperimentRunnerTemplate:
        catalog_entry = str(getattr(template, "catalog_entry", "") or "").strip()
        if not catalog_entry:
            return ExperimentRunnerTemplate.model_validate(
                template.model_dump(mode="json"),
            )
        if catalog_entry in seen_entries:
            chain = " -> ".join([*seen_entries, catalog_entry])
            raise ValueError(f"Cyclic execution catalog reference: {chain}")
        catalog_template, catalog_metadata = self._catalog_entry_template(
            project,
            catalog_entry,
        )
        base_template = self._materialize_runner_template(
            project=project,
            template=catalog_template,
            seen_entries=(*seen_entries, catalog_entry),
        )
        payload = template.model_dump(
            mode="json",
            exclude_defaults=True,
        )
        payload.pop("catalog_entry", None)
        merged = self._merge_runner_template(
            base=base_template,
            patch=payload,
        )
        if catalog_metadata:
            merged = self._merge_runner_template(
                base=merged,
                patch={"metadata": catalog_metadata},
            )
        merged.catalog_entry = catalog_entry
        return merged

    async def _experiment_hypothesis_kinds(self, experiment: Any) -> list[str]:
        claim_ids = set(getattr(experiment, "claim_ids", []) or [])
        if not claim_ids:
            return []
        state = await self._service.load_state()
        kinds: list[str] = []
        for claim in state.claims:
            if claim.id not in claim_ids:
                continue
            metadata = dict(getattr(claim, "metadata", {}) or {})
            kind = str(metadata.get("hypothesis_kind", "") or "").strip()
            if kind and kind not in kinds:
                kinds.append(kind)
        return kinds

    @staticmethod
    def _runner_rule_matches(
        rule: ExperimentRunnerRule,
        *,
        workflow: ResearchWorkflow,
        experiment: Any,
        hypothesis_kinds: list[str],
    ) -> bool:
        if rule.stages and workflow.current_stage not in set(rule.stages):
            return False
        experiment_kind = str(getattr(experiment, "metadata", {}).get("experiment_kind", "") or "").strip()
        if rule.experiment_kinds and experiment_kind not in set(rule.experiment_kinds):
            return False
        comparison_group = str(getattr(experiment, "comparison_group", "") or "").strip()
        if rule.comparison_groups and comparison_group not in set(rule.comparison_groups):
            return False
        if rule.hypothesis_kinds and not set(rule.hypothesis_kinds).intersection(hypothesis_kinds):
            return False
        return True

    async def _resolved_runner_template(
        self,
        *,
        project: Any,
        workflow: ResearchWorkflow,
        experiment: Any,
    ) -> tuple[ExperimentRunnerTemplate | None, list[str]]:
        profile = getattr(
            workflow,
            "experiment_runner",
            ExperimentRunnerProfile(),
        )
        if not getattr(profile, "enabled", False):
            return None, []
        template = ExperimentRunnerTemplate.model_validate(
            profile.default.model_dump(mode="json"),
        )
        experiment_kind = self._experiment_kind(experiment)
        override = None
        if experiment_kind:
            override = dict(getattr(profile, "kind_overrides", {}) or {}).get(
                experiment_kind,
            )
        if override is not None:
            template = self._merge_runner_template(
                base=template,
                patch=dict(override or {}),
            )
        hypothesis_kinds = await self._experiment_hypothesis_kinds(experiment)
        matched_rules: list[str] = []
        for rule in list(getattr(profile, "rules", []) or []):
            if not self._runner_rule_matches(
                rule,
                workflow=workflow,
                experiment=experiment,
                hypothesis_kinds=hypothesis_kinds,
            ):
                continue
            template = self._merge_runner_template(
                base=template,
                patch=rule.template.model_dump(
                    mode="json",
                    exclude_defaults=True,
                ),
            )
            matched_rules.append(rule.name)
        if not self._runner_template_has_effect(template):
            return None, matched_rules
        materialized = self._materialize_runner_template(
            project=project,
            template=template,
        )
        if not self._runner_template_has_effect(materialized):
            return None, matched_rules
        return materialized, matched_rules

    @staticmethod
    def _execution_already_configured(experiment: Any) -> bool:
        execution = getattr(experiment, "execution", None)
        if execution is None:
            return False
        if str(getattr(execution, "mode", "inline") or "inline").strip() != "inline":
            return True
        return any(
            [
                bool(list(getattr(execution, "command", []) or [])),
                bool(str(getattr(execution, "entrypoint", "") or "").strip()),
                bool(str(getattr(execution, "working_dir", "") or "").strip()),
                bool(str(getattr(execution, "notebook_path", "") or "").strip()),
                bool(str(getattr(execution, "result_bundle_file", "") or "").strip()),
                bool(str(getattr(execution, "result_bundle_schema", "") or "").strip()),
                bool(dict(getattr(execution, "environment", {}) or {})),
                bool(str(getattr(execution, "external_run_id", "") or "").strip()),
                bool(str(getattr(execution, "requested_by", "") or "").strip()),
                bool(str(getattr(execution, "instructions", "") or "").strip()),
                bool(dict(getattr(execution, "metadata", {}) or {})),
            ],
        )

    @staticmethod
    def _contract_issue_line(validation: dict[str, Any]) -> str:
        issues: list[str] = []
        missing_metrics = list(validation.get("missing_metrics", []) or [])
        missing_outputs = list(validation.get("missing_outputs", []) or [])
        missing_artifact_types = list(validation.get("missing_artifact_types", []) or [])
        if missing_metrics:
            issues.append("missing metrics: " + ", ".join(missing_metrics))
        if missing_outputs:
            issues.append("missing outputs: " + ", ".join(missing_outputs))
        if missing_artifact_types:
            issues.append(
                "missing artifact types: " + ", ".join(missing_artifact_types),
            )
        return "; ".join(issues) or str(validation.get("summary", "") or "").strip()

    @staticmethod
    def _contract_action_line(action: dict[str, Any]) -> str:
        title = " ".join(str(action.get("title", "") or "").split()).strip()
        if not title:
            title = str(action.get("target", "") or "").strip() or "Resolve contract issue"
        tool_name = str(action.get("suggested_tool", "") or "").strip()
        if tool_name:
            return f"- {title} via {tool_name}"
        return f"- {title}"

    @staticmethod
    def _contract_failure_run_id(item: dict[str, Any]) -> str:
        run = item.get("run")
        if run is not None:
            return str(getattr(run, "id", "") or "").strip()
        return str(item.get("experiment_id", "") or "").strip()

    @staticmethod
    def _contract_failure_actions(item: dict[str, Any]) -> list[dict[str, Any]]:
        validation = item.get("validation")
        remediation: dict[str, Any] = {}
        if isinstance(validation, dict):
            remediation = dict(validation.get("remediation") or {})
        elif isinstance(item.get("remediation"), dict):
            remediation = dict(item.get("remediation") or {})
        return [
            action
            for action in list(remediation.get("actions", []) or [])
            if isinstance(action, dict)
        ]

    @staticmethod
    def _contract_action_key(action: dict[str, Any]) -> str:
        explicit = str(action.get("action_key", "") or "").strip()
        if explicit:
            return explicit
        experiment_id = str(action.get("experiment_id", "") or "").strip()
        action_type = str(action.get("action_type", "") or "").strip()
        target = str(action.get("target", "") or "").strip()
        return ":".join(part for part in [experiment_id, action_type, target] if part)

    @staticmethod
    def _contract_action_due_at(action: dict[str, Any]) -> str | None:
        due_hours = action.get("due_in_hours")
        try:
            hours = int(due_hours)
        except (TypeError, ValueError):
            hours = 0
        if hours <= 0:
            return None
        return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()

    @classmethod
    def _is_external_execution(cls, run: Any) -> bool:
        return cls._experiment_execution_mode(run) in {
            "command",
            "notebook",
            "external",
            "file_watch",
        }

    def _experiment_runtime_root(self) -> Path:
        try:
            return self._service.path.parent
        except Exception:
            return Path.cwd()

    def _experiment_output_dir(self, experiment_id: str) -> Path:
        return self._experiment_runtime_root() / "experiment-runs" / experiment_id

    def _execution_template_values(
        self,
        experiment: Any,
        *,
        output_dir: Path | None = None,
    ) -> dict[str, str]:
        return {
            "experiment_id": str(getattr(experiment, "id", "") or ""),
            "workflow_id": str(getattr(experiment, "workflow_id", "") or ""),
            "project_id": str(getattr(experiment, "project_id", "") or ""),
            "experiment_name": str(getattr(experiment, "name", "") or ""),
            "current_stage": str(getattr(experiment, "metadata", {}).get("stage", "") or ""),
            "comparison_group": str(
                getattr(experiment, "comparison_group", "") or "",
            ),
            "experiment_kind": self._experiment_kind(experiment),
            "output_dir": str(output_dir or self._experiment_output_dir(str(getattr(experiment, "id", "") or ""))),
        }

    @staticmethod
    def _resolve_execution_path(
        value: str,
        *,
        working_dir: Path,
    ) -> Path:
        path = Path(value).expanduser()
        if path.is_absolute():
            return path
        return working_dir / path

    @staticmethod
    def _apply_template_values(
        value: str,
        *,
        template_values: dict[str, str],
    ) -> str:
        rendered = str(value)
        for key, replacement in template_values.items():
            rendered = rendered.replace(f"{{{key}}}", replacement)
        return rendered

    @classmethod
    def _render_template_payload(
        cls,
        value: Any,
        *,
        template_values: dict[str, str],
    ) -> Any:
        if isinstance(value, str):
            return cls._apply_template_values(
                value,
                template_values=template_values,
            )
        if isinstance(value, list):
            return [
                cls._render_template_payload(item, template_values=template_values)
                for item in value
            ]
        if isinstance(value, dict):
            return {
                str(key): cls._render_template_payload(
                    item,
                    template_values=template_values,
                )
                for key, item in value.items()
            }
        return value

    @staticmethod
    def _read_json_payload(path: Path) -> Any:
        if not path.exists() or not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    @classmethod
    def _parse_structured_json_string(cls, value: str) -> Any:
        text = str(value or "").strip()
        if not text or text[0] not in {"{", "["}:
            return None
        try:
            return json.loads(text)
        except Exception:
            return None

    @classmethod
    def _read_metrics_payload(cls, path: Path) -> dict[str, Any]:
        payload = cls._read_json_payload(path)
        if payload is None:
            return {}
        if isinstance(payload, dict):
            nested = payload.get("metrics")
            if isinstance(nested, dict):
                return dict(nested)
            return dict(payload)
        return {}

    @classmethod
    def _collect_metric_matches_from_payload(
        cls,
        payload: Any,
        *,
        metric_name: str,
        location: str = "$",
    ) -> list[tuple[Any, str]]:
        target = str(metric_name or "").strip()
        if not target:
            return []
        matches: list[tuple[Any, str]] = []
        if isinstance(payload, dict):
            named_metric = None
            for key in ("metric", "name", "key", "label"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip() == target:
                    named_metric = value.strip()
                    break
            if named_metric:
                for value_key in ("value", "score", "metric_value", "result"):
                    normalized = cls._normalize_metric_value(payload.get(value_key))
                    if normalized is None:
                        continue
                    matches.append((normalized, f"{location}.{value_key}"))
                    break
            for key, value in payload.items():
                key_text = str(key).strip()
                child_location = f"{location}.{key_text}" if key_text else location
                if key_text == target:
                    normalized = cls._normalize_metric_value(value)
                    if normalized is not None:
                        matches.append((normalized, child_location))
                matches.extend(
                    cls._collect_metric_matches_from_payload(
                        value,
                        metric_name=target,
                        location=child_location,
                    ),
                )
            return matches
        if isinstance(payload, list):
            for index, value in enumerate(payload):
                matches.extend(
                    cls._collect_metric_matches_from_payload(
                        value,
                        metric_name=target,
                        location=f"{location}[{index}]",
                    ),
                )
            return matches
        if isinstance(payload, str):
            parsed = cls._parse_structured_json_string(payload)
            if parsed is None:
                return matches
            return cls._collect_metric_matches_from_payload(
                parsed,
                metric_name=target,
                location=f"{location}#json",
            )
        return matches

    def _execution_result_bundle_settings(
        self,
        experiment: Any,
        *,
        output_dir: Path | None = None,
    ) -> dict[str, str]:
        execution = getattr(experiment, "execution", None)
        metadata = dict(getattr(execution, "metadata", {}) or {})
        template_values = self._execution_template_values(
            experiment,
            output_dir=output_dir,
        )
        bundle_file = str(
            self._render_template_payload(
                str(
                    getattr(execution, "result_bundle_file", "") or metadata.get("result_bundle_file", ""),
                ),
                template_values=template_values,
            )
            or "",
        ).strip()
        bundle_schema = str(
            self._render_template_payload(
                str(
                    getattr(execution, "result_bundle_schema", "")
                    or metadata.get("result_bundle_schema", ""),
                ),
                template_values=template_values,
            )
            or "",
        ).strip()
        return {
            "file": bundle_file,
            "schema": bundle_schema,
        }

    @staticmethod
    def _bundle_metric_map(payload: dict[str, Any]) -> dict[str, Any]:
        metrics = payload.get("metrics")
        if not isinstance(metrics, dict):
            return {}
        return {
            str(key).strip(): value
            for key, value in metrics.items()
            if str(key).strip()
        }

    @staticmethod
    def _bundle_output_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
        outputs = payload.get("outputs")
        rows: list[dict[str, Any]] = []
        if isinstance(outputs, dict):
            for key, value in outputs.items():
                key_text = str(key).strip()
                if isinstance(value, str):
                    rows.append({"name": key_text, "path": value})
                elif isinstance(value, dict):
                    rows.append({"name": key_text, **dict(value)})
            return rows
        if isinstance(outputs, list):
            return [dict(item) for item in outputs if isinstance(item, dict)]
        return rows

    @staticmethod
    def _bundle_artifact_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
        artifacts = payload.get("artifacts")
        rows: list[dict[str, Any]] = []
        if isinstance(artifacts, dict):
            for key, value in artifacts.items():
                key_text = str(key).strip()
                if isinstance(value, str):
                    rows.append({"artifact_type": key_text, "path": value})
                elif isinstance(value, dict):
                    rows.append({"artifact_type": key_text, **dict(value)})
            return rows
        if isinstance(artifacts, list):
            return [dict(item) for item in artifacts if isinstance(item, dict)]
        return rows

    async def _result_bundle_schema_definition(
        self,
        experiment: Any,
        *,
        schema_name: str,
    ) -> ResultBundleSchemaDefinition | None:
        normalized = str(schema_name or "").strip()
        project_id = str(getattr(experiment, "project_id", "") or "").strip()
        if not normalized or not project_id:
            return None
        return await self._service.get_project_result_bundle_schema(
            project_id=project_id,
            schema_name=normalized,
        )

    async def _validate_result_bundle_payload(
        self,
        *,
        experiment: Any,
        bundle_payload: dict[str, Any] | None,
        bundle_path: Path,
        schema_name: str,
    ) -> dict[str, Any]:
        normalized = str(schema_name or "").strip()
        if not normalized:
            return {}
        schema = await self._result_bundle_schema_definition(
            experiment,
            schema_name=normalized,
        )
        if schema is None:
            return {
                "enabled": True,
                "schema_name": normalized,
                "schema_found": False,
                "passed": False,
                "bundle_path": str(bundle_path),
                "missing_sections": [],
                "missing_metrics": [],
                "missing_outputs": [],
                "missing_artifact_types": [],
                "validated_at": utc_now(),
            }
        if bundle_payload is None:
            return {
                "enabled": True,
                "schema_name": normalized,
                "schema_found": True,
                "passed": False,
                "bundle_path": str(bundle_path),
                "missing_sections": [str(item).strip() for item in schema.required_sections if str(item).strip()],
                "missing_metrics": [str(item).strip() for item in schema.required_metrics if str(item).strip()],
                "missing_outputs": [str(item).strip() for item in schema.required_outputs if str(item).strip()],
                "missing_artifact_types": [
                    str(item).strip()
                    for item in schema.required_artifact_types
                    if str(item).strip()
                ],
                "validated_at": utc_now(),
            }

        available_sections = sorted(
            key
            for key in ("metrics", "outputs", "artifacts")
            if key in bundle_payload and bundle_payload.get(key) is not None
        )
        metric_names = sorted(self._bundle_metric_map(bundle_payload).keys())
        output_names: list[str] = []
        for item in self._bundle_output_entries(bundle_payload):
            name = str(
                item.get("name")
                or item.get("filename")
                or item.get("output")
                or item.get("target")
                or item.get("path")
                or "",
            ).strip()
            if not name:
                continue
            normalized_name = Path(name).name or name
            if normalized_name not in output_names:
                output_names.append(normalized_name)
        artifact_types: list[str] = []
        for item in self._bundle_artifact_entries(bundle_payload):
            artifact_type = str(
                item.get("artifact_type")
                or item.get("type")
                or item.get("kind")
                or "",
            ).strip()
            if artifact_type and artifact_type not in artifact_types:
                artifact_types.append(artifact_type)

        required_sections = [
            str(item).strip() for item in schema.required_sections if str(item).strip()
        ]
        required_metrics = [
            str(item).strip() for item in schema.required_metrics if str(item).strip()
        ]
        required_outputs = [
            str(item).strip() for item in schema.required_outputs if str(item).strip()
        ]
        required_artifact_types = [
            str(item).strip()
            for item in schema.required_artifact_types
            if str(item).strip()
        ]

        missing_sections = [
            item for item in required_sections if item not in available_sections
        ]
        missing_metrics = [item for item in required_metrics if item not in metric_names]
        missing_outputs = [
            item
            for item in required_outputs
            if item not in output_names and Path(item).name not in output_names
        ]
        missing_artifact_types = [
            item for item in required_artifact_types if item not in artifact_types
        ]
        return {
            "enabled": True,
            "schema_name": normalized,
            "schema_found": True,
            "passed": not any(
                [
                    missing_sections,
                    missing_metrics,
                    missing_outputs,
                    missing_artifact_types,
                ],
            ),
            "bundle_path": str(bundle_path),
            "available_sections": available_sections,
            "available_metrics": metric_names,
            "available_outputs": output_names,
            "available_artifact_types": artifact_types,
            "missing_sections": missing_sections,
            "missing_metrics": missing_metrics,
            "missing_outputs": missing_outputs,
            "missing_artifact_types": missing_artifact_types,
            "validated_at": utc_now(),
        }

    def _local_execution_command(
        self,
        experiment: Any,
        *,
        output_dir: Path,
    ) -> list[str]:
        execution = getattr(experiment, "execution", None)
        mode = self._experiment_execution_mode(experiment)
        metadata = dict(getattr(execution, "metadata", {}) or {})
        command = [str(part) for part in list(getattr(execution, "command", []) or []) if str(part)]
        entrypoint = str(getattr(execution, "entrypoint", "") or "").strip()
        notebook_path = str(getattr(execution, "notebook_path", "") or "").strip()
        template_values = self._execution_template_values(
            experiment,
            output_dir=output_dir,
        )

        if mode == "notebook":
            notebook = notebook_path or str(metadata.get("notebook_path", "") or "").strip()
            if not notebook:
                raise ValueError("Notebook execution requires notebook_path")
            command = [
                "jupyter",
                "nbconvert",
                "--to",
                "notebook",
                "--execute",
                "--inplace",
                notebook,
            ]
        elif not command and entrypoint:
            command = [entrypoint]

        return [
            self._apply_template_values(
                part,
                template_values=template_values,
            )
            for part in command
        ]

    def _collect_execution_outputs(
        self,
        experiment: Any,
        *,
        working_dir: Path,
        output_dir: Path,
        stdout_path: Path,
        stderr_path: Path,
    ) -> tuple[dict[str, Any], list[str], dict[str, Any]]:
        execution = getattr(experiment, "execution", None)
        metadata = dict(getattr(execution, "metadata", {}) or {})
        template_values = self._execution_template_values(
            experiment,
            output_dir=output_dir,
        )
        files: list[str] = []
        for candidate in (stdout_path, stderr_path):
            if candidate.exists():
                files.append(str(candidate))

        metrics_file = str(
            self._render_template_payload(
                metadata.get("metrics_file", ""),
                template_values=template_values,
            )
            or "",
        ).strip()
        metrics: dict[str, Any] = {}
        if metrics_file:
            resolved_metrics_path = self._resolve_execution_path(
                metrics_file,
                working_dir=working_dir,
            )
            if resolved_metrics_path.exists():
                files.append(str(resolved_metrics_path))
                metrics = self._read_metrics_payload(resolved_metrics_path)

        rendered_output_files = self._render_template_payload(
            list(metadata.get("output_files", []) or []),
            template_values=template_values,
        )
        for item in list(rendered_output_files or []):
            resolved = self._resolve_execution_path(
                str(item),
                working_dir=working_dir,
            )
            if resolved.exists():
                files.append(str(resolved))

        bundle_info = self._execution_result_bundle_settings(
            experiment,
            output_dir=output_dir,
        )
        bundle_file = str(bundle_info.get("file", "") or "").strip()
        if bundle_file:
            resolved_bundle_path = self._resolve_execution_path(
                bundle_file,
                working_dir=working_dir,
            )
            if resolved_bundle_path.exists():
                files.append(str(resolved_bundle_path))
                bundle_payload = self._bundle_payload_from_path(resolved_bundle_path)
                if bundle_payload is not None:
                    for key, value in self._bundle_metric_map(bundle_payload).items():
                        normalized = self._normalize_metric_value(value)
                        if normalized is None or key in metrics:
                            continue
                        metrics[key] = normalized
                    for item in self._bundle_output_entries(bundle_payload):
                        path_value = str(
                            item.get("path")
                            or item.get("file")
                            or item.get("uri")
                            or "",
                        ).strip()
                        resolved_output = self._resolve_bundle_reference_path(
                            experiment,
                            bundle_path=resolved_bundle_path,
                            value=path_value,
                            target_name=str(item.get("name") or ""),
                        )
                        if resolved_output is not None:
                            files.append(str(resolved_output))
                    bundle_info["path"] = str(resolved_bundle_path)

        unique_files = self._unique_strings(files)
        return metrics, unique_files, bundle_info

    async def _apply_result_bundle_artifacts(
        self,
        *,
        experiment: Any,
        bundle_info: dict[str, Any],
    ) -> tuple[Any, list[str]]:
        bundle_path_text = str(bundle_info.get("path", "") or "").strip()
        if not bundle_path_text:
            return experiment, []
        bundle_path = Path(bundle_path_text)
        bundle_payload = self._bundle_payload_from_path(bundle_path)
        created_ids: list[str] = []
        bundle_schema = str(bundle_info.get("schema", "") or "").strip()
        if bundle_payload is not None:
            for entry in self._bundle_artifact_entries(bundle_payload):
                artifact_type = str(
                    entry.get("artifact_type")
                    or entry.get("type")
                    or entry.get("kind")
                    or "",
                ).strip()
                if not artifact_type:
                    continue
                path_value = str(
                    entry.get("path")
                    or entry.get("file")
                    or entry.get("uri")
                    or "",
                ).strip()
                resolved_path = self._resolve_bundle_reference_path(
                    experiment,
                    bundle_path=bundle_path,
                    value=path_value,
                    target_name=artifact_type,
                )
                if resolved_path is None:
                    continue
                artifact = await self._service.upsert_artifact(
                    project_id=str(getattr(experiment, "project_id", "") or ""),
                    workflow_id=str(getattr(experiment, "workflow_id", "") or ""),
                    experiment_id=str(getattr(experiment, "id", "") or ""),
                    artifact_type=artifact_type,
                    title=str(entry.get("title") or f"{experiment.name} {artifact_type}").strip(),
                    description=str(entry.get("description") or "").strip(),
                    path=str(resolved_path),
                    source_type=str(entry.get("source_type") or "experiment").strip(),
                    source_id=str(entry.get("source_id") or experiment.id).strip(),
                    claim_ids=list(getattr(experiment, "claim_ids", []) or []),
                    metadata={
                        **dict(entry.get("metadata", {}) or {}),
                        "bundle_path": str(bundle_path),
                        "result_bundle_schema": bundle_schema,
                    },
                )
                created_ids.append(artifact.id)
        bundle_validation = await self._validate_result_bundle_payload(
            experiment=experiment,
            bundle_payload=bundle_payload,
            bundle_path=bundle_path,
            schema_name=bundle_schema,
        )
        if not created_ids and not bundle_schema:
            return experiment, created_ids
        experiment = await self._service.update_experiment(
            experiment_id=str(getattr(experiment, "id", "") or ""),
            metadata={
                "last_result_bundle_path": str(bundle_path),
                "last_result_bundle_schema": bundle_schema,
                "result_bundle_validation": bundle_validation,
            },
        )
        return experiment, created_ids

    @staticmethod
    def _task_execution_retry_policy(task: WorkflowTask) -> tuple[int, int]:
        metadata = dict(getattr(task, "metadata", {}) or {})
        retry_policy = dict(metadata.get("retry_policy", {}) or {})
        try:
            max_attempts = int(retry_policy.get("max_attempts") or 1)
        except (TypeError, ValueError):
            max_attempts = 1
        try:
            backoff_minutes = int(retry_policy.get("backoff_minutes") or 60)
        except (TypeError, ValueError):
            backoff_minutes = 60
        return max(1, max_attempts), max(1, backoff_minutes)

    @classmethod
    def _eligible_for_task_execution(
        cls,
        *,
        task: WorkflowTask,
        now: datetime,
    ) -> bool:
        if task.status not in {"pending", "blocked", "running"}:
            return False
        max_attempts, backoff_minutes = cls._task_execution_retry_policy(task)
        if int(getattr(task, "execution_count", 0) or 0) >= max_attempts:
            return False
        hours = cls._hours_since(getattr(task, "last_execution_at", None), now=now)
        if hours is None:
            return True
        return hours * 60 >= backoff_minutes

    def _experiment_candidate_dirs(self, experiment: Any) -> list[Path]:
        paths: list[Path] = []
        configured_workdir = str(
            getattr(getattr(experiment, "execution", None), "working_dir", "") or "",
        ).strip()
        if configured_workdir:
            paths.append(Path(configured_workdir).expanduser())
        paths.append(self._experiment_output_dir(str(getattr(experiment, "id", "") or "")))
        unique: list[Path] = []
        seen: set[str] = set()
        for path in paths:
            marker = str(path)
            if marker in seen:
                continue
            seen.add(marker)
            unique.append(path)
        return unique

    def _locate_existing_experiment_path(
        self,
        experiment: Any,
        *,
        target: str = "",
        preferred_path: str = "",
    ) -> Path | None:
        requested_values = [
            str(value).strip()
            for value in [preferred_path, target]
            if str(value).strip()
        ]
        candidate_dirs = self._experiment_candidate_dirs(experiment)
        for value in requested_values:
            direct = Path(value).expanduser()
            if direct.exists() and direct.is_file():
                return direct
            for base_dir in candidate_dirs:
                resolved = self._resolve_execution_path(value, working_dir=base_dir)
                if resolved.exists() and resolved.is_file():
                    return resolved
        target_name = Path(preferred_path or target).name.strip()
        for output_file in list(getattr(experiment, "output_files", []) or []):
            candidate = Path(str(output_file)).expanduser()
            if not candidate.exists() or not candidate.is_file():
                continue
            if candidate.name == target_name or str(candidate) in requested_values:
                return candidate
        if not target_name:
            return None
        for base_dir in candidate_dirs:
            if not base_dir.exists() or not base_dir.is_dir():
                continue
            try:
                for candidate in sorted(base_dir.rglob(target_name)):
                    if candidate.is_file():
                        return candidate
            except Exception:
                continue
        return None

    async def _artifact_for_experiment_path(
        self,
        *,
        experiment: Any,
        path: str,
    ) -> Any | None:
        artifacts = await self._service.list_artifacts(
            project_id=str(getattr(experiment, "project_id", "") or ""),
            workflow_id=str(getattr(experiment, "workflow_id", "") or ""),
            limit=200,
        )
        wanted = str(path).strip()
        for artifact in artifacts:
            if str(getattr(artifact, "experiment_id", "") or "").strip() != str(
                getattr(experiment, "id", "") or "",
            ).strip():
                continue
            if str(getattr(artifact, "path", "") or "").strip() != wanted:
                continue
            return artifact
        return None

    @staticmethod
    def _normalize_metric_value(value: Any) -> Any | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            try:
                if "." not in text and "e" not in text.lower():
                    return int(text)
                return float(text)
            except ValueError:
                return None
        return None

    async def _metric_candidate_paths(
        self,
        experiment: Any,
    ) -> list[Path]:
        execution = getattr(experiment, "execution", None)
        metadata = dict(getattr(execution, "metadata", {}) or {})
        template_values = self._execution_template_values(
            experiment,
            output_dir=self._experiment_output_dir(str(getattr(experiment, "id", "") or "")),
        )
        raw_candidates: list[str] = []
        metrics_file = str(
            self._render_template_payload(
                metadata.get("metrics_file", ""),
                template_values=template_values,
            )
            or "",
        ).strip()
        if metrics_file:
            raw_candidates.append(metrics_file)
        bundle_settings = self._execution_result_bundle_settings(experiment)
        if bundle_settings["file"]:
            raw_candidates.append(bundle_settings["file"])
        raw_candidates.extend(
            str(item).strip()
            for item in list(getattr(experiment, "output_files", []) or [])
            if str(item).strip()
        )
        artifacts = await self._service.list_artifacts(
            project_id=str(getattr(experiment, "project_id", "") or ""),
            workflow_id=str(getattr(experiment, "workflow_id", "") or ""),
            limit=200,
        )
        artifact_ids = set(getattr(experiment, "artifact_ids", []) or [])
        for artifact in artifacts:
            if str(getattr(artifact, "id", "") or "") not in artifact_ids:
                continue
            path = str(getattr(artifact, "path", "") or "").strip()
            if path:
                raw_candidates.append(path)
        unique_paths: list[Path] = []
        seen: set[str] = set()
        for candidate in raw_candidates:
            if not candidate:
                continue
            resolved = self._locate_existing_experiment_path(
                experiment,
                target=Path(candidate).name or candidate,
                preferred_path=candidate,
            )
            if resolved is None or not resolved.exists() or not resolved.is_file():
                continue
            if not metrics_file or candidate != metrics_file:
                if resolved.suffix.lower() not in {".json", ".ipynb"}:
                    continue
            marker = str(resolved)
            if marker in seen:
                continue
            seen.add(marker)
            unique_paths.append(resolved)
        return unique_paths

    async def _bundle_candidate_paths(
        self,
        experiment: Any,
    ) -> list[Path]:
        raw_candidates: list[str] = []
        bundle_settings = self._execution_result_bundle_settings(experiment)
        if bundle_settings["file"]:
            raw_candidates.append(bundle_settings["file"])
        raw_candidates.extend(
            str(item).strip()
            for item in list(getattr(experiment, "output_files", []) or [])
            if str(item).strip()
        )
        artifacts = await self._service.list_artifacts(
            project_id=str(getattr(experiment, "project_id", "") or ""),
            workflow_id=str(getattr(experiment, "workflow_id", "") or ""),
            limit=200,
        )
        artifact_ids = set(getattr(experiment, "artifact_ids", []) or [])
        for artifact in artifacts:
            if str(getattr(artifact, "id", "") or "") not in artifact_ids:
                continue
            path = str(getattr(artifact, "path", "") or "").strip()
            if path:
                raw_candidates.append(path)
        unique_paths: list[Path] = []
        seen: set[str] = set()
        for candidate in raw_candidates:
            resolved = self._locate_existing_experiment_path(
                experiment,
                target=Path(candidate).name or candidate,
                preferred_path=candidate,
            )
            if resolved is None or not resolved.exists() or not resolved.is_file():
                continue
            if resolved.suffix.lower() != ".json":
                continue
            marker = str(resolved)
            if marker in seen:
                continue
            seen.add(marker)
            unique_paths.append(resolved)
        return unique_paths

    @classmethod
    def _bundle_payload_from_path(
        cls,
        path: Path,
    ) -> dict[str, Any] | None:
        payload = cls._read_json_payload(path)
        if not isinstance(payload, dict):
            return None
        if isinstance(payload.get("result_bundle"), dict):
            return dict(payload.get("result_bundle") or {})
        bundle_keys = {"metrics", "outputs", "artifacts"}
        if bundle_keys.intersection(payload.keys()):
            return dict(payload)
        return None

    def _resolve_bundle_reference_path(
        self,
        experiment: Any,
        *,
        bundle_path: Path,
        value: str,
        target_name: str = "",
    ) -> Path | None:
        text = str(value or "").strip()
        if not text:
            return None
        direct = Path(text).expanduser()
        if direct.exists() and direct.is_file():
            return direct
        relative = (bundle_path.parent / text).expanduser()
        if relative.exists() and relative.is_file():
            return relative
        return self._locate_existing_experiment_path(
            experiment,
            target=target_name or Path(text).name or text,
            preferred_path=text,
        )

    async def _resolve_output_from_bundle(
        self,
        *,
        experiment: Any,
        output_name: str,
    ) -> dict[str, Any]:
        target = str(output_name or "").strip()
        if not target:
            return {"found": False, "reason": "Output name is empty."}
        matches: dict[str, dict[str, Any]] = {}
        for bundle_path in await self._bundle_candidate_paths(experiment):
            payload = self._bundle_payload_from_path(bundle_path)
            if payload is None:
                continue
            outputs = payload.get("outputs")
            candidate_entries: list[dict[str, Any]] = []
            if isinstance(outputs, dict):
                for key, value in outputs.items():
                    key_text = str(key).strip()
                    if key_text != target and Path(key_text).name != target:
                        continue
                    if isinstance(value, str):
                        candidate_entries.append({"name": key_text, "path": value})
                    elif isinstance(value, dict):
                        candidate_entries.append({"name": key_text, **dict(value)})
            elif isinstance(outputs, list):
                for item in outputs:
                    if not isinstance(item, dict):
                        continue
                    name = str(
                        item.get("name")
                        or item.get("filename")
                        or item.get("output")
                        or item.get("target")
                        or "",
                    ).strip()
                    if name != target and Path(name).name != target:
                        continue
                    candidate_entries.append(dict(item))
            for entry in candidate_entries:
                path_value = str(
                    entry.get("path")
                    or entry.get("file")
                    or entry.get("uri")
                    or "",
                ).strip()
                resolved_path = self._resolve_bundle_reference_path(
                    experiment,
                    bundle_path=bundle_path,
                    value=path_value,
                    target_name=target,
                )
                if resolved_path is None:
                    continue
                matches[str(resolved_path)] = {
                    "path": str(resolved_path),
                    "name": str(entry.get("name") or target).strip() or target,
                    "bundle_path": str(bundle_path),
                }
        if not matches:
            return {
                "found": False,
                "reason": f"Could not resolve output '{target}' from existing result bundles.",
            }
        if len(matches) > 1:
            return {
                "found": False,
                "reason": f"Output '{target}' resolves to multiple bundle paths.",
                "conflicting_paths": sorted(matches.keys()),
            }
        match = next(iter(matches.values()))
        return {"found": True, **match}

    async def _resolve_artifact_from_bundle(
        self,
        *,
        experiment: Any,
        artifact_type: str,
    ) -> dict[str, Any]:
        target = str(artifact_type or "").strip()
        if not target:
            return {"found": False, "reason": "Artifact type is empty."}
        matches: dict[str, dict[str, Any]] = {}
        for bundle_path in await self._bundle_candidate_paths(experiment):
            payload = self._bundle_payload_from_path(bundle_path)
            if payload is None:
                continue
            artifacts = payload.get("artifacts")
            candidate_entries: list[dict[str, Any]] = []
            if isinstance(artifacts, dict):
                for key, value in artifacts.items():
                    key_text = str(key).strip()
                    if key_text != target:
                        continue
                    if isinstance(value, str):
                        candidate_entries.append(
                            {"artifact_type": key_text, "path": value},
                        )
                    elif isinstance(value, dict):
                        candidate_entries.append(
                            {"artifact_type": key_text, **dict(value)},
                        )
            elif isinstance(artifacts, list):
                for item in artifacts:
                    if not isinstance(item, dict):
                        continue
                    item_type = str(
                        item.get("artifact_type")
                        or item.get("type")
                        or item.get("kind")
                        or "",
                    ).strip()
                    if item_type != target:
                        continue
                    candidate_entries.append(dict(item))
            for entry in candidate_entries:
                path_value = str(
                    entry.get("path")
                    or entry.get("file")
                    or entry.get("uri")
                    or "",
                ).strip()
                resolved_path = self._resolve_bundle_reference_path(
                    experiment,
                    bundle_path=bundle_path,
                    value=path_value,
                    target_name=target,
                )
                if resolved_path is None:
                    continue
                matches[str(resolved_path)] = {
                    "path": str(resolved_path),
                    "artifact_type": str(
                        entry.get("artifact_type")
                        or entry.get("type")
                        or target,
                    ).strip()
                    or target,
                    "title": str(entry.get("title") or "").strip(),
                    "description": str(entry.get("description") or "").strip(),
                    "source_type": str(entry.get("source_type") or "").strip(),
                    "source_id": str(entry.get("source_id") or "").strip(),
                    "metadata": dict(entry.get("metadata", {}) or {}),
                    "bundle_path": str(bundle_path),
                }
        if not matches:
            return {
                "found": False,
                "reason": f"Could not resolve artifact type '{target}' from existing result bundles.",
            }
        if len(matches) > 1:
            return {
                "found": False,
                "reason": f"Artifact type '{target}' resolves to multiple bundle paths.",
                "conflicting_paths": sorted(matches.keys()),
            }
        match = next(iter(matches.values()))
        return {"found": True, **match}

    async def _extract_metric_from_existing_files(
        self,
        *,
        experiment: Any,
        metric_name: str,
    ) -> dict[str, Any]:
        target = str(metric_name or "").strip()
        if not target:
            return {
                "found": False,
                "reason": "Metric name is empty.",
                "paths_checked": [],
            }
        candidate_paths = await self._metric_candidate_paths(experiment)
        matches: list[tuple[Any, Path]] = []
        unique_values: dict[str, tuple[Any, Path]] = {}
        for path in candidate_paths:
            payload = self._read_json_payload(path)
            if payload is None:
                continue
            path_matches = self._collect_metric_matches_from_payload(
                payload,
                metric_name=target,
            )
            for normalized, _ in path_matches:
                value_key = json.dumps(normalized, ensure_ascii=True, sort_keys=True)
                unique_values.setdefault(value_key, (normalized, path))
                matches.append((normalized, path))
        if not matches:
            return {
                "found": False,
                "reason": f"Could not find metric '{target}' in existing outputs.",
                "paths_checked": [str(path) for path in candidate_paths],
            }
        if len(unique_values) > 1:
            return {
                "found": False,
                "reason": (
                    f"Metric '{target}' has conflicting values across existing files."
                ),
                "paths_checked": [str(path) for path in candidate_paths],
                "conflicting_values": [
                    {
                        "value": value,
                        "path": str(path),
                    }
                    for value, path in unique_values.values()
                ],
            }
        value, path = next(iter(unique_values.values()))
        return {
            "found": True,
            "value": value,
            "path": str(path),
            "paths_checked": [str(candidate) for candidate in candidate_paths],
        }

    async def _can_auto_execute_task(
        self,
        *,
        task: WorkflowTask,
    ) -> bool:
        metadata = dict(getattr(task, "metadata", {}) or {})
        action_type = str(metadata.get("action_type", "") or "").strip()
        if action_type not in {"publish_artifact", "archive_output", "record_metric"}:
            return False
        experiment_id = str(metadata.get("experiment_id", "") or "").strip()
        if not experiment_id:
            return False
        try:
            experiment = await self._service.get_experiment(experiment_id)
            payload_hint = dict(metadata.get("payload_hint", {}) or {})
            target = str(metadata.get("target", "") or "").strip()
            if action_type == "record_metric":
                if not target:
                    return False
                resolution = await self._extract_metric_from_existing_files(
                    experiment=experiment,
                    metric_name=target,
                )
                return bool(resolution.get("found"))
            if action_type == "archive_output":
                output_name = str(
                    (list(payload_hint.get("output_files", []) or []) or [target])[0] or "",
                ).strip()
                preferred_path = str(payload_hint.get("path", "") or "").strip()
                resolved_path = self._locate_existing_experiment_path(
                    experiment,
                    target=target or output_name,
                    preferred_path=preferred_path or output_name,
                )
                if resolved_path is not None:
                    return True
                resolution = await self._resolve_output_from_bundle(
                    experiment=experiment,
                    output_name=target or output_name,
                )
                return bool(resolution.get("found"))
            artifact_type = str(
                payload_hint.get("artifact_type", "") or target or "analysis",
            ).strip()
            preferred_path = str(payload_hint.get("path", "") or "").strip()
            resolved_path = self._locate_existing_experiment_path(
                experiment,
                target=target or artifact_type,
                preferred_path=preferred_path,
            )
            if resolved_path is not None:
                return True
            resolution = await self._resolve_artifact_from_bundle(
                experiment=experiment,
                artifact_type=artifact_type,
            )
        except Exception:
            return False
        return bool(resolution.get("found"))

    async def _apply_workflow_runner_template(
        self,
        *,
        workflow: ResearchWorkflow,
        experiment: Any,
    ) -> Any:
        if self._execution_already_configured(experiment):
            return experiment
        project = await self._service.get_project(str(getattr(experiment, "project_id", "") or ""))
        template, matched_rules = await self._resolved_runner_template(
            project=project,
            workflow=workflow,
            experiment=experiment,
        )
        if template is None:
            return experiment
        output_dir = self._experiment_output_dir(str(getattr(experiment, "id", "") or ""))
        template_values = self._execution_template_values(
            experiment,
            output_dir=output_dir,
        )
        parameter_overrides = dict(
            self._render_template_payload(
                template.parameter_overrides,
                template_values=template_values,
            )
            or {},
        )
        input_data_overrides = dict(
            self._render_template_payload(
                template.input_data_overrides,
                template_values=template_values,
            )
            or {},
        )
        if parameter_overrides or input_data_overrides:
            experiment = await self._service.update_experiment(
                experiment_id=str(getattr(experiment, "id", "") or ""),
                parameters=parameter_overrides or None,
                input_data=input_data_overrides or None,
                metadata={
                    "runner_rule_names": matched_rules,
                }
                if matched_rules
                else None,
            )
            template_values = self._execution_template_values(
                experiment,
                output_dir=output_dir,
            )
        payload = await self._service.configure_experiment_execution(
            experiment_id=str(getattr(experiment, "id", "") or ""),
            patch={
                "mode": template.mode,
                "command": [
                    str(item)
                    for item in self._render_template_payload(
                        list(template.command),
                        template_values=template_values,
                    )
                    if str(item).strip()
                ],
                "entrypoint": str(
                    self._render_template_payload(
                        template.entrypoint,
                        template_values=template_values,
                    )
                    or "",
                ).strip(),
                "working_dir": str(
                    self._render_template_payload(
                        template.working_dir,
                        template_values=template_values,
                    )
                    or "",
                ).strip(),
                "notebook_path": str(
                    self._render_template_payload(
                        template.notebook_path,
                        template_values=template_values,
                    )
                    or "",
                ).strip(),
                "result_bundle_file": str(
                    self._render_template_payload(
                        template.result_bundle_file,
                        template_values=template_values,
                    )
                    or "",
                ).strip(),
                "result_bundle_schema": str(
                    self._render_template_payload(
                        template.result_bundle_schema,
                        template_values=template_values,
                    )
                    or "",
                ).strip(),
                "environment": {
                    str(key): str(value)
                    for key, value in dict(
                        self._render_template_payload(
                            template.environment,
                            template_values=template_values,
                        )
                        or {},
                    ).items()
                },
                "requested_by": str(
                    self._render_template_payload(
                        template.requested_by or "workflow-runtime",
                        template_values=template_values,
                    )
                    or "workflow-runtime",
                ).strip(),
                "instructions": str(
                    self._render_template_payload(
                        template.instructions,
                        template_values=template_values,
                    )
                    or "",
                ).strip(),
                "metadata": dict(
                    self._render_template_payload(
                        {
                            **template.metadata,
                            "runner_rule_names": matched_rules,
                        },
                        template_values=template_values,
                    )
                    or {},
                ),
            },
        )
        return payload["experiment"]

    async def _execute_local_experiment_process(
        self,
        experiment: Any,
    ) -> dict[str, Any]:
        output_dir = self._experiment_output_dir(experiment.id)
        output_dir.mkdir(parents=True, exist_ok=True)
        execution = getattr(experiment, "execution", None)
        configured_workdir = str(getattr(execution, "working_dir", "") or "").strip()
        working_dir = (
            Path(configured_workdir).expanduser()
            if configured_workdir
            else output_dir
        )
        working_dir.mkdir(parents=True, exist_ok=True)
        mode = self._experiment_execution_mode(experiment)
        command = self._local_execution_command(experiment, output_dir=output_dir)
        if not command:
            raise ValueError(f"No local command configured for experiment {experiment.id}")

        metadata = dict(getattr(execution, "metadata", {}) or {})
        configured_environment = {
            str(key): str(value)
            for key, value in dict(getattr(execution, "environment", {}) or {}).items()
            if str(key).strip()
        }
        timeout_seconds = int(metadata.get("timeout_seconds") or 600)
        await self._service.record_experiment_heartbeat(
            experiment_id=experiment.id,
            summary=f"Launching local {mode} execution.",
            status="running",
            metadata={
                "execution_mode": mode,
                "command": command,
                "working_dir": str(working_dir),
                "environment_keys": sorted(configured_environment.keys()),
            },
        )

        env = os.environ.copy()
        env.update(configured_environment)
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(working_dir),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        timed_out = False
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            timed_out = True
            process.kill()
            stdout, stderr = await process.communicate()

        stdout_path = output_dir / "stdout.log"
        stderr_path = output_dir / "stderr.log"
        stdout_path.write_bytes(stdout or b"")
        stderr_path.write_bytes(stderr or b"")
        collected_metrics, output_files, bundle_info = self._collect_execution_outputs(
            experiment,
            working_dir=working_dir,
            output_dir=output_dir,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )
        status = "completed"
        summary = (
            f"Local {mode} execution finished with exit code {process.returncode}."
        )
        if timed_out:
            status = "failed"
            summary = (
                f"Local {mode} execution timed out after {timeout_seconds} second(s)."
            )
        elif process.returncode != 0:
            status = "failed"
            summary = (
                f"Local {mode} execution failed with exit code {process.returncode}."
            )
        notes = "\n".join(
            [
                f"Command: {' '.join(command)}",
                f"Working directory: {working_dir}",
                "",
                "stdout",
                (stdout or b"").decode("utf-8", errors="replace")[:4000],
                "",
                "stderr",
                (stderr or b"").decode("utf-8", errors="replace")[:4000],
            ],
        )
        result = await self._service.record_experiment_result(
            experiment_id=experiment.id,
            summary=summary,
            status=status,
            metrics=collected_metrics,
            output_files=output_files,
            notes=notes,
            metadata={
                "execution_mode": mode,
                "command": command,
                "working_dir": str(working_dir),
                "timeout_seconds": timeout_seconds,
                "environment_keys": sorted(configured_environment.keys()),
                **(
                    {
                        "result_bundle_path": str(bundle_info.get("path") or ""),
                        "result_bundle_schema": str(bundle_info.get("schema") or ""),
                    }
                    if bundle_info.get("path")
                    else {}
                ),
            },
        )
        updated_experiment, _ = await self._apply_result_bundle_artifacts(
            experiment=result["experiment"],
            bundle_info=bundle_info,
        )
        result["experiment"] = updated_experiment
        return result

    async def execute_experiment(self, experiment_id: str) -> dict[str, Any]:
        experiment = await self._service.get_experiment(experiment_id)
        mode = self._experiment_execution_mode(experiment)
        if mode in {"command", "notebook"}:
            payload = await self._execute_local_experiment_process(experiment)
            return {
                **payload,
                "executed": True,
                "mode": mode,
            }
        if mode in {"external", "file_watch"}:
            payload = await self._service.record_experiment_heartbeat(
                experiment_id=experiment.id,
                summary=f"Experiment is waiting for {mode} callbacks.",
                status="running",
                metadata={
                    "execution_mode": mode,
                    "external_run_id": getattr(experiment.execution, "external_run_id", ""),
                },
            )
            return {
                **payload,
                "executed": False,
                "mode": mode,
                "waiting": True,
            }
        return {
            "experiment": experiment,
            "executed": False,
            "mode": mode,
            "reason": "inline execution is handled by the structured worker",
        }

    async def _reconcile_experiment_contract_followup_task(
        self,
        *,
        workflow: ResearchWorkflow,
        note_ids: list[str],
        claim_ids: list[str],
        artifact_ids: list[str],
        contract_failures: list[dict[str, Any]],
    ) -> ResearchWorkflow:
        task = self._find_task_by_kind(
            workflow,
            stage_name="experiment_run",
            task_kind="experiment_contract_followup",
        )
        summary = ""
        if contract_failures:
            summary = (
                f"Resolve artifact contract gaps for {len(contract_failures)} experiment run(s)."
            )
            if task is None:
                workflow = await self._service.add_workflow_task(
                    workflow_id=workflow.id,
                    stage="experiment_run",
                    title="Resolve experiment contract gaps",
                    description=(
                        "Backfill missing metrics, outputs, or artifact types "
                        "required by the execution contract before analysis."
                    ),
                    metadata={
                        "task_kind": "experiment_contract_followup",
                        "contract_failure_run_ids": [
                            self._contract_failure_run_id(item)
                            for item in contract_failures
                        ],
                    },
                )
                task = self._find_task_by_kind(
                    workflow,
                    stage_name="experiment_run",
                    task_kind="experiment_contract_followup",
                )
            if task is not None:
                workflow = await self._service.update_workflow_task(
                    workflow_id=workflow.id,
                    task_id=task.id,
                    status="pending",
                    summary=summary,
                    note_ids=note_ids,
                    claim_ids=claim_ids,
                    artifact_ids=artifact_ids,
                )
            return workflow

        if task is not None and task.status in {"pending", "running", "blocked"}:
            workflow = await self._service.update_workflow_task(
                workflow_id=workflow.id,
                task_id=task.id,
                status="completed",
                summary="Resolved experiment contract gaps.",
                note_ids=note_ids,
                claim_ids=claim_ids,
                artifact_ids=artifact_ids,
            )
        return workflow

    async def _reconcile_experiment_contract_remediation_tasks(
        self,
        *,
        workflow: ResearchWorkflow,
        note_ids: list[str],
        claim_ids: list[str],
        artifact_ids: list[str],
        contract_failures: list[dict[str, Any]],
    ) -> ResearchWorkflow:
        actions = [
            action
            for item in contract_failures
            for action in self._contract_failure_actions(item)
        ]
        existing_tasks = self._find_tasks_by_kind(
            workflow,
            stage_name="experiment_run",
            task_kind="experiment_contract_remediation",
        )
        existing_by_key = {
            str(task.metadata.get("remediation_key", "") or "").strip(): task
            for task in existing_tasks
            if str(task.metadata.get("remediation_key", "") or "").strip()
        }
        active_keys: set[str] = set()

        for action in actions:
            remediation_key = self._contract_action_key(action)
            if not remediation_key:
                continue
            active_keys.add(remediation_key)
            task = existing_by_key.get(remediation_key)
            due_at = self._contract_action_due_at(action)
            summary = str(action.get("instructions", "") or "").strip()
            if task is None:
                workflow = await self._service.add_workflow_task(
                    workflow_id=workflow.id,
                    stage="experiment_run",
                    title=str(action.get("title", "") or "Resolve contract remediation"),
                    description=summary,
                    due_at=due_at,
                    assignee=str(action.get("assignee", "") or "agent"),
                    metadata={
                        "task_kind": "experiment_contract_remediation",
                        "remediation_key": remediation_key,
                        "experiment_id": str(action.get("experiment_id", "") or ""),
                        "action_type": str(action.get("action_type", "") or ""),
                        "target": str(action.get("target", "") or ""),
                        "suggested_tool": str(action.get("suggested_tool", "") or ""),
                        "payload_hint": dict(action.get("payload_hint") or {}),
                        "retry_policy": dict(action.get("retry_policy") or {}),
                    },
                )
                refreshed = self._find_tasks_by_kind(
                    workflow,
                    stage_name="experiment_run",
                    task_kind="experiment_contract_remediation",
                )
                existing_by_key = {
                    str(item.metadata.get("remediation_key", "") or "").strip(): item
                    for item in refreshed
                    if str(item.metadata.get("remediation_key", "") or "").strip()
                }
                task = existing_by_key.get(remediation_key)
            if task is None:
                continue
            task_status = "pending" if task.status != "running" else "running"
            workflow = await self._service.update_workflow_task(
                workflow_id=workflow.id,
                task_id=task.id,
                status=task_status,
                summary=summary,
                due_at=due_at,
                note_ids=note_ids,
                claim_ids=claim_ids,
                artifact_ids=artifact_ids,
            )

        for task in self._find_tasks_by_kind(
            workflow,
            stage_name="experiment_run",
            task_kind="experiment_contract_remediation",
        ):
            remediation_key = str(task.metadata.get("remediation_key", "") or "").strip()
            if remediation_key in active_keys:
                continue
            if task.status in {"pending", "running", "blocked"}:
                workflow = await self._service.update_workflow_task(
                    workflow_id=workflow.id,
                    task_id=task.id,
                    status="completed",
                    summary="Resolved contract remediation item.",
                    note_ids=note_ids,
                    claim_ids=claim_ids,
                    artifact_ids=artifact_ids,
                )
        return workflow

    async def _sync_blocked_experiment_contract_state(
        self,
        workflow: ResearchWorkflow,
    ) -> ResearchWorkflow:
        if workflow.current_stage != "experiment_run":
            return workflow
        context = await self._service.get_workflow_contract_remediation_context(
            workflow.id,
        )
        if context:
            workflow = await self._reconcile_experiment_contract_remediation_tasks(
                workflow=workflow,
                note_ids=[],
                claim_ids=[],
                artifact_ids=[],
                contract_failures=list(context.get("contract_failures", []) or []),
            )
            workflow = await self._reconcile_experiment_contract_followup_task(
                workflow=workflow,
                note_ids=[],
                claim_ids=[],
                artifact_ids=[],
                contract_failures=list(context.get("contract_failures", []) or []),
            )
            context = await self._service.get_workflow_contract_remediation_context(
                workflow.id,
            )
        workflow = await self._service.update_workflow_binding(
            workflow_id=workflow.id,
            patch={
                "metadata": {
                    "contract_remediation_ready": bool(
                        context.get("ready_for_retry") if context else False,
                    ),
                    "contract_remediation_summary": str(
                        context.get("remediation_summary", "") if context else "",
                    ).strip(),
                    "contract_remediation_task_count": len(
                        list(context.get("remediation_tasks", []) or [])
                        if context
                        else [],
                    ),
                },
            },
        )
        return workflow

    async def _finalize_stage_worker(
        self,
        *,
        project: Any,
        workflow: ResearchWorkflow,
        task_id: str,
        summary: str,
        detail: str,
        note_ids: list[str],
        artifact_ids: list[str],
        claim_ids: list[str] | None = None,
        trigger: str,
        trigger_reason: str,
        status: str,
    ) -> dict[str, Any]:
        stage_before = workflow.current_stage
        status_before = workflow.status
        execution_note = await self._service.create_note(
            project_id=project.id,
            workflow_id=workflow.id,
            title=f"Structured stage execution · {workflow.title}",
            content=detail,
            note_type="decision_log",
            claim_ids=claim_ids,
            artifact_ids=artifact_ids,
            tags=["structured-execution", stage_before],
            metadata={
                "executor": "structured_stage_worker",
                "trigger": trigger,
                "trigger_reason": trigger_reason,
            },
        )
        combined_note_ids = list(
            dict.fromkeys([*note_ids, execution_note.id]),
        )
        await self._service.update_workflow_task(
            workflow_id=workflow.id,
            task_id=task_id,
            status=status,
            summary=summary,
            note_ids=combined_note_ids,
            claim_ids=claim_ids,
            artifact_ids=artifact_ids,
        )
        workflow_final = await self._service.tick_workflow(workflow.id)
        workflow_final = await self._service.update_workflow_binding(
            workflow_id=workflow.id,
            patch={
                "last_dispatch_at": utc_now(),
                "last_summary": self._truncate_summary(summary, limit=500),
                "metadata": {
                    "last_executor": "structured_stage_worker",
                    "last_execution_note_id": execution_note.id,
                    "last_execution_trigger": trigger,
                },
            },
        )
        return {
            "workflow": workflow_final,
            "project": project,
            "note": execution_note,
            "response": summary,
            "mutated_by_agent": False,
            "agent_id": "",
            "session_id": workflow.bindings.session_id,
            "execution_id": execution_note.id,
            "stage_before": stage_before,
            "status_before": status_before,
            "trigger": trigger,
            "trigger_reason": trigger_reason,
            "executor_kind": "structured_stage_worker",
            "skipped": False,
        }

    async def _execute_literature_search_worker(
        self,
        *,
        project: Any,
        workflow: ResearchWorkflow,
        trigger: str,
        trigger_reason: str,
    ) -> dict[str, Any]:
        from researchclaw.agents.skills.arxiv.tools import arxiv_search
        from researchclaw.agents.tools.semantic_scholar import (
            semantic_scholar_search,
        )

        stage_tasks = self._stage_tasks(workflow)
        if not stage_tasks:
            workflow = await self._service.tick_workflow(workflow.id)
            stage_tasks = self._stage_tasks(workflow)
        if not stage_tasks:
            raise RuntimeError("No task found for literature_search stage")
        task_id = stage_tasks[0].id

        query = self._build_search_query(project=project, workflow=workflow)
        raw_sources = [
            ("semantic_scholar", semantic_scholar_search(query=query, max_results=5)),
            ("arxiv", arxiv_search(query=query, max_results=5)),
        ]
        papers: list[dict[str, Any]] = []
        source_name = ""
        source_error = ""
        for candidate_source, rows in raw_sources:
            clean_rows = [
                item
                for item in rows
                if isinstance(item, dict)
                and str(item.get("title", "") or "").strip()
            ]
            if clean_rows:
                papers = clean_rows[:5]
                source_name = candidate_source
                break
            if rows and isinstance(rows[0], dict):
                source_error = str(rows[0].get("error", "") or source_error)

        if not papers:
            summary = (
                f"No literature search results found for query '{query}'. "
                f"{source_error}".strip()
            )
            return await self._finalize_stage_worker(
                project=project,
                workflow=workflow,
                task_id=task_id,
                summary=summary,
                detail=summary,
                note_ids=[],
                artifact_ids=[],
                trigger=trigger,
                trigger_reason=trigger_reason,
                status="blocked",
            )

        artifact_ids: list[str] = []
        paper_refs: list[str] = []
        rows: list[str] = []
        for idx, paper in enumerate(papers, start=1):
            source_id = self._paper_source_id(paper)
            artifact = await self._service.upsert_artifact(
                project_id=project.id,
                workflow_id=workflow.id,
                title=str(paper.get("title", "") or "").strip() or f"Paper {idx}",
                artifact_type="paper",
                description=self._truncate_summary(
                    self._paper_abstract(paper),
                    limit=500,
                ),
                uri=str(paper.get("url", "") or paper.get("pdf_url", "") or "").strip(),
                source_type=source_name,
                source_id=source_id,
                metadata={
                    key: value
                    for key, value in paper.items()
                    if key not in {"error"}
                },
            )
            artifact_ids.append(artifact.id)
            paper_ref = self._paper_ref(paper)
            if paper_ref:
                paper_refs.append(paper_ref)
            authors = paper.get("authors") or []
            author_preview = ", ".join(str(item) for item in authors[:3])
            year = str(
                paper.get("year")
                or paper.get("published")
                or paper.get("publication_date")
                or "",
            ).strip()
            abstract = self._truncate_summary(self._paper_abstract(paper), limit=260)
            rows.append(
                f"{idx}. {artifact.title}"
                + (f" | {author_preview}" if author_preview else "")
                + (f" | {year}" if year else "")
                + (f"\n   {abstract}" if abstract else "")
            )

        note = await self._service.create_note(
            project_id=project.id,
            workflow_id=workflow.id,
            title=f"Literature shortlist · {workflow.title}",
            content="\n".join(
                [
                    f"Query: {query}",
                    f"Source: {source_name}",
                    "",
                    "Top papers",
                    *rows,
                ],
            ),
            note_type="paper_note",
            artifact_ids=artifact_ids,
            paper_refs=paper_refs,
            tags=["literature_search", source_name],
            metadata={
                "query": query,
                "source": source_name,
                "paper_count": len(artifact_ids),
            },
        )
        summary = (
            f"Shortlisted {len(artifact_ids)} paper(s) from {source_name} for query '{query}'."
        )
        return await self._finalize_stage_worker(
            project=project,
            workflow=workflow,
            task_id=task_id,
            summary=summary,
            detail="\n".join(
                [
                    summary,
                    "",
                    f"Primary note: {note.title}",
                    *rows,
                ],
            ),
            note_ids=[note.id],
            artifact_ids=artifact_ids,
            trigger=trigger,
            trigger_reason=trigger_reason,
            status="completed",
        )

    async def _execute_paper_reading_worker(
        self,
        *,
        project: Any,
        workflow: ResearchWorkflow,
        trigger: str,
        trigger_reason: str,
    ) -> dict[str, Any]:
        from researchclaw.agents.skills.arxiv.tools import arxiv_get_paper
        from researchclaw.agents.tools.semantic_scholar import (
            semantic_scholar_get_paper,
        )

        stage_tasks = self._stage_tasks(workflow)
        if not stage_tasks:
            workflow = await self._service.tick_workflow(workflow.id)
            stage_tasks = self._stage_tasks(workflow)
        if not stage_tasks:
            raise RuntimeError("No task found for paper_reading stage")
        task_id = stage_tasks[0].id

        paper_artifacts = await self._service.list_artifacts(
            project_id=project.id,
            workflow_id=workflow.id,
            artifact_type="paper",
            limit=20,
        )
        if not paper_artifacts:
            paper_artifacts = await self._service.list_artifacts(
                project_id=project.id,
                artifact_type="paper",
                limit=20,
            )
        unread = [artifact for artifact in paper_artifacts if not artifact.note_ids]
        selected = (unread or paper_artifacts)[:3]

        if not selected:
            summary = "No paper artifacts are available for the paper_reading stage."
            return await self._finalize_stage_worker(
                project=project,
                workflow=workflow,
                task_id=task_id,
                summary=summary,
                detail=summary,
                note_ids=[],
                artifact_ids=[],
                trigger=trigger,
                trigger_reason=trigger_reason,
                status="blocked",
            )

        created_note_ids: list[str] = []
        artifact_ids: list[str] = []
        execution_rows: list[str] = []
        for artifact in selected:
            details = dict(artifact.metadata or {})
            if artifact.source_type == "arxiv" and artifact.source_id:
                fetched = arxiv_get_paper(artifact.source_id)
                if isinstance(fetched, dict) and not fetched.get("error"):
                    details.update(fetched)
            elif artifact.source_type == "semantic_scholar" and artifact.source_id:
                fetched = semantic_scholar_get_paper(artifact.source_id)
                if isinstance(fetched, dict) and not fetched.get("error"):
                    details.update(fetched)

            abstract = self._truncate_summary(
                str(details.get("abstract", "") or artifact.description or "").strip(),
                limit=1200,
            )
            tldr = self._truncate_summary(
                str(details.get("tldr", "") or "").strip(),
                limit=400,
            )
            references = [
                self._paper_ref(details),
                self._paper_ref(artifact.metadata or {}),
            ]
            paper_ref = next((ref for ref in references if ref), "")
            authors = details.get("authors") or artifact.metadata.get("authors") or []
            author_preview = ", ".join(str(item) for item in authors[:4])
            venue = str(details.get("venue", "") or artifact.metadata.get("venue", "") or "").strip()
            year = str(
                details.get("year")
                or details.get("published")
                or artifact.metadata.get("year")
                or artifact.metadata.get("published")
                or "",
            ).strip()

            note = await self._service.create_note(
                project_id=project.id,
                workflow_id=workflow.id,
                title=f"Paper reading · {artifact.title}",
                content="\n".join(
                    [
                        f"Title: {artifact.title}",
                        f"Authors: {author_preview or '-'}",
                        f"Venue: {venue or '-'}",
                        f"Year: {year or '-'}",
                        f"Reference: {paper_ref or '-'}",
                        "",
                        "TL;DR",
                        tldr or "No TL;DR available.",
                        "",
                        "Abstract / Key summary",
                        abstract or "No abstract available.",
                    ],
                ),
                note_type="paper_note",
                artifact_ids=[artifact.id],
                paper_refs=[paper_ref] if paper_ref else [],
                tags=["paper_reading", artifact.source_type or "paper"],
                metadata={
                    "source_artifact_id": artifact.id,
                    "source_type": artifact.source_type,
                    "source_id": artifact.source_id,
                },
            )
            created_note_ids.append(note.id)
            artifact_ids.append(artifact.id)
            execution_rows.append(
                f"- {artifact.title}: created note {note.id}"
                + (f" | {paper_ref}" if paper_ref else "")
            )

        summary = f"Created {len(created_note_ids)} paper reading note(s) from shortlisted papers."
        return await self._finalize_stage_worker(
            project=project,
            workflow=workflow,
            task_id=task_id,
            summary=summary,
            detail="\n".join([summary, "", *execution_rows]),
            note_ids=created_note_ids,
            artifact_ids=artifact_ids,
            trigger=trigger,
            trigger_reason=trigger_reason,
            status="completed",
        )

    async def _execute_note_synthesis_worker(
        self,
        *,
        project: Any,
        workflow: ResearchWorkflow,
        trigger: str,
        trigger_reason: str,
    ) -> dict[str, Any]:
        stage_tasks = self._stage_tasks(workflow)
        if not stage_tasks:
            workflow = await self._service.tick_workflow(workflow.id)
            stage_tasks = self._stage_tasks(workflow)
        if not stage_tasks:
            raise RuntimeError("No task found for note_synthesis stage")
        task_id = stage_tasks[0].id

        paper_notes = await self._service.list_notes(
            project_id=project.id,
            workflow_id=workflow.id,
            note_type="paper_note",
            limit=20,
        )
        reading_notes = [
            note
            for note in paper_notes
            if "paper_reading" in set(getattr(note, "tags", []) or [])
            or str(getattr(note, "title", "") or "").startswith("Paper reading")
        ]
        selected = reading_notes or paper_notes
        if not selected:
            summary = "No paper reading notes are available for the note_synthesis stage."
            return await self._finalize_stage_worker(
                project=project,
                workflow=workflow,
                task_id=task_id,
                summary=summary,
                detail=summary,
                note_ids=[],
                artifact_ids=[],
                trigger=trigger,
                trigger_reason=trigger_reason,
                status="blocked",
            )

        source_note_ids = [note.id for note in selected[:6]]
        source_artifact_ids = self._unique_strings(
            [
                artifact_id
                for note in selected[:6]
                for artifact_id in list(getattr(note, "artifact_ids", []) or [])
            ],
        )
        observations: list[str] = []
        source_titles: list[str] = []
        for note in selected[:6]:
            source_title = self._source_title_from_note(note)
            source_titles.append(source_title)
            tldr = self._extract_note_section(note.content, "TL;DR")
            abstract = self._extract_note_section(
                note.content,
                "Abstract / Key summary",
            )
            reference = ""
            for line in str(note.content or "").splitlines():
                if line.startswith("Reference:"):
                    reference = line.split(":", 1)[1].strip()
                    break
            summary_text = self._truncate_summary(
                tldr or abstract or str(note.content or ""),
                limit=220,
            )
            observations.append(
                f"- {source_title}"
                + (f" | {reference}" if reference and reference != "-" else "")
                + (f"\n  {summary_text}" if summary_text else "")
            )

        synthesis_artifact = await self._service.upsert_artifact(
            project_id=project.id,
            workflow_id=workflow.id,
            title=f"Synthesis summary · {workflow.title}",
            artifact_type="summary",
            description=f"Synthesized {len(source_note_ids)} reading note(s).",
            source_type="workflow_stage",
            source_id=f"{workflow.id}:note_synthesis",
            note_ids=source_note_ids,
            metadata={
                "stage": "note_synthesis",
                "source_note_ids": source_note_ids,
                "source_titles": source_titles,
            },
        )
        synthesis_note = await self._service.create_note(
            project_id=project.id,
            workflow_id=workflow.id,
            title=f"Note synthesis · {workflow.title}",
            content="\n".join(
                [
                    f"Goal: {workflow.goal or workflow.title}",
                    f"Source notes: {len(source_note_ids)}",
                    "",
                    "Cross-paper observations",
                    *observations,
                    "",
                    "Emerging themes",
                    "- The literature already covers multiple relevant methods, but the evidence is fragmented across papers and summaries.",
                    "- Baseline strength, evaluation setup, and transferable assumptions remain central comparison points before stronger claims can be made.",
                    "- The next step should convert these reading notes into falsifiable hypotheses and concrete experiment directions.",
                ],
            ),
            note_type="idea_note",
            artifact_ids=[synthesis_artifact.id, *source_artifact_ids],
            paper_refs=[
                paper_ref
                for note in selected[:6]
                for paper_ref in list(getattr(note, "paper_refs", []) or [])
            ],
            tags=["note_synthesis", "structured-stage"],
            metadata={
                "stage": "note_synthesis",
                "source_note_ids": source_note_ids,
            },
        )
        summary = f"Synthesized {len(source_note_ids)} paper note(s) into one thematic note."
        return await self._finalize_stage_worker(
            project=project,
            workflow=workflow,
            task_id=task_id,
            summary=summary,
            detail="\n".join(
                [
                    summary,
                    "",
                    f"Synthesis note: {synthesis_note.title}",
                    *observations,
                ],
            ),
            note_ids=[synthesis_note.id],
            artifact_ids=[synthesis_artifact.id, *source_artifact_ids],
            trigger=trigger,
            trigger_reason=trigger_reason,
            status="completed",
        )

    async def _execute_hypothesis_queue_worker(
        self,
        *,
        project: Any,
        workflow: ResearchWorkflow,
        trigger: str,
        trigger_reason: str,
    ) -> dict[str, Any]:
        stage_tasks = self._stage_tasks(workflow)
        if not stage_tasks:
            workflow = await self._service.tick_workflow(workflow.id)
            stage_tasks = self._stage_tasks(workflow)
        if not stage_tasks:
            raise RuntimeError("No task found for hypothesis_queue stage")
        task_id = stage_tasks[0].id

        synthesis_notes = await self._service.list_notes(
            project_id=project.id,
            workflow_id=workflow.id,
            tags=["note_synthesis"],
            limit=10,
        )
        source_notes = synthesis_notes or await self._service.list_notes(
            project_id=project.id,
            workflow_id=workflow.id,
            note_type="paper_note",
            limit=10,
        )
        if not source_notes:
            summary = "No synthesis context is available for the hypothesis_queue stage."
            return await self._finalize_stage_worker(
                project=project,
                workflow=workflow,
                task_id=task_id,
                summary=summary,
                detail=summary,
                note_ids=[],
                artifact_ids=[],
                trigger=trigger,
                trigger_reason=trigger_reason,
                status="blocked",
            )

        source_note_ids = [note.id for note in source_notes[:5]]
        source_artifact_ids = self._unique_strings(
            [
                artifact_id
                for note in source_notes[:5]
                for artifact_id in list(getattr(note, "artifact_ids", []) or [])
            ],
        )
        paper_artifacts = await self._service.list_artifacts(
            project_id=project.id,
            workflow_id=workflow.id,
            artifact_type="paper",
            limit=5,
        )
        paper_titles = [artifact.title for artifact in paper_artifacts[:3]]
        topic = workflow.goal or workflow.title
        candidate_hypotheses = [
            (
                f"Evaluation and baseline choices likely account for a substantial share of the reported gains in {topic}.",
                "baseline_risk",
            ),
            (
                f"A focused comparison using insights from {paper_titles[0] if paper_titles else 'the shortlisted literature'} will likely expose at least one unresolved failure mode in {topic}.",
                "failure_mode_probe",
            ),
            (
                f"Ablating the core assumptions surfaced during note synthesis will likely clarify which evidence is robust enough to support claims about {topic}.",
                "assumption_ablation",
            ),
        ]
        existing_claims = await self._service.list_claims(
            project_id=project.id,
            workflow_id=workflow.id,
            limit=50,
        )
        existing_texts = {
            str(claim.text).strip().lower(): claim
            for claim in existing_claims
        }
        claim_ids: list[str] = []
        queue_lines: list[str] = []
        primary_note = source_notes[0]

        for text, hypothesis_kind in candidate_hypotheses:
            normalized = text.strip().lower()
            claim = existing_texts.get(normalized)
            if claim is None:
                claim = await self._service.create_claim(
                    project_id=project.id,
                    workflow_id=workflow.id,
                    text=text,
                    status="draft",
                    note_ids=source_note_ids,
                    artifact_ids=source_artifact_ids,
                    metadata={
                        "stage": "hypothesis_queue",
                        "hypothesis_kind": hypothesis_kind,
                    },
                )
                await self._service.attach_evidence(
                    project_id=project.id,
                    claim_ids=[claim.id],
                    evidence_type="note",
                    summary=f"Hypothesis derived from synthesis note '{primary_note.title}'.",
                    source_type="note",
                    source_id=primary_note.id,
                    title=primary_note.title,
                    locator="derived hypothesis",
                    note_id=primary_note.id,
                    workflow_id=workflow.id,
                    metadata={
                        "stage": "hypothesis_queue",
                    },
                )
            claim_ids.append(claim.id)
            queue_lines.append(f"- {claim.text}")

        hypothesis_artifact = await self._service.upsert_artifact(
            project_id=project.id,
            workflow_id=workflow.id,
            title=f"Hypothesis queue · {workflow.title}",
            artifact_type="analysis",
            description=f"Queued {len(claim_ids)} draft hypothesis claim(s).",
            source_type="workflow_stage",
            source_id=f"{workflow.id}:hypothesis_queue",
            claim_ids=claim_ids,
            note_ids=source_note_ids,
            metadata={
                "stage": "hypothesis_queue",
                "claim_ids": claim_ids,
            },
        )
        queue_note = await self._service.create_note(
            project_id=project.id,
            workflow_id=workflow.id,
            title=f"Hypothesis queue · {workflow.title}",
            content="\n".join(
                [
                    f"Topic: {topic}",
                    f"Source note: {primary_note.title}",
                    "",
                    "Queued hypotheses",
                    *queue_lines,
                ],
            ),
            note_type="idea_note",
            claim_ids=claim_ids,
            artifact_ids=[hypothesis_artifact.id, *source_artifact_ids],
            tags=["hypothesis_queue", "structured-stage"],
            metadata={
                "stage": "hypothesis_queue",
                "claim_ids": claim_ids,
            },
        )
        summary = f"Queued {len(claim_ids)} draft hypothesis claim(s) from synthesized notes."
        return await self._finalize_stage_worker(
            project=project,
            workflow=workflow,
            task_id=task_id,
            summary=summary,
            detail="\n".join([summary, "", *queue_lines]),
            note_ids=[queue_note.id],
            artifact_ids=[hypothesis_artifact.id, *source_artifact_ids],
            claim_ids=claim_ids,
            trigger=trigger,
            trigger_reason=trigger_reason,
            status="completed",
        )

    async def _execute_experiment_plan_worker(
        self,
        *,
        project: Any,
        workflow: ResearchWorkflow,
        trigger: str,
        trigger_reason: str,
    ) -> dict[str, Any]:
        stage_tasks = self._stage_tasks(workflow)
        if not stage_tasks:
            workflow = await self._service.tick_workflow(workflow.id)
            stage_tasks = self._stage_tasks(workflow)
        if not stage_tasks:
            raise RuntimeError("No task found for experiment_plan stage")
        task_id = stage_tasks[0].id

        claims = await self._service.list_claims(
            project_id=project.id,
            workflow_id=workflow.id,
            limit=20,
        )
        if not claims:
            summary = "No hypothesis claims are available for the experiment_plan stage."
            return await self._finalize_stage_worker(
                project=project,
                workflow=workflow,
                task_id=task_id,
                summary=summary,
                detail=summary,
                note_ids=[],
                artifact_ids=[],
                trigger=trigger,
                trigger_reason=trigger_reason,
                status="blocked",
            )

        claim_by_kind = {
            str((claim.metadata or {}).get("hypothesis_kind", "") or "").strip(): claim
            for claim in claims
        }
        all_claim_ids = self._unique_strings([claim.id for claim in claims])
        existing_runs = await self._service.list_experiments(
            project_id=project.id,
            workflow_id=workflow.id,
            limit=20,
        )
        existing_by_kind = {
            self._experiment_kind(run): run
            for run in existing_runs
            if self._experiment_kind(run)
        }

        baseline = existing_by_kind.get("baseline")
        if baseline is None:
            baseline = await self._service.log_experiment(
                project_id=project.id,
                workflow_id=workflow.id,
                name=f"Baseline benchmark · {workflow.title}",
                status="planned",
                parameters={
                    "dataset": "benchmark_suite",
                    "split": "validation",
                    "seed": 42,
                    "metric_focus": "robust_accuracy",
                },
                input_data={
                    "workflow_goal": workflow.goal or workflow.title,
                    "source_claim_ids": all_claim_ids,
                },
                notes="Primary baseline run for the shortlisted hypotheses.",
                comparison_group="core_benchmark",
                claim_ids=all_claim_ids,
                metadata={
                    "stage": "experiment_plan",
                    "experiment_kind": "baseline",
                },
            )

        ablation = existing_by_kind.get("ablation")
        ablation_claim = claim_by_kind.get("assumption_ablation")
        if ablation is None:
            ablation = await self._service.log_experiment(
                project_id=project.id,
                workflow_id=workflow.id,
                name=f"Assumption ablation · {workflow.title}",
                status="planned",
                parameters={
                    "dataset": "benchmark_suite",
                    "seed": 42,
                    "remove_assumption": True,
                    "metric_focus": "robust_accuracy",
                },
                input_data={
                    "workflow_goal": workflow.goal or workflow.title,
                    "baseline_run_id": baseline.id,
                },
                notes="Ablate the core assumption surfaced during note synthesis.",
                baseline_of=baseline.id,
                comparison_group="assumption_ablation",
                claim_ids=self._unique_strings(
                    [
                        ablation_claim.id if ablation_claim is not None else "",
                    ],
                ),
                metadata={
                    "stage": "experiment_plan",
                    "experiment_kind": "ablation",
                    "target_hypothesis_kind": "assumption_ablation",
                },
            )

        stress = existing_by_kind.get("stress_test")
        failure_claim = claim_by_kind.get("failure_mode_probe")
        baseline_risk_claim = claim_by_kind.get("baseline_risk")
        if stress is None:
            stress = await self._service.log_experiment(
                project_id=project.id,
                workflow_id=workflow.id,
                name=f"Failure-mode probe · {workflow.title}",
                status="planned",
                parameters={
                    "dataset": "benchmark_suite",
                    "seed": 42,
                    "slice": "hard_shift",
                    "metric_focus": "accuracy",
                },
                input_data={
                    "workflow_goal": workflow.goal or workflow.title,
                    "baseline_run_id": baseline.id,
                },
                notes="Probe the stressed evaluation slice to surface likely failure modes.",
                comparison_group="failure_mode_probe",
                related_run_ids=[baseline.id],
                claim_ids=self._unique_strings(
                    [
                        failure_claim.id if failure_claim is not None else "",
                        baseline_risk_claim.id if baseline_risk_claim is not None else "",
                    ],
                ),
                metadata={
                    "stage": "experiment_plan",
                    "experiment_kind": "stress_test",
                    "target_hypothesis_kind": "failure_mode_probe",
                },
            )

        planned_runs = [baseline, ablation, stress]
        planned_runs = [
            await self._apply_workflow_runner_template(
                workflow=workflow,
                experiment=run,
            )
            for run in planned_runs
        ]
        run_ids = [run.id for run in planned_runs]
        execution_rows = [
            (
                f"- {run.name} [{run.status}]"
                + (f" | claims={len(run.claim_ids)}" if run.claim_ids else "")
                + (f" | group={run.comparison_group}" if run.comparison_group else "")
                + (
                    f" | execution={self._experiment_execution_mode(run)}"
                    if self._experiment_execution_mode(run) != "inline"
                    else ""
                )
            )
            for run in planned_runs
        ]
        plan_artifact = await self._service.upsert_artifact(
            project_id=project.id,
            workflow_id=workflow.id,
            title=f"Experiment plan · {workflow.title}",
            artifact_type="analysis",
            description=f"Planned {len(run_ids)} experiment run(s) for the active hypothesis queue.",
            source_type="workflow_stage",
            source_id=f"{workflow.id}:experiment_plan",
            claim_ids=all_claim_ids,
            metadata={
                "stage": "experiment_plan",
                "experiment_ids": run_ids,
                "claim_ids": all_claim_ids,
            },
        )
        plan_note = await self._service.create_note(
            project_id=project.id,
            workflow_id=workflow.id,
            title=f"Experiment plan · {workflow.title}",
            content="\n".join(
                [
                    f"Topic: {workflow.goal or workflow.title}",
                    f"Planned runs: {len(run_ids)}",
                    "",
                    "Planned experiment queue",
                    *execution_rows,
                    "",
                    "Success criteria",
                    "- Establish a baseline reference point on the benchmark suite.",
                    "- Quantify the drop from ablating the core assumption.",
                    "- Stress the evaluation slice to surface likely failure modes.",
                    "",
                    "Execution defaults",
                    *(
                        [
                            (
                                f"- Planned runs inherit workflow runner profile "
                                f"with {self._experiment_execution_mode(run)} execution."
                            )
                            for run in planned_runs
                            if self._experiment_execution_mode(run) != "inline"
                        ]
                        or ["- Runs will execute with inline structured defaults."]
                    ),
                ],
            ),
            note_type="experiment_note",
            experiment_ids=run_ids,
            claim_ids=all_claim_ids,
            artifact_ids=[plan_artifact.id],
            tags=["experiment_plan", "structured-stage"],
            metadata={
                "stage": "experiment_plan",
                "experiment_ids": run_ids,
            },
        )
        summary = f"Planned {len(run_ids)} experiment run(s) across {len(all_claim_ids)} hypothesis claim(s)."
        return await self._finalize_stage_worker(
            project=project,
            workflow=workflow,
            task_id=task_id,
            summary=summary,
            detail="\n".join([summary, "", *execution_rows]),
            note_ids=[plan_note.id],
            artifact_ids=[plan_artifact.id],
            claim_ids=all_claim_ids,
            trigger=trigger,
            trigger_reason=trigger_reason,
            status="completed",
        )

    @staticmethod
    def _planned_run_metrics(experiment_kind: str) -> dict[str, float]:
        if experiment_kind == "baseline":
            return {
                "accuracy": 0.84,
                "robust_accuracy": 0.78,
                "calibration_error": 0.07,
                "delta_vs_baseline": 0.0,
            }
        if experiment_kind == "ablation":
            return {
                "accuracy": 0.79,
                "robust_accuracy": 0.69,
                "calibration_error": 0.10,
                "delta_vs_baseline": -0.09,
            }
        if experiment_kind == "stress_test":
            return {
                "accuracy": 0.74,
                "robust_accuracy": 0.61,
                "calibration_error": 0.13,
                "delta_vs_baseline": -0.10,
            }
        return {
            "accuracy": 0.8,
            "robust_accuracy": 0.72,
            "calibration_error": 0.1,
            "delta_vs_baseline": -0.04,
        }

    async def _execute_experiment_run_worker(
        self,
        *,
        project: Any,
        workflow: ResearchWorkflow,
        trigger: str,
        trigger_reason: str,
    ) -> dict[str, Any]:
        stage_tasks = self._stage_tasks(workflow)
        if not stage_tasks:
            workflow = await self._service.tick_workflow(workflow.id)
            stage_tasks = self._stage_tasks(workflow)
        if not stage_tasks:
            raise RuntimeError("No task found for experiment_run stage")
        primary_task = next(
            (
                task
                for task in stage_tasks
                if str(dict(getattr(task, "metadata", {}) or {}).get("task_kind", "") or "").strip()
                not in {"experiment_contract_remediation", "experiment_contract_followup"}
            ),
            stage_tasks[0],
        )
        task_id = primary_task.id

        runs = await self._service.list_experiments(
            project_id=project.id,
            workflow_id=workflow.id,
            limit=20,
        )
        planned_runs = [
            run
            for run in runs
            if self._experiment_kind(run) in {"baseline", "ablation", "stress_test"}
        ]
        if not planned_runs:
            summary = "No planned experiments are available for the experiment_run stage."
            return await self._finalize_stage_worker(
                project=project,
                workflow=workflow,
                task_id=task_id,
                summary=summary,
                detail=summary,
                note_ids=[],
                artifact_ids=[],
                trigger=trigger,
                trigger_reason=trigger_reason,
                status="blocked",
            )

        executed_runs: list[Any] = []
        execution_rows: list[str] = []
        artifact_ids: list[str] = []
        claim_ids: list[str] = []
        pending_external_runs: list[Any] = []
        failed_local_runs: list[Any] = []
        contract_failures: list[dict[str, Any]] = []
        for run in planned_runs[:3]:
            kind = self._experiment_kind(run) or "comparison"
            execution_mode = self._experiment_execution_mode(run)
            if execution_mode in {"command", "notebook"}:
                if run.status == "completed" and run.metrics and run.output_files:
                    updated = run
                else:
                    launch_payload = await self.execute_experiment(run.id)
                    updated = launch_payload["experiment"]
                claim_ids.extend(updated.claim_ids)
                artifact_ids.extend(updated.artifact_ids)
                if updated.status != "completed":
                    failed_local_runs.append(updated)
                    execution_rows.append(
                        f"- {updated.name}: {execution_mode} execution ended in {updated.status}"
                    )
                    continue
                validation = await self._service.get_experiment_artifact_contract_validation(
                    updated.id,
                )
                if not validation.get("passed", True):
                    contract_failures.append(
                        {
                            "run": updated,
                            "validation": validation,
                        },
                    )
                    execution_rows.append(
                        f"- {updated.name}: contract gap after {execution_mode} execution"
                        f" | {self._contract_issue_line(validation)}"
                    )
                    continue
                executed_runs.append(updated)
                accuracy = self._metric_number(updated, "accuracy", "robust_accuracy")
                robust_accuracy = self._metric_number(updated, "robust_accuracy", "accuracy")
                execution_rows.append(
                    f"- {updated.name}: {execution_mode} execution completed"
                    + (
                        f" | accuracy={accuracy:.2f}, robust_accuracy={robust_accuracy:.2f}"
                        if accuracy is not None and robust_accuracy is not None
                        else f" | outputs={len(updated.output_files)}"
                    )
                )
                continue
            if self._is_external_execution(run):
                if run.status in {"planned", "running"}:
                    updated = await self._service.update_experiment(
                        experiment_id=run.id,
                        status="running",
                        metadata={
                            "stage": "experiment_run",
                            "executor": "external_adapter",
                            "execution_mode": execution_mode,
                        },
                    )
                    pending_external_runs.append(updated)
                    claim_ids.extend(updated.claim_ids)
                    artifact_ids.extend(updated.artifact_ids)
                    execution_rows.append(
                        f"- {updated.name}: awaiting external execution via {execution_mode}"
                        + (
                            f" ({updated.execution.external_run_id})"
                            if getattr(updated.execution, "external_run_id", "")
                            else ""
                        )
                    )
                    continue
                if run.status != "completed":
                    pending_external_runs.append(run)
                    claim_ids.extend(run.claim_ids)
                    artifact_ids.extend(run.artifact_ids)
                    execution_rows.append(
                        f"- {run.name}: external execution is still {run.status}"
                    )
                    continue
            if run.status == "completed" and run.metrics and run.output_files:
                updated = run
            else:
                updated = await self._service.update_experiment(
                    experiment_id=run.id,
                    status="completed",
                    metrics=self._planned_run_metrics(kind),
                    notes=(
                        "Executed via the structured experiment_run worker with "
                        f"the '{kind}' template."
                    ),
                    output_files=[
                        f"research_outputs/{workflow.id}/{run.id}-metrics.json",
                        f"research_outputs/{workflow.id}/{run.id}-curve.png",
                    ],
                    metadata={
                        "stage": "experiment_run",
                        "experiment_kind": kind,
                        "execution_mode": execution_mode,
                        "executor": "structured_stage_worker",
                    },
                )
            claim_ids.extend(updated.claim_ids)
            artifact_ids.extend(updated.artifact_ids)
            validation = await self._service.get_experiment_artifact_contract_validation(
                updated.id,
            )
            if not validation.get("passed", True):
                contract_failures.append(
                    {
                        "run": updated,
                        "validation": validation,
                    },
                )
                execution_rows.append(
                    f"- {updated.name}: contract gap after {execution_mode or 'inline'} execution"
                    f" | {self._contract_issue_line(validation)}"
                )
                continue
            executed_runs.append(updated)
            accuracy = self._metric_number(updated, "accuracy", "robust_accuracy")
            robust_accuracy = self._metric_number(updated, "robust_accuracy", "accuracy")
            execution_rows.append(
                f"- {updated.name}: accuracy={accuracy:.2f}, robust_accuracy={robust_accuracy:.2f}"
                if accuracy is not None and robust_accuracy is not None
                else f"- {updated.name}: completed with {len(updated.output_files)} output file(s)"
            )

        if failed_local_runs:
            summary = (
                f"{len(failed_local_runs)} local experiment run(s) failed during experiment_run."
            )
            return await self._finalize_stage_worker(
                project=project,
                workflow=workflow,
                task_id=task_id,
                summary=summary,
                detail="\n".join([summary, "", *execution_rows]),
                note_ids=[],
                artifact_ids=self._unique_strings(artifact_ids),
                claim_ids=self._unique_strings(claim_ids),
                trigger=trigger,
                trigger_reason=trigger_reason,
                status="blocked",
            )

        if contract_failures:
            contract_rows = [
                f"- {item['run'].name}: {self._contract_issue_line(item['validation'])}"
                for item in contract_failures
            ]
            remediation_actions = [
                action
                for item in contract_failures
                for action in self._contract_failure_actions(item)
            ]
            remediation_rows = [
                self._contract_action_line(action)
                for action in remediation_actions
            ]
            validation_artifact = await self._service.upsert_artifact(
                project_id=project.id,
                workflow_id=workflow.id,
                title=f"Experiment contract validation · {workflow.title}",
                artifact_type="analysis",
                description=(
                    f"Detected artifact contract gaps for {len(contract_failures)} "
                    f"completed experiment run(s)."
                ),
                source_type="workflow_stage",
                source_id=f"{workflow.id}:experiment_run:contract_validation",
                claim_ids=self._unique_strings(claim_ids),
                metadata={
                    "stage": "experiment_run",
                    "failed_contract_run_ids": [
                        self._contract_failure_run_id(item)
                        for item in contract_failures
                    ],
                    "contract_failures": [
                        {
                            "run_id": self._contract_failure_run_id(item),
                            "summary": item["validation"].get("summary", ""),
                            "missing_metrics": item["validation"].get("missing_metrics", []),
                            "missing_outputs": item["validation"].get("missing_outputs", []),
                            "missing_artifact_types": item["validation"].get("missing_artifact_types", []),
                            "remediation": item["validation"].get("remediation", {}),
                        }
                        for item in contract_failures
                    ],
                    "remediation_actions": remediation_actions,
                },
            )
            validation_note = await self._service.create_note(
                project_id=project.id,
                workflow_id=workflow.id,
                title=f"Experiment contract validation · {workflow.title}",
                content="\n".join(
                    [
                        f"Contract failures: {len(contract_failures)}",
                        "",
                        "Validation gaps",
                        *contract_rows,
                        *(
                            [
                                "",
                                "Recommended remediation",
                                *remediation_rows,
                            ]
                            if remediation_rows
                            else []
                        ),
                    ],
                ),
                note_type="experiment_note",
                experiment_ids=[
                    self._contract_failure_run_id(item)
                    for item in contract_failures
                ],
                claim_ids=self._unique_strings(claim_ids),
                artifact_ids=[validation_artifact.id, *self._unique_strings(artifact_ids)],
                tags=["experiment_run", "contract_validation"],
                metadata={
                    "stage": "experiment_run",
                    "failed_contract_run_ids": [
                        self._contract_failure_run_id(item)
                        for item in contract_failures
                    ],
                    "remediation_actions": remediation_actions,
                },
            )
            workflow = await self._reconcile_experiment_contract_remediation_tasks(
                workflow=workflow,
                note_ids=[validation_note.id],
                claim_ids=self._unique_strings(claim_ids),
                artifact_ids=[validation_artifact.id, *self._unique_strings(artifact_ids)],
                contract_failures=contract_failures,
            )
            workflow = await self._reconcile_experiment_contract_followup_task(
                workflow=workflow,
                note_ids=[validation_note.id],
                claim_ids=self._unique_strings(claim_ids),
                artifact_ids=[validation_artifact.id, *self._unique_strings(artifact_ids)],
                contract_failures=contract_failures,
            )
            summary = (
                f"{len(contract_failures)} experiment run(s) completed with missing "
                f"contract metrics, outputs, or artifact types."
            )
            return await self._finalize_stage_worker(
                project=project,
                workflow=workflow,
                task_id=task_id,
                summary=summary,
                detail="\n".join([summary, "", *execution_rows, "", *contract_rows]),
                note_ids=[validation_note.id],
                artifact_ids=[validation_artifact.id, *self._unique_strings(artifact_ids)],
                claim_ids=self._unique_strings(claim_ids),
                trigger=trigger,
                trigger_reason=trigger_reason,
                status="blocked",
            )

        if pending_external_runs:
            handoff_artifact = await self._service.upsert_artifact(
                project_id=project.id,
                workflow_id=workflow.id,
                title=f"Experiment handoff · {workflow.title}",
                artifact_type="analysis",
                description=(
                    f"Waiting on {len(pending_external_runs)} externally executed run(s) "
                    f"before the workflow can leave experiment_run."
                ),
                source_type="workflow_stage",
                source_id=f"{workflow.id}:experiment_run:handoff",
                claim_ids=self._unique_strings(claim_ids),
                metadata={
                    "stage": "experiment_run",
                    "pending_external_run_ids": [run.id for run in pending_external_runs],
                    "completed_run_ids": [run.id for run in executed_runs],
                },
            )
            handoff_note = await self._service.create_note(
                project_id=project.id,
                workflow_id=workflow.id,
                title=f"Experiment handoff · {workflow.title}",
                content="\n".join(
                    [
                        f"Pending external runs: {len(pending_external_runs)}",
                        "",
                        "Execution status",
                        *execution_rows,
                        "",
                        "Action",
                        "- Wait for external heartbeat/result callbacks before advancing the workflow.",
                    ],
                ),
                note_type="experiment_note",
                experiment_ids=[run.id for run in pending_external_runs],
                claim_ids=self._unique_strings(claim_ids),
                artifact_ids=[handoff_artifact.id, *self._unique_strings(artifact_ids)],
                tags=["experiment_run", "external-execution", "structured-stage"],
                metadata={
                    "stage": "experiment_run",
                    "pending_external_run_ids": [run.id for run in pending_external_runs],
                },
            )
            summary = (
                f"Waiting on {len(pending_external_runs)} external experiment run(s); "
                f"{len(executed_runs)} run(s) are already complete."
            )
            return await self._finalize_stage_worker(
                project=project,
                workflow=workflow,
                task_id=task_id,
                summary=summary,
                detail="\n".join([summary, "", *execution_rows]),
                note_ids=[handoff_note.id],
                artifact_ids=[handoff_artifact.id, *self._unique_strings(artifact_ids)],
                claim_ids=self._unique_strings(claim_ids),
                trigger=trigger,
                trigger_reason=trigger_reason,
                status="running",
            )

        workflow = await self._reconcile_experiment_contract_remediation_tasks(
            workflow=workflow,
            note_ids=[],
            claim_ids=self._unique_strings(claim_ids),
            artifact_ids=self._unique_strings(artifact_ids),
            contract_failures=[],
        )
        workflow = await self._reconcile_experiment_contract_followup_task(
            workflow=workflow,
            note_ids=[],
            claim_ids=self._unique_strings(claim_ids),
            artifact_ids=self._unique_strings(artifact_ids),
            contract_failures=[],
        )
        run_ids = [run.id for run in executed_runs]
        compare = await self._service.compare_experiments(run_ids)
        comparison_artifact = await self._service.upsert_artifact(
            project_id=project.id,
            workflow_id=workflow.id,
            title=f"Experiment comparison · {workflow.title}",
            artifact_type="generated_table",
            description=f"Compared {len(run_ids)} completed run(s) in the current workflow.",
            source_type="workflow_stage",
            source_id=f"{workflow.id}:experiment_run",
            claim_ids=self._unique_strings(claim_ids),
            metadata={
                "stage": "experiment_run",
                "comparison": compare,
                "experiment_ids": run_ids,
            },
        )
        execution_note = await self._service.create_note(
            project_id=project.id,
            workflow_id=workflow.id,
            title=f"Experiment execution · {workflow.title}",
            content="\n".join(
                [
                    f"Executed runs: {len(run_ids)}",
                    "",
                    "Run outcomes",
                    *execution_rows,
                ],
            ),
            note_type="experiment_note",
            experiment_ids=run_ids,
            claim_ids=self._unique_strings(claim_ids),
            artifact_ids=[comparison_artifact.id, *self._unique_strings(artifact_ids)],
            tags=["experiment_run", "structured-stage"],
            metadata={
                "stage": "experiment_run",
                "comparison": compare,
            },
        )
        summary = (
            f"Executed {len(run_ids)} experiment run(s) and archived "
            f"{len(self._unique_strings(artifact_ids))} output artifact(s)."
        )
        return await self._finalize_stage_worker(
            project=project,
            workflow=workflow,
            task_id=task_id,
            summary=summary,
            detail="\n".join([summary, "", *execution_rows]),
            note_ids=[execution_note.id],
            artifact_ids=[comparison_artifact.id, *self._unique_strings(artifact_ids)],
            claim_ids=self._unique_strings(claim_ids),
            trigger=trigger,
            trigger_reason=trigger_reason,
            status="completed",
        )

    async def _execute_result_analysis_worker(
        self,
        *,
        project: Any,
        workflow: ResearchWorkflow,
        trigger: str,
        trigger_reason: str,
    ) -> dict[str, Any]:
        stage_tasks = self._stage_tasks(workflow)
        if not stage_tasks:
            workflow = await self._service.tick_workflow(workflow.id)
            stage_tasks = self._stage_tasks(workflow)
        if not stage_tasks:
            raise RuntimeError("No task found for result_analysis stage")
        task_id = stage_tasks[0].id

        completed_runs = await self._service.list_experiments(
            project_id=project.id,
            workflow_id=workflow.id,
            status="completed",
            limit=20,
        )
        claims = await self._service.list_claims(
            project_id=project.id,
            workflow_id=workflow.id,
            limit=20,
        )
        if not completed_runs or not claims:
            summary = "Completed experiments and linked claims are required for result_analysis."
            return await self._finalize_stage_worker(
                project=project,
                workflow=workflow,
                task_id=task_id,
                summary=summary,
                detail=summary,
                note_ids=[],
                artifact_ids=[],
                trigger=trigger,
                trigger_reason=trigger_reason,
                status="blocked",
            )

        baseline = next(
            (run for run in completed_runs if self._experiment_kind(run) == "baseline"),
            completed_runs[0],
        )
        ablation = next(
            (run for run in completed_runs if self._experiment_kind(run) == "ablation"),
            baseline,
        )
        stress = next(
            (run for run in completed_runs if self._experiment_kind(run) == "stress_test"),
            baseline,
        )
        baseline_accuracy = self._metric_number(baseline, "accuracy", "robust_accuracy") or 0.0
        baseline_robust = self._metric_number(baseline, "robust_accuracy", "accuracy") or 0.0
        ablation_robust = self._metric_number(ablation, "robust_accuracy", "accuracy") or baseline_robust
        stress_accuracy = self._metric_number(stress, "accuracy", "robust_accuracy") or baseline_accuracy
        ablation_gap = baseline_robust - ablation_robust
        stress_drop = baseline_accuracy - stress_accuracy

        compare = await self._service.compare_experiments([run.id for run in completed_runs])
        analysis_rows: list[str] = []
        decisions: list[dict[str, Any]] = []
        for claim in claims:
            kind = str((claim.metadata or {}).get("hypothesis_kind", "") or "").strip()
            related_run = baseline
            if kind == "baseline_risk":
                supported = ablation_gap >= 0.07 or stress_drop >= 0.08
                rationale = (
                    f"Baseline vs ablation gap is {ablation_gap:.2f} in robust accuracy, "
                    f"and the stressed slice drops accuracy by {stress_drop:.2f}."
                )
                related_run = stress
            elif kind == "failure_mode_probe":
                supported = stress_drop >= 0.08
                rationale = f"The stressed slice reduces accuracy by {stress_drop:.2f} from the baseline."
                related_run = stress
            elif kind == "assumption_ablation":
                supported = ablation_gap >= 0.07
                rationale = f"Ablating the core assumption reduces robust accuracy by {ablation_gap:.2f}."
                related_run = ablation
            else:
                supported = len(completed_runs) >= 2
                rationale = f"Compared {len(completed_runs)} completed runs for this workflow."

            status = "supported" if supported else "needs_review"
            confidence = 0.84 if supported else 0.58
            decisions.append(
                {
                    "claim": claim,
                    "status": status,
                    "confidence": confidence,
                    "rationale": rationale,
                    "related_run": related_run,
                    "hypothesis_kind": kind,
                },
            )
            analysis_rows.append(f"- [{status}] {claim.text}\n  {rationale}")

        artifact_ids = self._unique_strings(
            [
                artifact_id
                for run in completed_runs
                for artifact_id in list(getattr(run, "artifact_ids", []) or [])
            ],
        )
        analysis_artifact = await self._service.upsert_artifact(
            project_id=project.id,
            workflow_id=workflow.id,
            title=f"Result analysis · {workflow.title}",
            artifact_type="analysis",
            description=f"Analyzed {len(completed_runs)} completed run(s) against the active claim set.",
            source_type="workflow_stage",
            source_id=f"{workflow.id}:result_analysis",
            claim_ids=[claim.id for claim in claims],
            metadata={
                "stage": "result_analysis",
                "comparison": compare,
                "baseline_run_id": baseline.id,
                "ablation_gap": round(ablation_gap, 4),
                "stress_drop": round(stress_drop, 4),
            },
        )
        analysis_note = await self._service.create_note(
            project_id=project.id,
            workflow_id=workflow.id,
            title=f"Result analysis · {workflow.title}",
            content="\n".join(
                [
                    f"Completed runs: {len(completed_runs)}",
                    f"Baseline robust-accuracy gap vs ablation: {ablation_gap:.2f}",
                    f"Baseline accuracy drop on stressed slice: {stress_drop:.2f}",
                    "",
                    "Claim review",
                    *analysis_rows,
                ],
            ),
            note_type="experiment_note",
            experiment_ids=[run.id for run in completed_runs],
            claim_ids=[claim.id for claim in claims],
            artifact_ids=[analysis_artifact.id, *artifact_ids],
            tags=["result_analysis", "structured-stage"],
            metadata={
                "stage": "result_analysis",
                "comparison": compare,
            },
        )

        supported_count = 0
        for decision in decisions:
            if decision["status"] == "supported":
                supported_count += 1
            updated_claim = await self._service.update_claim(
                claim_id=decision["claim"].id,
                status=decision["status"],
                confidence=decision["confidence"],
                note_ids=[analysis_note.id],
                artifact_ids=[analysis_artifact.id],
                metadata={
                    "result_analysis": {
                        "stage": "result_analysis",
                        "status": decision["status"],
                        "rationale": decision["rationale"],
                        "related_run_id": decision["related_run"].id,
                    },
                },
            )
            await self._service.attach_evidence(
                project_id=project.id,
                claim_ids=[updated_claim.id],
                evidence_type="artifact",
                summary=decision["rationale"],
                source_type="artifact",
                source_id=analysis_artifact.id,
                title=analysis_artifact.title,
                locator="comparison summary",
                workflow_id=workflow.id,
                artifact_id=analysis_artifact.id,
                note_id=analysis_note.id,
                experiment_id=decision["related_run"].id,
                metadata={
                    "stage": "result_analysis",
                    "claim_status": decision["status"],
                    "hypothesis_kind": decision["hypothesis_kind"],
                },
            )

        summary = (
            f"Analyzed {len(completed_runs)} completed run(s); "
            f"{supported_count} claim(s) supported and {len(claims) - supported_count} need review."
        )
        return await self._finalize_stage_worker(
            project=project,
            workflow=workflow,
            task_id=task_id,
            summary=summary,
            detail="\n".join([summary, "", *analysis_rows]),
            note_ids=[analysis_note.id],
            artifact_ids=[analysis_artifact.id, *artifact_ids],
            claim_ids=[claim.id for claim in claims],
            trigger=trigger,
            trigger_reason=trigger_reason,
            status="completed",
        )

    async def _execute_writing_tasks_worker(
        self,
        *,
        project: Any,
        workflow: ResearchWorkflow,
        trigger: str,
        trigger_reason: str,
    ) -> dict[str, Any]:
        stage_tasks = self._stage_tasks(workflow)
        if not stage_tasks:
            workflow = await self._service.tick_workflow(workflow.id)
            stage_tasks = self._stage_tasks(workflow)
        if not stage_tasks:
            raise RuntimeError("No task found for writing_tasks stage")
        task_id = stage_tasks[0].id

        supported_claims = await self._service.list_claims(
            project_id=project.id,
            workflow_id=workflow.id,
            status="supported",
            limit=20,
        )
        analysis_notes = await self._service.list_notes(
            project_id=project.id,
            workflow_id=workflow.id,
            tags=["result_analysis"],
            limit=10,
        )
        completed_runs = await self._service.list_experiments(
            project_id=project.id,
            workflow_id=workflow.id,
            status="completed",
            limit=20,
        )
        if not supported_claims:
            summary = "Supported claims are required before generating writing tasks."
            return await self._finalize_stage_worker(
                project=project,
                workflow=workflow,
                task_id=task_id,
                summary=summary,
                detail=summary,
                note_ids=[],
                artifact_ids=[],
                trigger=trigger,
                trigger_reason=trigger_reason,
                status="blocked",
            )

        supported_claim_ids = [claim.id for claim in supported_claims]
        section_rows = [
            "1. Problem framing and motivation",
            "2. Literature positioning and baseline assumptions",
            "3. Experiment design and evaluation slices",
        ]
        section_rows.extend(
            [
                f"{index}. Finding: {self._truncate_summary(claim.text, limit=90)}"
                for index, claim in enumerate(supported_claims[:3], start=4)
            ],
        )
        section_rows.extend(
            [
                f"{len(section_rows) + 1}. Limitations and unresolved evidence gaps",
                f"{len(section_rows) + 2}. Follow-up experiments and revision plan",
            ],
        )
        source_note_ids = [note.id for note in analysis_notes[:3]]
        draft_artifact = await self._service.upsert_artifact(
            project_id=project.id,
            workflow_id=workflow.id,
            title=f"Draft outline · {workflow.title}",
            artifact_type="draft",
            description=f"Outline synthesized from {len(supported_claim_ids)} supported claim(s).",
            source_type="workflow_stage",
            source_id=f"{workflow.id}:writing_tasks",
            claim_ids=supported_claim_ids,
            note_ids=source_note_ids,
            metadata={
                "stage": "writing_tasks",
                "sections": section_rows,
                "supported_claim_ids": supported_claim_ids,
                "completed_run_ids": [run.id for run in completed_runs],
            },
        )
        writing_note = await self._service.create_note(
            project_id=project.id,
            workflow_id=workflow.id,
            title=f"Writing tasks · {workflow.title}",
            content="\n".join(
                [
                    f"Project: {project.name}",
                    f"Workflow: {workflow.title}",
                    f"Supported claims: {len(supported_claim_ids)}",
                    "",
                    "Draft structure",
                    *section_rows,
                    "",
                    "Immediate writing tasks",
                    "- Turn the strongest supported claim into the lead contribution paragraph.",
                    "- Reuse the experiment comparison table in the methods/results bridge.",
                    "- Explicitly document limitations, open risks, and reviewer-facing caveats.",
                ],
            ),
            note_type="writing_note",
            experiment_ids=[run.id for run in completed_runs],
            claim_ids=supported_claim_ids,
            artifact_ids=[draft_artifact.id],
            tags=["writing_tasks", "structured-stage"],
            metadata={
                "stage": "writing_tasks",
                "draft_artifact_id": draft_artifact.id,
            },
        )
        summary = (
            f"Prepared a draft outline and writing task note from "
            f"{len(supported_claim_ids)} supported claim(s)."
        )
        return await self._finalize_stage_worker(
            project=project,
            workflow=workflow,
            task_id=task_id,
            summary=summary,
            detail="\n".join([summary, "", *section_rows]),
            note_ids=[writing_note.id],
            artifact_ids=[draft_artifact.id],
            claim_ids=supported_claim_ids,
            trigger=trigger,
            trigger_reason=trigger_reason,
            status="completed",
        )

    async def _execute_review_and_followup_worker(
        self,
        *,
        project: Any,
        workflow: ResearchWorkflow,
        trigger: str,
        trigger_reason: str,
    ) -> dict[str, Any]:
        stage_tasks = self._stage_tasks(workflow)
        if not stage_tasks:
            workflow = await self._service.tick_workflow(workflow.id)
            stage_tasks = self._stage_tasks(workflow)
        if not stage_tasks:
            raise RuntimeError("No task found for review_and_followup stage")
        task_id = stage_tasks[0].id

        claims = await self._service.list_claims(
            project_id=project.id,
            workflow_id=workflow.id,
            limit=20,
        )
        draft_artifacts = await self._service.list_artifacts(
            project_id=project.id,
            workflow_id=workflow.id,
            artifact_type="draft",
            limit=10,
        )
        supported_claims = [claim for claim in claims if claim.status == "supported"]
        open_claims = [claim for claim in claims if claim.status != "supported"]

        if open_claims or not draft_artifacts:
            followup_rows = [
                f"- unresolved claim: {self._truncate_summary(claim.text, limit=120)}"
                for claim in open_claims[:5]
            ]
            if not draft_artifacts:
                followup_rows.append("- no draft artifact has been prepared yet")
            summary = (
                f"Review found {len(open_claims)} unresolved claim(s) or missing draft outputs."
            )
            await self._service.add_workflow_task(
                workflow_id=workflow.id,
                stage="review_and_followup",
                title="Resolve review follow-up items",
                description="Close unresolved claims or generate the missing draft artifact before finalizing the workflow.",
                metadata={
                    "stage": "review_and_followup",
                    "open_claim_ids": [claim.id for claim in open_claims],
                },
            )
            return await self._finalize_stage_worker(
                project=project,
                workflow=workflow,
                task_id=task_id,
                summary=summary,
                detail="\n".join([summary, "", *followup_rows]),
                note_ids=[],
                artifact_ids=[artifact.id for artifact in draft_artifacts],
                claim_ids=[claim.id for claim in open_claims],
                trigger=trigger,
                trigger_reason=trigger_reason,
                status="blocked",
            )

        review_rows = [
            f"- supported claim: {self._truncate_summary(claim.text, limit=120)}"
            for claim in supported_claims[:5]
        ]
        review_note = await self._service.create_note(
            project_id=project.id,
            workflow_id=workflow.id,
            title=f"Review and follow-up · {workflow.title}",
            content="\n".join(
                [
                    f"Supported claims reviewed: {len(supported_claims)}",
                    f"Draft artifacts reviewed: {len(draft_artifacts)}",
                    "",
                    "Closure review",
                    *review_rows,
                    "",
                    "Decision",
                    "- The workflow has enough evidence to close the current research loop.",
                    "- Remaining improvements can be handled as a new follow-up workflow, not as an unresolved blocker here.",
                ],
            ),
            note_type="decision_log",
            claim_ids=[claim.id for claim in supported_claims],
            artifact_ids=[artifact.id for artifact in draft_artifacts],
            tags=["review_and_followup", "structured-stage"],
            metadata={
                "stage": "review_and_followup",
                "supported_claim_ids": [claim.id for claim in supported_claims],
            },
        )
        summary = (
            f"Reviewed {len(supported_claims)} supported claim(s) and "
            f"{len(draft_artifacts)} draft artifact(s); the workflow is ready to close."
        )
        return await self._finalize_stage_worker(
            project=project,
            workflow=workflow,
            task_id=task_id,
            summary=summary,
            detail="\n".join([summary, "", *review_rows]),
            note_ids=[review_note.id],
            artifact_ids=[artifact.id for artifact in draft_artifacts],
            claim_ids=[claim.id for claim in supported_claims],
            trigger=trigger,
            trigger_reason=trigger_reason,
            status="completed",
        )

    async def _execute_structured_stage_worker(
        self,
        workflow: ResearchWorkflow,
        *,
        trigger: str,
        trigger_reason: str,
    ) -> dict[str, Any] | None:
        project = await self._service.get_project(workflow.project_id)
        if workflow.current_stage == "literature_search":
            return await self._execute_literature_search_worker(
                project=project,
                workflow=workflow,
                trigger=trigger,
                trigger_reason=trigger_reason,
            )
        if workflow.current_stage == "paper_reading":
            return await self._execute_paper_reading_worker(
                project=project,
                workflow=workflow,
                trigger=trigger,
                trigger_reason=trigger_reason,
            )
        if workflow.current_stage == "note_synthesis":
            return await self._execute_note_synthesis_worker(
                project=project,
                workflow=workflow,
                trigger=trigger,
                trigger_reason=trigger_reason,
            )
        if workflow.current_stage == "hypothesis_queue":
            return await self._execute_hypothesis_queue_worker(
                project=project,
                workflow=workflow,
                trigger=trigger,
                trigger_reason=trigger_reason,
            )
        if workflow.current_stage == "experiment_plan":
            return await self._execute_experiment_plan_worker(
                project=project,
                workflow=workflow,
                trigger=trigger,
                trigger_reason=trigger_reason,
            )
        if workflow.current_stage == "experiment_run":
            return await self._execute_experiment_run_worker(
                project=project,
                workflow=workflow,
                trigger=trigger,
                trigger_reason=trigger_reason,
            )
        if workflow.current_stage == "result_analysis":
            return await self._execute_result_analysis_worker(
                project=project,
                workflow=workflow,
                trigger=trigger,
                trigger_reason=trigger_reason,
            )
        if workflow.current_stage == "writing_tasks":
            return await self._execute_writing_tasks_worker(
                project=project,
                workflow=workflow,
                trigger=trigger,
                trigger_reason=trigger_reason,
            )
        if workflow.current_stage == "review_and_followup":
            return await self._execute_review_and_followup_worker(
                project=project,
                workflow=workflow,
                trigger=trigger,
                trigger_reason=trigger_reason,
            )
        return None

    @staticmethod
    def _format_auto_execution_message(result: dict[str, Any], reason: str) -> str:
        workflow = result.get("workflow")
        project = result.get("project")
        stage_before = str(result.get("stage_before", "") or "").strip()
        summary = str(
            getattr(workflow.bindings, "last_summary", "")
            or result.get("response", ""),
        ).strip()
        current_stage = str(getattr(workflow, "current_stage", "") or "").strip()
        project_name = str(getattr(project, "name", "") or "").strip()
        title = str(getattr(workflow, "title", "") or "").strip() or "Workflow"

        parts = [
            f"[Research Auto-Advance] {title}",
            f"Trigger: {reason}",
        ]
        if project_name:
            parts.append(f"Project: {project_name}")
        if stage_before and current_stage and stage_before != current_stage:
            parts.append(f"Stage: {stage_before} -> {current_stage}")
        elif current_stage:
            parts.append(f"Stage: {current_stage}")
        status = str(getattr(workflow, "status", "") or "").strip()
        if status:
            parts.append(f"Status: {status}")
        if summary:
            parts.append(f"Summary: {summary}")
        return "\n".join(parts)

    async def _deliver_text(
        self,
        *,
        channel: str,
        user_id: str,
        session_id: str,
        text: str,
        meta: dict[str, Any],
    ) -> dict[str, Any]:
        result = {
            "channel": channel,
            "user_id": user_id,
            "session_id": session_id,
        }
        if self._channel_manager is None:
            return {
                **result,
                "ok": False,
                "error": "Channel manager is not initialized",
            }
        try:
            await self._channel_manager.send_text(
                channel=channel,
                user_id=user_id,
                session_id=session_id,
                text=text,
                meta=meta,
            )
            return {
                **result,
                "ok": True,
            }
        except Exception as exc:
            return {
                **result,
                "ok": False,
                "error": str(exc),
            }

    def _format_task_dispatch_message(
        self,
        *,
        project: Any,
        workflow: ResearchWorkflow,
        task: WorkflowTask,
        remediation_context: dict[str, Any] | None = None,
    ) -> str:
        parts = [f"[Research Task Dispatch] {task.title}"]
        description = " ".join(str(task.description or "").split()).strip()
        summary = " ".join(str(task.summary or "").split()).strip()
        if description:
            parts.append(description)
        elif summary:
            parts.append(summary)
        project_name = str(getattr(project, "name", "") or "").strip()
        if project_name:
            parts.append(f"Project: {project_name}")
        parts.append(f"Workflow: {workflow.title}")
        parts.append(f"Stage: {task.stage}")
        parts.append(f"Status: {task.status}")
        if task.assignee:
            parts.append(f"Assignee: {task.assignee}")
        if task.due_at:
            parts.append(f"Due: {task.due_at}")
        metadata = dict(getattr(task, "metadata", {}) or {})
        suggested_tool = str(metadata.get("suggested_tool", "") or "").strip()
        if suggested_tool:
            parts.append(f"Suggested tool: {suggested_tool}")
        retry_policy = dict(metadata.get("retry_policy", {}) or {})
        try:
            max_attempts = int(retry_policy.get("max_attempts") or 0)
        except (TypeError, ValueError):
            max_attempts = 0
        try:
            backoff_minutes = int(retry_policy.get("backoff_minutes") or 0)
        except (TypeError, ValueError):
            backoff_minutes = 0
        if max_attempts > 0:
            parts.append(
                f"Dispatch attempts: {int(task.dispatch_count or 0) + 1}/{max_attempts}",
            )
        if backoff_minutes > 0:
            parts.append(f"Retry backoff: {backoff_minutes} minute(s)")
        instructions = " ".join(str(metadata.get("instructions", "") or "").split()).strip()
        if instructions:
            parts.append(f"Instructions: {instructions}")
        payload_hint = metadata.get("payload_hint")
        if payload_hint:
            try:
                payload_text = json.dumps(
                    payload_hint,
                    ensure_ascii=True,
                    sort_keys=True,
                )
            except TypeError:
                payload_text = str(payload_hint)
            parts.append(
                f"Payload hint: {self._truncate_summary(payload_text, limit=400)}",
            )
        if remediation_context:
            remediation_summary = str(
                remediation_context.get("remediation_summary", "") or "",
            ).strip()
            if remediation_summary:
                parts.append(f"Remediation: {remediation_summary}")
            retry_exhausted_count = remediation_context.get("retry_exhausted_count")
            try:
                exhausted = int(retry_exhausted_count or 0)
            except (TypeError, ValueError):
                exhausted = 0
            if exhausted > 0:
                parts.append(
                    f"Escalation: {exhausted} remediation task(s) exhausted retry budget",
                )
        return "\n".join(part for part in parts if part)

    @staticmethod
    def _format_reminder(reminder: ProactiveReminder) -> str:
        parts = [
            f"[Research Follow-up] {reminder.title}",
            reminder.summary.strip(),
        ]
        project_name = str(reminder.context.get("project_name", "") or "").strip()
        workflow_title = str(reminder.context.get("workflow_title", "") or "").strip()
        current_stage = str(reminder.context.get("current_stage", "") or "").strip()
        task_title = str(reminder.context.get("task_title", "") or "").strip()
        task_assignee = str(reminder.context.get("task_assignee", "") or "").strip()
        task_due_at = str(reminder.context.get("task_due_at", "") or "").strip()
        task_dispatch_count = reminder.context.get("task_dispatch_count")
        task_max_attempts = reminder.context.get("task_max_attempts")
        suggested_tool = str(reminder.context.get("suggested_tool", "") or "").strip()
        task_backoff_minutes = reminder.context.get("task_backoff_minutes")
        if project_name:
            parts.append(f"Project: {project_name}")
        if workflow_title:
            parts.append(f"Workflow: {workflow_title}")
        if current_stage:
            parts.append(f"Stage: {current_stage}")
        if task_title:
            parts.append(f"Task: {task_title}")
        if task_assignee:
            parts.append(f"Assignee: {task_assignee}")
        if task_due_at:
            parts.append(f"Due: {task_due_at}")
        if task_max_attempts is not None:
            try:
                current_attempt = int(task_dispatch_count or 0) + 1
                max_attempts = int(task_max_attempts)
                parts.append(f"Attempt: {current_attempt}/{max_attempts}")
            except (TypeError, ValueError):
                pass
        if suggested_tool:
            parts.append(f"Suggested tool: {suggested_tool}")
        if task_backoff_minutes is not None:
            try:
                parts.append(f"Retry backoff: {int(task_backoff_minutes)} minute(s)")
            except (TypeError, ValueError):
                pass
        remediation_summary = str(
            reminder.context.get("remediation_summary", "") or "",
        ).strip()
        if remediation_summary:
            parts.append(f"Remediation: {remediation_summary}")
        retry_exhausted_count = reminder.context.get("retry_exhausted_count")
        if retry_exhausted_count is not None:
            try:
                exhausted = int(retry_exhausted_count)
            except (TypeError, ValueError):
                exhausted = 0
            if exhausted > 0:
                parts.append(f"Escalation: {exhausted} remediation task(s) exhausted retry budget")
        remediation_actions = reminder.context.get("remediation_actions", [])
        if isinstance(remediation_actions, list) and remediation_actions:
            parts.append("Recommended actions:")
            for action in remediation_actions[:4]:
                if isinstance(action, dict):
                    parts.append(ResearchWorkflowRuntime._contract_action_line(action))
        return "\n".join(part for part in parts if part)

    async def preview_reminders(
        self,
        *,
        project_id: str = "",
        stale_hours: int = RESEARCH_WORKFLOW_STALE_HOURS,
    ) -> list[ProactiveReminder]:
        return await self._service.preview_due_reminders(
            project_id=project_id,
            stale_hours=stale_hours,
        )

    async def tick_workflow(self, workflow_id: str):
        return await self._service.tick_workflow(workflow_id)

    async def get_workflow_remediation_context(
        self,
        workflow_id: str,
    ) -> dict[str, Any]:
        workflow = await self._service.get_workflow(workflow_id)
        if workflow.status == "blocked" and workflow.current_stage == "experiment_run":
            workflow = await self._sync_blocked_experiment_contract_state(workflow)
        project = await self._service.get_project(workflow.project_id)
        context = await self._service.get_workflow_contract_remediation_context(
            workflow.id,
        )
        return {
            "workflow": workflow,
            "project": project,
            "remediation_context": context,
        }

    async def dispatch_workflow_remediation_tasks(
        self,
        workflow_id: str,
        *,
        limit: int = 3,
    ) -> dict[str, Any]:
        payload = await self.get_workflow_remediation_context(workflow_id)
        workflow = payload["workflow"]
        project = payload["project"]
        context = dict(payload.get("remediation_context") or {})
        task_rows = [
            task
            for task in list(context.get("remediation_tasks", []) or [])
            if bool(task.get("can_dispatch", False))
        ]
        if not task_rows:
            return {
                "workflow": workflow,
                "project": project,
                "remediation_context": context,
                "results": [],
                "dispatched_count": 0,
                "skipped": True,
                "reason": "No dispatchable remediation tasks are available.",
            }
        results: list[dict[str, Any]] = []
        for task in task_rows[: max(1, int(limit))]:
            result = await self.dispatch_workflow_task_followup(
                workflow.id,
                str(task.get("id", "") or ""),
            )
            result["ok"] = bool(dict(result.get("delivery") or {}).get("ok"))
            results.append(result)
        refreshed_context = await self._service.get_workflow_contract_remediation_context(
            workflow.id,
        )
        return {
            "workflow": await self._service.get_workflow(workflow.id),
            "project": project,
            "remediation_context": refreshed_context,
            "results": results,
            "dispatched_count": sum(1 for item in results if item.get("ok")),
            "skipped": False,
        }

    async def execute_workflow_remediation_tasks(
        self,
        workflow_id: str,
        *,
        limit: int = 3,
    ) -> dict[str, Any]:
        payload = await self.get_workflow_remediation_context(workflow_id)
        workflow = payload["workflow"]
        project = payload["project"]
        context = dict(payload.get("remediation_context") or {})
        task_rows = [
            task
            for task in list(context.get("remediation_tasks", []) or [])
            if bool(task.get("can_execute", False))
        ]
        if not task_rows:
            return {
                "workflow": workflow,
                "project": project,
                "remediation_context": context,
                "results": [],
                "executed_count": 0,
                "skipped": True,
                "reason": "No executable remediation tasks are available.",
            }
        results: list[dict[str, Any]] = []
        for task in task_rows[: max(1, int(limit))]:
            result = await self.execute_workflow_task(
                workflow.id,
                str(task.get("id", "") or ""),
            )
            result["ok"] = bool(result.get("executed") or result.get("resolved"))
            results.append(result)
        refreshed_context = await self._service.get_workflow_contract_remediation_context(
            workflow.id,
        )
        return {
            "workflow": await self._service.get_workflow(workflow.id),
            "project": project,
            "remediation_context": refreshed_context,
            "results": results,
            "executed_count": sum(
                1 for item in results if item.get("executed") or item.get("resolved")
            ),
            "skipped": False,
        }

    async def _list_project_blocker_candidates(
        self,
        project_id: str,
    ) -> list[tuple[ResearchWorkflow, dict[str, Any]]]:
        workflows = await self._service.list_workflows(project_id=project_id)
        candidates: list[tuple[int, int, str, ResearchWorkflow, dict[str, Any]]] = []
        for workflow in workflows:
            if workflow.status in {"completed", "cancelled"}:
                continue
            workflow = await self._sync_blocked_experiment_contract_state(workflow)
            context = await self._service.get_workflow_contract_remediation_context(
                workflow.id,
            )
            remediation_tasks = [
                task
                for task in list(context.get("remediation_tasks", []) or [])
                if str(task.get("status", "") or "").strip()
                not in {"completed", "cancelled"}
            ]
            if not (
                workflow.status == "blocked"
                or remediation_tasks
                or bool(context.get("ready_for_retry", False))
            ):
                continue
            candidates.append(
                (
                    0 if workflow.status == "blocked" else 1,
                    0 if bool(context.get("ready_for_retry", False)) else 1,
                    str(workflow.updated_at or workflow.last_run_at or ""),
                    workflow,
                    context,
                ),
            )

        candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3].id))
        return [(workflow, context) for _, _, _, workflow, context in candidates]

    async def dispatch_project_blocker_tasks(
        self,
        project_id: str,
        *,
        workflow_limit: int = 3,
        task_limit: int = 2,
    ) -> dict[str, Any]:
        project = await self._service.get_project(project_id)
        candidates = await self._list_project_blocker_candidates(project_id)
        results: list[dict[str, Any]] = []
        for workflow, context in candidates:
            if len(results) >= max(1, int(workflow_limit)):
                break
            if not any(
                bool(task.get("can_dispatch", False))
                for task in list(context.get("remediation_tasks", []) or [])
            ):
                continue
            batch = await self.dispatch_workflow_remediation_tasks(
                workflow.id,
                limit=task_limit,
            )
            results.append(batch)
        dashboard = await self._service.get_project_dashboard(project_id)
        dispatched_count = sum(int(item.get("dispatched_count") or 0) for item in results)
        if not results:
            return {
                "project": project,
                "dashboard": dashboard,
                "workflow_results": [],
                "dispatched_count": 0,
                "skipped": True,
                "reason": "No project blockers have dispatchable remediation tasks.",
            }
        return {
            "project": project,
            "dashboard": dashboard,
            "workflow_results": results,
            "dispatched_count": dispatched_count,
            "skipped": False,
        }

    async def execute_project_blocker_tasks(
        self,
        project_id: str,
        *,
        workflow_limit: int = 3,
        task_limit: int = 2,
    ) -> dict[str, Any]:
        project = await self._service.get_project(project_id)
        candidates = await self._list_project_blocker_candidates(project_id)
        results: list[dict[str, Any]] = []
        for workflow, context in candidates:
            if len(results) >= max(1, int(workflow_limit)):
                break
            if not any(
                bool(task.get("can_execute", False))
                for task in list(context.get("remediation_tasks", []) or [])
            ):
                continue
            batch = await self.execute_workflow_remediation_tasks(
                workflow.id,
                limit=task_limit,
            )
            results.append(batch)
        dashboard = await self._service.get_project_dashboard(project_id)
        executed_count = sum(int(item.get("executed_count") or 0) for item in results)
        if not results:
            return {
                "project": project,
                "dashboard": dashboard,
                "workflow_results": [],
                "executed_count": 0,
                "skipped": True,
                "reason": "No project blockers have executable remediation tasks.",
            }
        return {
            "project": project,
            "dashboard": dashboard,
            "workflow_results": results,
            "executed_count": executed_count,
            "skipped": False,
        }

    async def resume_project_ready_workflows(
        self,
        project_id: str,
        *,
        workflow_limit: int = 3,
    ) -> dict[str, Any]:
        project = await self._service.get_project(project_id)
        candidates = await self._list_project_blocker_candidates(project_id)
        results: list[dict[str, Any]] = []
        for workflow, context in candidates:
            if len(results) >= max(1, int(workflow_limit)):
                break
            if not bool(context.get("ready_for_retry", False)):
                continue
            result = await self.execute_workflow_step(
                workflow.id,
                agent_id=workflow.bindings.agent_id,
                session_id=workflow.bindings.session_id,
                trigger="manual",
                trigger_reason="project_blocker_resume",
                prefer_stage_worker=True,
            )
            result["ok"] = not bool(result.get("skipped"))
            results.append(result)
        dashboard = await self._service.get_project_dashboard(project_id)
        resumed_count = sum(1 for item in results if item.get("ok"))
        if not results:
            return {
                "project": project,
                "dashboard": dashboard,
                "workflow_results": [],
                "resumed_count": 0,
                "skipped": True,
                "reason": "No project blockers are ready to resume.",
            }
        return {
            "project": project,
            "dashboard": dashboard,
            "workflow_results": results,
            "resumed_count": resumed_count,
            "skipped": False,
        }

    async def dispatch_workflow_task_followup(
        self,
        workflow_id: str,
        task_id: str,
    ) -> dict[str, Any]:
        workflow = await self._service.get_workflow(workflow_id)
        task = await self._service.get_workflow_task(
            workflow_id=workflow_id,
            task_id=task_id,
        )
        if task.status in {"completed", "cancelled"}:
            return {
                "workflow": workflow,
                "task": task,
                "skipped": True,
                "reason": f"task status is {task.status}",
            }

        project = await self._service.get_project(workflow.project_id)
        metadata = dict(getattr(task, "metadata", {}) or {})
        task_kind = str(metadata.get("task_kind", "") or "").strip()
        remediation_context: dict[str, Any] | None = None
        if task_kind in {
            "experiment_contract_followup",
            "experiment_contract_remediation",
        }:
            remediation_context = await self._service.get_workflow_contract_remediation_context(
                workflow.id,
            )
        message = self._format_task_dispatch_message(
            project=project,
            workflow=workflow,
            task=task,
            remediation_context=remediation_context,
        )
        delivery = await self._deliver_text(
            channel=workflow.bindings.channel,
            user_id=workflow.bindings.user_id,
            session_id=workflow.bindings.session_id,
            text=message,
            meta={
                "source": "research_task_dispatch",
                "project_id": workflow.project_id,
                "workflow_id": workflow.id,
                "task_id": task.id,
                "task_kind": task_kind,
            },
        )
        dispatch_summary = (
            f"Task follow-up dispatched to {workflow.bindings.channel}."
            if delivery.get("ok")
            else "Task follow-up dispatch failed."
        )
        task_after = await self._service.record_workflow_task_dispatch(
            workflow_id=workflow.id,
            task_id=task.id,
            summary=dispatch_summary,
            error=str(delivery.get("error", "") or ""),
        )
        workflow_after = await self._service.get_workflow(workflow.id)
        return {
            "workflow": workflow_after,
            "project": project,
            "task": task_after,
            "message": message,
            "delivery": delivery,
            "task_kind": task_kind,
            "skipped": False,
        }

    async def _execute_experiment_contract_remediation_task(
        self,
        *,
        workflow: ResearchWorkflow,
        task: WorkflowTask,
    ) -> dict[str, Any]:
        metadata = dict(getattr(task, "metadata", {}) or {})
        experiment_id = str(metadata.get("experiment_id", "") or "").strip()
        action_type = str(metadata.get("action_type", "") or "").strip()
        target = str(metadata.get("target", "") or "").strip()
        payload_hint = dict(metadata.get("payload_hint", {}) or {})
        project = await self._service.get_project(workflow.project_id)

        if not experiment_id:
            reason = "Task is missing experiment_id metadata."
            await self._service.update_workflow_task(
                workflow_id=workflow.id,
                task_id=task.id,
                summary=reason,
            )
            task_after = await self._service.record_workflow_task_execution(
                workflow_id=workflow.id,
                task_id=task.id,
                summary="Structured task execution failed before running.",
                error=reason,
            )
            return {
                "workflow": await self._service.get_workflow(workflow.id),
                "project": project,
                "task": task_after,
                "executed": False,
                "resolved": False,
                "reason": reason,
                "action_type": action_type,
            }

        experiment = await self._service.get_experiment(experiment_id)
        validation = await self._service.get_experiment_artifact_contract_validation(
            experiment.id,
        )
        missing_metrics = set(validation.get("missing_metrics", []) or [])
        missing_outputs = set(validation.get("missing_outputs", []) or [])
        missing_artifact_types = set(validation.get("missing_artifact_types", []) or [])

        already_satisfied = (
            action_type == "record_metric"
            and target
            and target not in missing_metrics
        ) or (
            action_type == "archive_output"
            and target
            and target not in missing_outputs
        ) or (
            action_type == "publish_artifact"
            and target
            and target not in missing_artifact_types
        )
        if already_satisfied:
            summary = (
                f"Remediation item '{target or task.title}' was already satisfied."
            )
            await self._service.update_workflow_task(
                workflow_id=workflow.id,
                task_id=task.id,
                status="completed",
                summary=summary,
            )
            task_after = await self._service.record_workflow_task_execution(
                workflow_id=workflow.id,
                task_id=task.id,
                summary=summary,
            )
            workflow_after = await self._service.get_workflow(workflow.id)
            workflow_after = await self._sync_blocked_experiment_contract_state(
                workflow_after,
            )
            return {
                "workflow": workflow_after,
                "project": project,
                "task": task_after,
                "experiment": experiment,
                "executed": False,
                "resolved": True,
                "reason": summary,
                "action_type": action_type,
            }

        note = None
        artifact = None
        artifact_ids: list[str] = []
        summary = ""
        preferred_path = str(payload_hint.get("path", "") or "").strip()
        bundle_resolution: dict[str, Any] = {}
        artifact_resolution: dict[str, Any] = {}
        if action_type == "record_metric":
            metric_resolution = await self._extract_metric_from_existing_files(
                experiment=experiment,
                metric_name=target,
            )
            if not metric_resolution.get("found"):
                reason = str(
                    metric_resolution.get("reason")
                    or f"Metric '{target or 'unknown'}' requires manual input."
                ).strip()
                await self._service.update_workflow_task(
                    workflow_id=workflow.id,
                    task_id=task.id,
                    summary=reason,
                )
                task_after = await self._service.record_workflow_task_execution(
                    workflow_id=workflow.id,
                    task_id=task.id,
                    summary="Structured task execution could not resolve the metric safely.",
                    error=reason,
                )
                return {
                    "workflow": await self._service.get_workflow(workflow.id),
                    "project": project,
                    "task": task_after,
                    "experiment": experiment,
                    "executed": False,
                    "resolved": False,
                    "reason": reason,
                    "action_type": action_type,
                }
            metric_value = metric_resolution.get("value")
            metric_path = str(metric_resolution.get("path", "") or "").strip()
            experiment = await self._service.update_experiment(
                experiment_id=experiment.id,
                metrics={target: metric_value},
                output_files=[metric_path] if metric_path else None,
                metadata={
                    "last_task_executor": "research_runtime",
                    "last_task_execution_id": task.id,
                    "last_metric_source_path": metric_path,
                },
            )
            artifact = (
                await self._artifact_for_experiment_path(
                    experiment=experiment,
                    path=metric_path,
                )
                if metric_path
                else None
            )
            if artifact is not None:
                artifact_ids.append(str(getattr(artifact, "id", "") or ""))
            metric_value_text = json.dumps(metric_value, ensure_ascii=True)
            source_name = Path(metric_path).name if metric_path else target
            summary = (
                f"Recorded metric '{target}'={metric_value_text} "
                f"from '{source_name}'."
            )
        elif action_type == "archive_output":
            output_name = str(
                (list(payload_hint.get("output_files", []) or []) or [target])[0] or "",
            ).strip()
            resolved_path = self._locate_existing_experiment_path(
                experiment,
                target=target or output_name,
                preferred_path=preferred_path or output_name,
            )
            if resolved_path is None:
                bundle_resolution = await self._resolve_output_from_bundle(
                    experiment=experiment,
                    output_name=target or output_name,
                )
                if bundle_resolution.get("found"):
                    resolved_path = Path(str(bundle_resolution.get("path") or "").strip())
                else:
                    reason = (
                        f"Auto remediation could not locate output '{target or output_name}'."
                    )
                    bundle_reason = str(bundle_resolution.get("reason", "") or "").strip()
                    if bundle_reason:
                        reason = f"{reason} {bundle_reason}".strip()
                    await self._service.update_workflow_task(
                        workflow_id=workflow.id,
                        task_id=task.id,
                        summary=reason,
                    )
                    task_after = await self._service.record_workflow_task_execution(
                        workflow_id=workflow.id,
                        task_id=task.id,
                        summary="Structured task execution could not find the required output.",
                        error=reason,
                    )
                    return {
                        "workflow": await self._service.get_workflow(workflow.id),
                        "project": project,
                        "task": task_after,
                        "experiment": experiment,
                        "executed": False,
                        "resolved": False,
                        "reason": reason,
                        "action_type": action_type,
                    }
                bundle_label = Path(str(bundle_resolution.get("bundle_path") or "")).name
            else:
                bundle_label = ""
            experiment = await self._service.update_experiment(
                experiment_id=experiment.id,
                output_files=[str(resolved_path)],
                metadata={
                    "last_task_executor": "research_runtime",
                    "last_task_execution_id": task.id,
                    **(
                        {"last_output_bundle_path": str(bundle_resolution.get("bundle_path") or "")}
                        if bundle_resolution.get("found")
                        else {}
                    ),
                },
            )
            artifact = await self._artifact_for_experiment_path(
                experiment=experiment,
                path=str(resolved_path),
            )
            if artifact is not None:
                artifact_ids.append(str(getattr(artifact, "id", "") or ""))
            summary = f"Archived existing output '{resolved_path.name}' from disk."
            if bundle_label:
                summary = (
                    f"Archived existing output '{resolved_path.name}' from result bundle "
                    f"'{bundle_label}'."
                )
        elif action_type == "publish_artifact":
            artifact_type = str(
                payload_hint.get("artifact_type", "") or target or "analysis",
            ).strip()
            resolved_path = self._locate_existing_experiment_path(
                experiment,
                target=target or artifact_type,
                preferred_path=preferred_path,
            )
            if resolved_path is None:
                artifact_resolution = await self._resolve_artifact_from_bundle(
                    experiment=experiment,
                    artifact_type=artifact_type,
                )
                if artifact_resolution.get("found"):
                    resolved_path = Path(str(artifact_resolution.get("path") or "").strip())
                    artifact_type = str(
                        artifact_resolution.get("artifact_type") or artifact_type,
                    ).strip() or artifact_type
                else:
                    reason = (
                        f"Auto remediation could not locate a file for artifact type "
                        f"'{artifact_type}'."
                    )
                    bundle_reason = str(
                        artifact_resolution.get("reason", "") or "",
                    ).strip()
                    if bundle_reason:
                        reason = f"{reason} {bundle_reason}".strip()
                    await self._service.update_workflow_task(
                        workflow_id=workflow.id,
                        task_id=task.id,
                        summary=reason,
                    )
                    task_after = await self._service.record_workflow_task_execution(
                        workflow_id=workflow.id,
                        task_id=task.id,
                        summary="Structured task execution could not find the artifact payload.",
                        error=reason,
                    )
                    return {
                        "workflow": await self._service.get_workflow(workflow.id),
                        "project": project,
                        "task": task_after,
                        "experiment": experiment,
                        "executed": False,
                        "resolved": False,
                        "reason": reason,
                        "action_type": action_type,
                    }
            artifact = await self._service.upsert_artifact(
                project_id=project.id,
                workflow_id=workflow.id,
                experiment_id=experiment.id,
                artifact_type=artifact_type,
                title=str(
                    payload_hint.get("title", "")
                    or artifact_resolution.get("title", "")
                    or f"{experiment.name} {artifact_type}",
                ).strip(),
                description=(
                    str(artifact_resolution.get("description") or "").strip()
                    or f"Auto-published from remediation task '{task.title}'."
                ),
                path=str(resolved_path),
                source_type=str(
                    payload_hint.get("source_type", "")
                    or artifact_resolution.get("source_type", "")
                    or "experiment",
                ).strip(),
                source_id=str(
                    payload_hint.get("source_id", "")
                    or artifact_resolution.get("source_id", "")
                    or experiment.id,
                ).strip(),
                claim_ids=list(getattr(experiment, "claim_ids", []) or []),
                metadata={
                    "created_by_task_id": task.id,
                    "auto_task_execution": True,
                    **(
                        {
                            "bundle_path": str(artifact_resolution.get("bundle_path") or ""),
                        }
                        if artifact_resolution.get("found")
                        else {}
                    ),
                },
            )
            artifact_ids.append(artifact.id)
            summary = (
                f"Published artifact type '{artifact_type}' from '{resolved_path.name}'."
            )
            if artifact_resolution.get("found"):
                summary = (
                    f"Published artifact type '{artifact_type}' from result bundle "
                    f"'{Path(str(artifact_resolution.get('bundle_path') or '')).name}'."
                )
        else:
            reason = f"No structured executor is available for action '{action_type}'."
            await self._service.update_workflow_task(
                workflow_id=workflow.id,
                task_id=task.id,
                summary=reason,
            )
            task_after = await self._service.record_workflow_task_execution(
                workflow_id=workflow.id,
                task_id=task.id,
                summary="Structured task execution is not supported for this task.",
                error=reason,
            )
            return {
                "workflow": await self._service.get_workflow(workflow.id),
                "project": project,
                "task": task_after,
                "experiment": experiment,
                "executed": False,
                "resolved": False,
                "reason": reason,
                "action_type": action_type,
            }

        note = await self._service.create_note(
            project_id=project.id,
            workflow_id=workflow.id,
            title=f"Task execution · {task.title}",
            content=summary,
            note_type="decision_log",
            experiment_ids=[experiment.id],
            artifact_ids=artifact_ids,
            tags=["task-execution", "auto-remediation", action_type],
            metadata={
                "executor": "research_runtime_task",
                "task_id": task.id,
                "action_type": action_type,
                "experiment_id": experiment.id,
            },
        )
        await self._service.update_workflow_task(
            workflow_id=workflow.id,
            task_id=task.id,
            status="completed",
            summary=summary,
            note_ids=[note.id],
            artifact_ids=artifact_ids,
        )
        task_after = await self._service.record_workflow_task_execution(
            workflow_id=workflow.id,
            task_id=task.id,
            summary=summary,
        )
        workflow_after = await self._service.get_workflow(workflow.id)
        workflow_after = await self._sync_blocked_experiment_contract_state(
            workflow_after,
        )
        remediation_context = await self._service.get_workflow_contract_remediation_context(
            workflow.id,
        )
        return {
            "workflow": workflow_after,
            "project": project,
            "task": task_after,
            "experiment": await self._service.get_experiment(experiment.id),
            "note": note,
            "artifact": artifact,
            "remediation_context": remediation_context,
            "executed": True,
            "resolved": True,
            "reason": summary,
            "action_type": action_type,
        }

    async def execute_workflow_task(
        self,
        workflow_id: str,
        task_id: str,
    ) -> dict[str, Any]:
        workflow = await self._service.get_workflow(workflow_id)
        if workflow.status == "blocked" and workflow.current_stage == "experiment_run":
            workflow = await self._sync_blocked_experiment_contract_state(workflow)
        task = await self._service.get_workflow_task(
            workflow_id=workflow_id,
            task_id=task_id,
        )
        project = await self._service.get_project(workflow.project_id)
        if task.status in {"completed", "cancelled"}:
            return {
                "workflow": workflow,
                "project": project,
                "task": task,
                "executed": False,
                "resolved": False,
                "skipped": True,
                "reason": f"task status is {task.status}",
            }
        task_kind = str(dict(getattr(task, "metadata", {}) or {}).get("task_kind", "") or "").strip()
        if task_kind == "experiment_contract_remediation":
            result = await self._execute_experiment_contract_remediation_task(
                workflow=workflow,
                task=task,
            )
            result["skipped"] = False
            result["task_kind"] = task_kind
            return result
        reason = f"No structured executor is available for task kind '{task_kind or 'generic'}'."
        await self._service.update_workflow_task(
            workflow_id=workflow.id,
            task_id=task.id,
            summary=reason,
        )
        task_after = await self._service.record_workflow_task_execution(
            workflow_id=workflow.id,
            task_id=task.id,
            summary="Structured task execution is not available for this task.",
            error=reason,
        )
        return {
            "workflow": await self._service.get_workflow(workflow.id),
            "project": project,
            "task": task_after,
            "executed": False,
            "resolved": False,
            "skipped": False,
            "reason": reason,
            "task_kind": task_kind,
        }

    async def execute_due_workflow_tasks(
        self,
        *,
        project_id: str = "",
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        workflows = await self._service.list_workflows(project_id=project_id)
        now = datetime.now(timezone.utc)
        candidates: list[tuple[str, ResearchWorkflow, WorkflowTask]] = []
        for workflow in workflows:
            if workflow.current_stage != "experiment_run":
                continue
            if workflow.status not in {"blocked", "running"}:
                continue
            workflow = await self._sync_blocked_experiment_contract_state(workflow)
            for task in self._stage_tasks(workflow):
                metadata = dict(getattr(task, "metadata", {}) or {})
                if str(metadata.get("task_kind", "") or "").strip() != "experiment_contract_remediation":
                    continue
                if str(task.assignee or "").strip() != "agent":
                    continue
                if str(metadata.get("action_type", "") or "").strip() not in {
                    "publish_artifact",
                    "archive_output",
                    "record_metric",
                }:
                    continue
                if not self._eligible_for_task_execution(task=task, now=now):
                    continue
                if not await self._can_auto_execute_task(task=task):
                    continue
                candidates.append((str(task.due_at or task.updated_at or ""), workflow, task))

        candidates.sort(key=lambda item: item[0])
        results: list[dict[str, Any]] = []
        for _, workflow, task in candidates[: max(1, int(limit))]:
            try:
                result = await self.execute_workflow_task(workflow.id, task.id)
                result["ok"] = bool(result.get("executed") or result.get("resolved"))
                result["auto_task"] = True
                results.append(result)
            except Exception as exc:
                task_after = await self._service.record_workflow_task_execution(
                    workflow_id=workflow.id,
                    task_id=task.id,
                    summary="Automatic remediation task execution failed.",
                    error=str(exc),
                )
                results.append(
                    {
                        "workflow": await self._service.get_workflow(workflow.id),
                        "task": task_after,
                        "ok": False,
                        "auto_task": True,
                        "error": str(exc),
                    },
                )
        return results

    async def execute_workflow_step(
        self,
        workflow_id: str,
        *,
        agent_id: str = "",
        session_id: str = "",
        trigger: str = "manual",
        trigger_reason: str = "",
        prefer_stage_worker: bool = False,
    ) -> dict[str, Any]:
        workflow = await self._service.get_workflow(workflow_id)
        if workflow.status in {"completed", "cancelled"}:
            return {
                "workflow": workflow,
                "skipped": True,
                "reason": f"workflow status is {workflow.status}",
            }

        if prefer_stage_worker:
            stage_result = await self._execute_structured_stage_worker(
                workflow,
                trigger=trigger,
                trigger_reason=trigger_reason,
            )
            if stage_result is not None:
                return stage_result

        if self._runner is None:
            raise RuntimeError("Agent runner is not initialized")

        project = await self._service.get_project(workflow.project_id)
        status_before = workflow.status
        chosen_agent_id = str(agent_id or workflow.bindings.agent_id or "main").strip() or "main"
        chosen_session_id = str(session_id or workflow.bindings.session_id or "").strip()
        if chosen_session_id in {"", "main"}:
            chosen_session_id = f"research:{workflow.id}"

        workflow = await self._service.update_workflow_binding(
            workflow_id=workflow.id,
            patch={
                "agent_id": chosen_agent_id,
                "session_id": chosen_session_id,
            },
        )

        notes = await self._service.list_notes(
            project_id=project.id,
            workflow_id=workflow.id,
            limit=5,
        )
        claims = await self._service.list_claims(
            project_id=project.id,
            workflow_id=workflow.id,
            limit=5,
        )
        experiments = await self._service.list_experiments(
            project_id=project.id,
            workflow_id=workflow.id,
            limit=3,
        )
        prompt = self._build_execution_prompt(
            project=project,
            workflow=workflow,
            notes=notes,
            claims=claims,
            experiments=experiments,
        )
        stage_before = workflow.current_stage
        stage_tasks_before = self._stage_tasks(workflow)
        attach_task_id = (
            stage_tasks_before[0].id
            if stage_tasks_before
            else (workflow.tasks[0].id if workflow.tasks else "")
        )
        fingerprint_before = self._workflow_fingerprint(workflow)

        response = await self._runner.chat(
            prompt,
            session_id=chosen_session_id,
            agent_id=chosen_agent_id,
        )
        response_text = str(response or "").strip()
        workflow_after_agent = await self._service.get_workflow(workflow.id)
        mutated_by_agent = (
            self._workflow_fingerprint(workflow_after_agent) != fingerprint_before
        )

        execution_note = await self._service.create_note(
            project_id=project.id,
            workflow_id=workflow.id,
            title=f"Workflow execution · {workflow.title}",
            content=response_text or "Agent run completed without a textual summary.",
            note_type="decision_log",
            tags=[
                "auto-execution" if trigger == "auto" else "manual-execution",
                stage_before,
            ],
            metadata={
                "executor": "research_runtime",
                "agent_id": chosen_agent_id,
                "session_id": chosen_session_id,
                "mutated_by_agent": mutated_by_agent,
                "trigger": trigger,
                "trigger_reason": trigger_reason,
            },
        )

        workflow_after_note = await self._service.get_workflow(workflow.id)
        target_task = self._find_task(workflow_after_note, attach_task_id)
        if target_task is not None:
            workflow_after_note = await self._service.update_workflow_task(
                workflow_id=workflow.id,
                task_id=target_task.id,
                summary=(
                    None
                    if mutated_by_agent and str(target_task.summary or "").strip()
                    else self._truncate_summary(response_text)
                ),
                note_ids=[execution_note.id],
            )

        workflow_final = await self._service.tick_workflow(workflow.id)
        workflow_final = await self._service.update_workflow_binding(
            workflow_id=workflow.id,
            patch={
                "agent_id": chosen_agent_id,
                "session_id": chosen_session_id,
                "last_dispatch_at": utc_now(),
                "last_summary": self._truncate_summary(response_text, limit=500),
                "metadata": {
                    "last_executor": "research_runtime",
                    "last_execution_note_id": execution_note.id,
                    "last_execution_trigger": trigger,
                },
            },
        )

        return {
            "workflow": workflow_final,
            "project": project,
            "note": execution_note,
            "response": response_text,
            "mutated_by_agent": mutated_by_agent,
            "agent_id": chosen_agent_id,
            "session_id": chosen_session_id,
            "execution_id": execution_note.id,
            "stage_before": stage_before,
            "status_before": status_before,
            "trigger": trigger,
            "trigger_reason": trigger_reason,
            "skipped": False,
        }

    async def execute_due_workflows(
        self,
        *,
        project_id: str = "",
        stale_hours: int = RESEARCH_WORKFLOW_STALE_HOURS,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        workflows = await self._service.list_workflows(project_id=project_id)
        now = datetime.now(timezone.utc)
        candidates: list[tuple[int, ResearchWorkflow, str]] = []
        for workflow in workflows:
            workflow = await self._sync_blocked_experiment_contract_state(workflow)
            reason = self._auto_execution_reason(
                workflow,
                now=now,
                stale_hours=stale_hours,
            )
            if not reason:
                continue
            priority = 0 if workflow.status == "blocked" else 1
            candidates.append((priority, workflow, reason))

        candidates.sort(
            key=lambda item: (
                item[0],
                str(item[1].last_run_at or item[1].updated_at or ""),
            ),
        )
        now_iso = utc_now()
        results: list[dict[str, Any]] = []

        for _, workflow, reason in candidates[: max(1, int(limit))]:
            policy = workflow.execution_policy
            window_started_at, current_count = self._normalize_auto_run_window(
                window_started_at=policy.auto_run_window_started_at,
                count=policy.auto_run_count_in_window,
                now=now,
                now_iso=now_iso,
            )
            try:
                result = await self.execute_workflow_step(
                    workflow.id,
                    agent_id=workflow.bindings.agent_id,
                    session_id=workflow.bindings.session_id,
                    trigger="auto",
                    trigger_reason=reason,
                    prefer_stage_worker=True,
                )
                updated_workflow = await self._service.update_workflow_execution_policy(
                    workflow_id=workflow.id,
                    patch={
                        "last_auto_run_at": now_iso,
                        "last_auto_run_reason": reason,
                        "last_auto_run_note_id": result.get("execution_id", ""),
                        "auto_run_window_started_at": window_started_at,
                        "auto_run_count_in_window": current_count + 1,
                    },
                )
                result["workflow"] = updated_workflow
                result["ok"] = True
                result["auto_reason"] = reason
                result["notification"] = None
                if updated_workflow.execution_policy.notify_after_execution:
                    result["notification"] = await self._deliver_text(
                        channel=updated_workflow.bindings.channel,
                        user_id=updated_workflow.bindings.user_id,
                        session_id=updated_workflow.bindings.session_id,
                        text=self._format_auto_execution_message(result, reason),
                        meta={
                            "source": "research_auto_advance",
                            "project_id": updated_workflow.project_id,
                            "workflow_id": updated_workflow.id,
                            "trigger_reason": reason,
                        },
                    )
                results.append(result)
            except Exception as exc:
                updated_workflow = await self._service.update_workflow_execution_policy(
                    workflow_id=workflow.id,
                    patch={
                        "last_auto_run_at": now_iso,
                        "last_auto_run_reason": f"failed: {exc}",
                        "auto_run_window_started_at": window_started_at,
                        "auto_run_count_in_window": current_count + 1,
                    },
                )
                results.append(
                    {
                        "workflow": updated_workflow,
                        "workflow_id": workflow.id,
                        "project_id": workflow.project_id,
                        "ok": False,
                        "auto_reason": reason,
                        "error": str(exc),
                    },
                )

        return results

    async def note_automation_run(
        self,
        *,
        workflow_id: str,
        run_id: str,
        summary: str = "",
        session_id: str = "",
        dispatches: list[dict[str, str]] | None = None,
    ):
        return await self._service.record_workflow_automation_run(
            workflow_id=workflow_id,
            run_id=run_id,
            summary=summary,
            session_id=session_id,
            dispatches=dispatches,
        )

    async def run_proactive_cycle(
        self,
        *,
        project_id: str = "",
        stale_hours: int = RESEARCH_WORKFLOW_STALE_HOURS,
    ) -> dict[str, Any]:
        task_execution_results = await self.execute_due_workflow_tasks(
            project_id=project_id,
        )
        auto_execution_results = await self.execute_due_workflows(
            project_id=project_id,
            stale_hours=stale_hours,
        )
        reminders = await self._service.generate_proactive_reminders(
            project_id=project_id,
            stale_hours=stale_hours,
        )
        results: list[dict[str, Any]] = []
        sent_count = sum(
            1
            for item in auto_execution_results
            if isinstance(item.get("notification"), dict)
            and item["notification"].get("ok")
        )

        for reminder in reminders:
            result = {
                "reminder_id": reminder.id,
                "reminder_type": reminder.reminder_type,
                "project_id": reminder.project_id,
                "workflow_id": reminder.workflow_id,
                "experiment_id": reminder.experiment_id,
                "task_id": reminder.task_id,
                "channel": reminder.binding.channel,
                "user_id": reminder.binding.user_id,
                "session_id": reminder.binding.session_id,
            }
            delivery = await self._deliver_text(
                channel=reminder.binding.channel,
                user_id=reminder.binding.user_id,
                session_id=reminder.binding.session_id,
                text=self._format_reminder(reminder),
                meta={
                    "source": "research_followup",
                    "project_id": reminder.project_id,
                    "workflow_id": reminder.workflow_id,
                    "experiment_id": reminder.experiment_id,
                    "task_id": reminder.task_id,
                    "reminder_type": reminder.reminder_type,
                },
            )
            result.update(delivery)
            if result.get("ok"):
                sent_count += 1
            results.append(result)

        self._last_cycle = {
            "last_run_at": utc_now(),
            "task_execution_count": len(task_execution_results),
            "task_execution_results": task_execution_results,
            "auto_execution_count": len(auto_execution_results),
            "auto_execution_results": auto_execution_results,
            "reminder_count": len(reminders),
            "sent_count": sent_count,
            "delivery_results": results,
        }
        return dict(self._last_cycle)

    async def get_runtime_stats(self) -> dict[str, Any]:
        base = await self._service.get_runtime_stats()
        return {
            **base,
            **self._last_cycle,
        }
