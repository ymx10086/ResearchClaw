"""Application service for project-centric research workflows."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from .models import (
    ArtifactType,
    EvidenceSource,
    EvidenceType,
    ExperimentEvent,
    ExperimentExecutionCatalogEntry,
    ExperimentExecutionBinding,
    ExperimentRunnerProfile,
    ExperimentRunnerRule,
    ExperimentRunnerTemplate,
    ExperimentRun,
    ProactiveReminder,
    ProjectPaperWatch,
    ResultBundleSchemaDefinition,
    ResearchArtifact,
    ResearchClaim,
    ResearchEvidence,
    ResearchNote,
    ResearchProject,
    ResearchState,
    ResearchWorkflow,
    WorkflowExecutionPolicy,
    WORKFLOW_STAGES,
    WorkflowBinding,
    WorkflowStageName,
    WorkflowStageState,
    WorkflowTask,
    utc_now,
)
from .store import JsonResearchStore


_DEFAULT_STAGE_TASKS: dict[str, tuple[str, str]] = {
    "literature_search": (
        "Search and shortlist core papers",
        "Collect the most relevant papers, benchmarks, and citation anchors.",
    ),
    "paper_reading": (
        "Read prioritized papers",
        "Extract methods, limitations, assumptions, and reusable evidence.",
    ),
    "note_synthesis": (
        "Synthesize notes into themes",
        "Turn raw reading notes into themes, gaps, tensions, and open questions.",
    ),
    "hypothesis_queue": (
        "Queue candidate hypotheses",
        "Rank plausible hypotheses or research directions with expected value.",
    ),
    "experiment_plan": (
        "Define an experiment plan",
        "Specify baselines, ablations, datasets, metrics, and exit criteria.",
    ),
    "experiment_run": (
        "Run or collect experiments",
        "Execute planned experiments and archive outputs for comparison.",
    ),
    "result_analysis": (
        "Analyze outcomes",
        "Interpret metrics, figures, and failure modes into reusable findings.",
    ),
    "writing_tasks": (
        "Draft writing tasks",
        "Convert validated findings into outlines, sections, and revision todos.",
    ),
    "review_and_followup": (
        "Review open risks and follow-ups",
        "Check unresolved claims, next actions, and long-running follow-up items.",
    ),
}


def _append_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def _remove_empty_strings(items: Iterable[str]) -> list[str]:
    return [str(item).strip() for item in items if str(item).strip()]


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _hours_since(value: str | None, *, now: datetime) -> float | None:
    parsed = _parse_iso(value)
    if parsed is None:
        return None
    return max(0.0, (now - parsed).total_seconds() / 3600.0)


def _stringify_metadata(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:
        return str(value)


def _artifact_type_from_path(path: str) -> ArtifactType:
    suffix = Path(path).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".svg", ".webp", ".pdf"}:
        return "generated_figure"
    if suffix in {".csv", ".tsv", ".xlsx", ".xls", ".json"}:
        return "generated_table"
    if suffix in {".md", ".txt"}:
        return "summary"
    return "experiment_result"


class ResearchService:
    """Structured state management for research projects and workflows."""

    def __init__(self, store: JsonResearchStore | None = None) -> None:
        self._store = store or JsonResearchStore()

    @property
    def path(self) -> Path:
        return self._store.path

    async def load_state(self) -> ResearchState:
        return await self._store.load()

    async def save_state(self, state: ResearchState) -> None:
        await self._store.save(state)

    # ---- generic find helpers ----

    @staticmethod
    def _project(state: ResearchState, project_id: str) -> ResearchProject:
        for item in state.projects:
            if item.id == project_id:
                return item
        raise ValueError(f"Unknown project: {project_id}")

    @staticmethod
    def _workflow(state: ResearchState, workflow_id: str) -> ResearchWorkflow:
        for item in state.workflows:
            if item.id == workflow_id:
                return item
        raise ValueError(f"Unknown workflow: {workflow_id}")

    @staticmethod
    def _claim(state: ResearchState, claim_id: str) -> ResearchClaim:
        for item in state.claims:
            if item.id == claim_id:
                return item
        raise ValueError(f"Unknown claim: {claim_id}")

    @staticmethod
    def _note(state: ResearchState, note_id: str) -> ResearchNote:
        for item in state.notes:
            if item.id == note_id:
                return item
        raise ValueError(f"Unknown note: {note_id}")

    @staticmethod
    def _experiment(state: ResearchState, experiment_id: str) -> ExperimentRun:
        for item in state.experiments:
            if item.id == experiment_id:
                return item
        raise ValueError(f"Unknown experiment: {experiment_id}")

    @staticmethod
    def _artifact(state: ResearchState, artifact_id: str) -> ResearchArtifact:
        for item in state.artifacts:
            if item.id == artifact_id:
                return item
        raise ValueError(f"Unknown artifact: {artifact_id}")

    @staticmethod
    def _workflow_stage(
        workflow: ResearchWorkflow,
        stage_name: WorkflowStageName,
    ) -> WorkflowStageState:
        for stage in workflow.stages:
            if stage.name == stage_name:
                return stage
        raise ValueError(f"Unknown workflow stage: {stage_name}")

    @staticmethod
    def _workflow_task(
        workflow: ResearchWorkflow,
        task_id: str,
    ) -> WorkflowTask:
        for task in workflow.tasks:
            if task.id == task_id:
                return task
        raise ValueError(f"Unknown workflow task: {task_id}")

    @staticmethod
    def _touch(item: Any, *, now: str | None = None) -> None:
        if hasattr(item, "updated_at"):
            setattr(item, "updated_at", now or utc_now())

    @staticmethod
    def _clone_binding(binding: WorkflowBinding) -> WorkflowBinding:
        return WorkflowBinding.model_validate(binding.model_dump(mode="json"))

    def _merge_binding(
        self,
        *,
        base: WorkflowBinding,
        patch: dict[str, Any] | None,
    ) -> WorkflowBinding:
        if not patch:
            return self._clone_binding(base)
        payload = base.model_dump(mode="json")
        for key, value in patch.items():
            if value is None:
                continue
            if key == "metadata" and isinstance(value, dict):
                merged_metadata = dict(payload.get("metadata") or {})
                merged_metadata.update(value)
                payload[key] = merged_metadata
                continue
            payload[key] = value
        return WorkflowBinding.model_validate(payload)

    def _merge_execution_policy(
        self,
        *,
        base: WorkflowExecutionPolicy,
        patch: dict[str, Any] | None,
    ) -> WorkflowExecutionPolicy:
        if not patch:
            return WorkflowExecutionPolicy.model_validate(
                base.model_dump(mode="json"),
            )
        payload = base.model_dump(mode="json")
        for key, value in patch.items():
            if value is None:
                continue
            payload[key] = value
        return WorkflowExecutionPolicy.model_validate(payload)

    @staticmethod
    def _clone_experiment_runner(
        profile: ExperimentRunnerProfile,
    ) -> ExperimentRunnerProfile:
        return ExperimentRunnerProfile.model_validate(
            profile.model_dump(mode="json"),
        )

    def _merge_runner_template(
        self,
        *,
        base: ExperimentRunnerTemplate,
        patch: dict[str, Any] | None,
    ) -> ExperimentRunnerTemplate:
        if not patch:
            return ExperimentRunnerTemplate.model_validate(
                base.model_dump(mode="json"),
            )
        payload = base.model_dump(mode="json")
        for key, value in patch.items():
            if value is None:
                continue
            if key in {"metadata", "environment", "parameter_overrides", "input_data_overrides"} and isinstance(value, dict):
                merged_value = dict(payload.get(key) or {})
                merged_value.update(value)
                payload[key] = merged_value
                continue
            if key == "command" and isinstance(value, list):
                payload[key] = _remove_empty_strings(value)
                continue
            payload[key] = value
        return ExperimentRunnerTemplate.model_validate(payload)

    @staticmethod
    def _merge_execution_catalog(
        *,
        base: list[ExperimentExecutionCatalogEntry],
        patch: list[dict[str, Any]] | None,
    ) -> list[ExperimentExecutionCatalogEntry]:
        if patch is None:
            return [
                ExperimentExecutionCatalogEntry.model_validate(
                    item.model_dump(mode="json"),
                )
                for item in base
            ]
        return [
            ExperimentExecutionCatalogEntry.model_validate(item)
            for item in patch
            if isinstance(item, dict)
        ]

    @staticmethod
    def _merge_result_bundle_schemas(
        *,
        base: list[ResultBundleSchemaDefinition],
        patch: list[dict[str, Any]] | None,
    ) -> list[ResultBundleSchemaDefinition]:
        if patch is None:
            return [
                ResultBundleSchemaDefinition.model_validate(
                    item.model_dump(mode="json"),
                )
                for item in base
            ]
        return [
            ResultBundleSchemaDefinition.model_validate(item)
            for item in patch
            if isinstance(item, dict)
        ]

    @staticmethod
    def _merge_contract_dicts(*contracts: dict[str, Any] | None) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for contract in contracts:
            if not isinstance(contract, dict):
                continue
            for key in ("required_metrics", "required_outputs", "required_artifact_types"):
                values = _remove_empty_strings(contract.get(key, []))
                if not values:
                    continue
                merged = list(payload.get(key, []) or [])
                for value in values:
                    _append_unique(merged, value)
                payload[key] = merged
            for key, value in contract.items():
                if key in {"required_metrics", "required_outputs", "required_artifact_types"}:
                    continue
                if value is None:
                    continue
                payload[key] = value
        return payload

    @staticmethod
    def _result_bundle_schema_contract(
        schema: ResultBundleSchemaDefinition | None,
    ) -> dict[str, Any]:
        if schema is None:
            return {}
        return {
            key: values
            for key, values in {
                "required_metrics": _remove_empty_strings(schema.required_metrics),
                "required_outputs": _remove_empty_strings(schema.required_outputs),
                "required_artifact_types": _remove_empty_strings(
                    schema.required_artifact_types,
                ),
            }.items()
            if values
        }

    def _project_result_bundle_schema(
        self,
        state: ResearchState,
        *,
        project_id: str,
        schema_name: str,
    ) -> ResultBundleSchemaDefinition | None:
        normalized = str(schema_name or "").strip()
        if not normalized:
            return None
        project = self._project(state, project_id)
        for item in list(getattr(project, "result_bundle_schemas", []) or []):
            if str(getattr(item, "name", "") or "").strip() == normalized:
                return item
        return None

    def _merge_runner_profile(
        self,
        *,
        base: ExperimentRunnerProfile,
        patch: dict[str, Any] | None,
    ) -> ExperimentRunnerProfile:
        if not patch:
            return self._clone_experiment_runner(base)
        payload = base.model_dump(mode="json")
        for key, value in patch.items():
            if value is None:
                continue
            if key == "default" and isinstance(value, dict):
                payload["default"] = self._merge_runner_template(
                    base=base.default,
                    patch=value,
                ).model_dump(mode="json")
                continue
            if key == "kind_overrides":
                if not isinstance(value, dict):
                    continue
                existing = {
                    name: dict(template)
                    for name, template in base.kind_overrides.items()
                }
                if not value:
                    payload[key] = {}
                    continue
                for kind, template_patch in value.items():
                    normalized_kind = str(kind or "").strip()
                    if not normalized_kind:
                        continue
                    if template_patch is None:
                        existing.pop(normalized_kind, None)
                        continue
                    if not isinstance(template_patch, dict):
                        continue
                    merged_patch = dict(existing.get(normalized_kind) or {})
                    merged_patch.update(template_patch)
                    validated = ExperimentRunnerTemplate.model_validate(merged_patch)
                    existing[normalized_kind] = validated.model_dump(
                        mode="json",
                        exclude_defaults=True,
                    )
                payload[key] = existing
                continue
            if key == "rules" and isinstance(value, list):
                payload[key] = [
                    ExperimentRunnerRule.model_validate(item).model_dump(mode="json")
                    for item in value
                    if isinstance(item, dict)
                ]
                continue
            payload[key] = value
        return ExperimentRunnerProfile.model_validate(payload)

    def _merge_experiment_execution(
        self,
        *,
        base: ExperimentExecutionBinding,
        patch: dict[str, Any] | None,
    ) -> ExperimentExecutionBinding:
        if not patch:
            return ExperimentExecutionBinding.model_validate(
                base.model_dump(mode="json"),
            )
        payload = base.model_dump(mode="json")
        for key, value in patch.items():
            if value is None:
                continue
            if key in {"metadata", "environment"} and isinstance(value, dict):
                merged_value = dict(payload.get(key) or {})
                merged_value.update(value)
                payload[key] = merged_value
                continue
            payload[key] = value
        return ExperimentExecutionBinding.model_validate(payload)

    @staticmethod
    def _ensure_workflow_scaffold(workflow: ResearchWorkflow) -> None:
        if workflow.stages:
            return
        workflow.stages = [WorkflowStageState(name=stage) for stage in WORKFLOW_STAGES]

    @staticmethod
    def _stage_task_list(
        workflow: ResearchWorkflow,
        stage_name: WorkflowStageName,
    ) -> list[WorkflowTask]:
        return [task for task in workflow.tasks if task.stage == stage_name]

    def _seed_stage_task(self, workflow: ResearchWorkflow) -> WorkflowTask:
        stage = self._workflow_stage(workflow, workflow.current_stage)
        existing = self._stage_task_list(workflow, workflow.current_stage)
        if existing:
            for task in existing:
                _append_unique(stage.task_ids, task.id)
            return existing[0]

        title, description = _DEFAULT_STAGE_TASKS.get(
            workflow.current_stage,
            ("Advance workflow stage", "Continue the current workflow stage."),
        )
        task = WorkflowTask(
            stage=workflow.current_stage,
            title=title,
            description=description,
            status="pending",
        )
        workflow.tasks.append(task)
        _append_unique(stage.task_ids, task.id)
        stage.updated_at = utc_now()
        return task

    def _recompute_workflow(
        self,
        workflow: ResearchWorkflow,
        *,
        now: str | None = None,
    ) -> ResearchWorkflow:
        current_time = now or utc_now()
        self._ensure_workflow_scaffold(workflow)
        stage = self._workflow_stage(workflow, workflow.current_stage)
        stage_tasks = self._stage_task_list(workflow, workflow.current_stage)
        for task in stage_tasks:
            _append_unique(stage.task_ids, task.id)

        if workflow.status in {"cancelled", "completed"}:
            return workflow

        if workflow.status == "draft":
            workflow.status = "queued"

        if workflow.status == "paused":
            stage.status = "pending"
            return workflow

        if not stage.started_at:
            stage.started_at = current_time

        if not workflow.started_at:
            workflow.started_at = current_time

        if not stage_tasks:
            self._seed_stage_task(workflow)
            stage_tasks = self._stage_task_list(workflow, workflow.current_stage)

        failed = [task for task in stage_tasks if task.status == "failed"]
        blocked = [task for task in stage_tasks if task.status == "blocked"]
        completed = [
            task for task in stage_tasks
            if task.status in {"completed", "cancelled"}
        ]

        if failed:
            workflow.status = "blocked"
            workflow.error = failed[-1].summary or f"Task failed: {failed[-1].title}"
            stage.status = "blocked"
            stage.blocked_reason = workflow.error
            stage.updated_at = current_time
            workflow.last_run_at = current_time
            self._touch(workflow, now=current_time)
            return workflow

        if blocked:
            workflow.status = "blocked"
            workflow.error = blocked[-1].summary or f"Task blocked: {blocked[-1].title}"
            stage.status = "blocked"
            stage.blocked_reason = workflow.error
            stage.updated_at = current_time
            workflow.last_run_at = current_time
            self._touch(workflow, now=current_time)
            return workflow

        if stage_tasks and len(completed) == len(stage_tasks):
            stage.status = "completed"
            stage.completed_at = current_time
            stage.updated_at = current_time
            workflow.last_transition_at = current_time
            current_index = WORKFLOW_STAGES.index(workflow.current_stage)
            if current_index == len(WORKFLOW_STAGES) - 1:
                workflow.status = "completed"
                workflow.completed_at = current_time
                workflow.last_run_at = current_time
                self._touch(workflow, now=current_time)
                return workflow

            next_stage = WORKFLOW_STAGES[current_index + 1]
            workflow.current_stage = next_stage  # type: ignore[assignment]
            workflow.status = "running"
            workflow.error = ""
            next_state = self._workflow_stage(workflow, workflow.current_stage)
            if next_state.status == "pending":
                next_state.status = "running"
            if not next_state.started_at:
                next_state.started_at = current_time
            next_state.updated_at = current_time
            self._seed_stage_task(workflow)
            workflow.last_run_at = current_time
            self._touch(workflow, now=current_time)
            return workflow

        stage.status = "running"
        stage.updated_at = current_time
        workflow.status = "running"
        workflow.error = ""
        workflow.last_run_at = current_time
        self._touch(workflow, now=current_time)
        return workflow

    @staticmethod
    def _note_matches(
        note: ResearchNote,
        *,
        query: str = "",
        note_type: str = "",
        tags: list[str] | None = None,
        project_id: str = "",
        workflow_id: str = "",
        claim_id: str = "",
        experiment_id: str = "",
    ) -> bool:
        if project_id and note.project_id != project_id:
            return False
        if workflow_id and note.workflow_id != workflow_id:
            return False
        if claim_id and claim_id not in note.claim_ids:
            return False
        if experiment_id and experiment_id not in note.experiment_ids:
            return False
        if note_type and note.note_type != note_type:
            return False
        wanted_tags = set(_remove_empty_strings(tags or []))
        if wanted_tags and not wanted_tags.intersection(note.tags):
            return False
        if query:
            haystack = " ".join(
                [
                    note.title,
                    note.content,
                    " ".join(note.tags),
                    " ".join(note.paper_refs),
                    _stringify_metadata(note.metadata),
                ],
            ).lower()
            if query.lower() not in haystack:
                return False
        return True

    @staticmethod
    def _project_binding(
        project: ResearchProject,
        workflow: ResearchWorkflow | None = None,
    ) -> WorkflowBinding:
        if workflow is not None:
            return WorkflowBinding.model_validate(
                workflow.bindings.model_dump(mode="json"),
            )
        return WorkflowBinding.model_validate(
            project.default_binding.model_dump(mode="json"),
        )

    def _add_artifact_to_state(
        self,
        state: ResearchState,
        *,
        project_id: str,
        title: str,
        artifact_type: ArtifactType,
        workflow_id: str = "",
        description: str = "",
        path: str = "",
        uri: str = "",
        source_type: str = "",
        source_id: str = "",
        experiment_id: str = "",
        note_ids: list[str] | None = None,
        claim_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ResearchArtifact:
        artifact = ResearchArtifact(
            project_id=project_id,
            workflow_id=workflow_id,
            title=title,
            artifact_type=artifact_type,
            description=description,
            path=path,
            uri=uri,
            source_type=source_type,
            source_id=source_id,
            experiment_id=experiment_id,
            note_ids=_remove_empty_strings(note_ids or []),
            claim_ids=_remove_empty_strings(claim_ids or []),
            metadata=dict(metadata or {}),
        )
        state.artifacts.append(artifact)

        project = self._project(state, project_id)
        _append_unique(project.artifact_ids, artifact.id)
        self._touch(project)

        if workflow_id:
            workflow = self._workflow(state, workflow_id)
            _append_unique(workflow.artifact_ids, artifact.id)
            stage = self._workflow_stage(workflow, workflow.current_stage)
            _append_unique(stage.artifact_ids, artifact.id)
            self._touch(workflow)
            stage.updated_at = utc_now()

        if experiment_id:
            experiment = self._experiment(state, experiment_id)
            _append_unique(experiment.artifact_ids, artifact.id)

        for note_id in artifact.note_ids:
            note = self._note(state, note_id)
            _append_unique(note.artifact_ids, artifact.id)
            self._touch(note)

        for claim_id in artifact.claim_ids:
            claim = self._claim(state, claim_id)
            _append_unique(claim.artifact_ids, artifact.id)
            self._touch(claim)

        return artifact

    def _add_evidence_to_state(
        self,
        state: ResearchState,
        *,
        project_id: str,
        evidence_type: EvidenceType,
        summary: str,
        claim_ids: list[str],
        source: EvidenceSource,
        workflow_id: str = "",
        artifact_id: str = "",
        note_id: str = "",
        experiment_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ResearchEvidence:
        evidence = ResearchEvidence(
            project_id=project_id,
            evidence_type=evidence_type,
            summary=summary,
            claim_ids=_remove_empty_strings(claim_ids),
            workflow_id=workflow_id,
            artifact_id=artifact_id,
            note_id=note_id,
            experiment_id=experiment_id,
            source=source,
            metadata=dict(metadata or {}),
        )
        state.evidences.append(evidence)

        for claim_id in evidence.claim_ids:
            claim = self._claim(state, claim_id)
            _append_unique(claim.evidence_ids, evidence.id)
            self._touch(claim)

        if artifact_id:
            artifact = self._artifact(state, artifact_id)
            _append_unique(artifact.evidence_ids, evidence.id)
            self._touch(artifact)

        if note_id:
            note = self._note(state, note_id)
            _append_unique(note.evidence_ids, evidence.id)
            self._touch(note)

        if experiment_id:
            experiment = self._experiment(state, experiment_id)
            _append_unique(experiment.evidence_ids, evidence.id)
            self._touch(experiment)

        return evidence

    def _add_experiment_event_to_state(
        self,
        state: ResearchState,
        *,
        experiment: ExperimentRun,
        event_type: str,
        summary: str,
        status: str = "",
        metrics: dict[str, Any] | None = None,
        output_files: list[str] | None = None,
        note_ids: list[str] | None = None,
        artifact_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExperimentEvent:
        event = ExperimentEvent(
            experiment_id=experiment.id,
            project_id=experiment.project_id,
            workflow_id=experiment.workflow_id,
            event_type=event_type,  # type: ignore[arg-type]
            summary=summary,
            status=status or experiment.status,
            metrics=dict(metrics or {}),
            output_files=_remove_empty_strings(output_files or []),
            note_ids=_remove_empty_strings(note_ids or []),
            artifact_ids=_remove_empty_strings(artifact_ids or []),
            metadata=dict(metadata or {}),
        )
        state.experiment_events.append(event)
        return event

    def _project_recent_items(
        self,
        items: list[Any],
        ids: list[str],
        *,
        limit: int = 5,
    ) -> list[Any]:
        wanted = set(ids)
        filtered = [item for item in items if getattr(item, "id", "") in wanted]
        filtered.sort(
            key=lambda item: str(getattr(item, "updated_at", "") or getattr(item, "created_at", "")),
            reverse=True,
        )
        return filtered[:limit]

    # ---- project APIs ----

    async def list_projects(self) -> list[ResearchProject]:
        state = await self.load_state()
        return list(state.projects)

    async def create_project(
        self,
        *,
        name: str,
        description: str = "",
        tags: list[str] | None = None,
        default_binding: dict[str, Any] | None = None,
        execution_catalog: list[dict[str, Any]] | None = None,
        result_bundle_schemas: list[dict[str, Any]] | None = None,
        default_experiment_runner: dict[str, Any] | None = None,
        paper_watches: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ResearchProject:
        state = await self.load_state()
        project = ResearchProject(
            name=name,
            description=description,
            tags=_remove_empty_strings(tags or []),
            default_binding=self._merge_binding(
                base=WorkflowBinding(),
                patch=default_binding,
            ),
            execution_catalog=self._merge_execution_catalog(
                base=[],
                patch=execution_catalog,
            ),
            result_bundle_schemas=self._merge_result_bundle_schemas(
                base=[],
                patch=result_bundle_schemas,
            ),
            default_experiment_runner=self._merge_runner_profile(
                base=ExperimentRunnerProfile(),
                patch=default_experiment_runner,
            ),
            paper_watches=[
                ProjectPaperWatch.model_validate(item)
                for item in (paper_watches or [])
            ],
            metadata=dict(metadata or {}),
        )
        state.projects.append(project)
        await self.save_state(state)
        return project

    async def get_project(self, project_id: str) -> ResearchProject:
        state = await self.load_state()
        return self._project(state, project_id)

    async def get_project_result_bundle_schema(
        self,
        *,
        project_id: str,
        schema_name: str,
    ) -> ResultBundleSchemaDefinition | None:
        state = await self.load_state()
        return self._project_result_bundle_schema(
            state,
            project_id=project_id,
            schema_name=schema_name,
        )

    async def update_project(
        self,
        *,
        project_id: str,
        description: str | None = None,
        status: str | None = None,
        tags: list[str] | None = None,
        default_binding: dict[str, Any] | None = None,
        execution_catalog: list[dict[str, Any]] | None = None,
        result_bundle_schemas: list[dict[str, Any]] | None = None,
        default_experiment_runner: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ResearchProject:
        state = await self.load_state()
        project = self._project(state, project_id)
        if description is not None:
            project.description = description
        if status is not None:
            project.status = status  # type: ignore[assignment]
        if tags is not None:
            project.tags = _remove_empty_strings(tags)
        if default_binding:
            project.default_binding = self._merge_binding(
                base=project.default_binding,
                patch=default_binding,
            )
        if execution_catalog is not None:
            project.execution_catalog = self._merge_execution_catalog(
                base=project.execution_catalog,
                patch=execution_catalog,
            )
        if result_bundle_schemas is not None:
            project.result_bundle_schemas = self._merge_result_bundle_schemas(
                base=project.result_bundle_schemas,
                patch=result_bundle_schemas,
            )
        if default_experiment_runner is not None:
            project.default_experiment_runner = self._merge_runner_profile(
                base=project.default_experiment_runner,
                patch=default_experiment_runner,
            )
        if metadata:
            merged_metadata = dict(project.metadata)
            merged_metadata.update(dict(metadata))
            project.metadata = merged_metadata
        self._touch(project)
        await self.save_state(state)
        return project

    async def add_project_paper_watch(
        self,
        *,
        project_id: str,
        query: str,
        source: str = "arxiv",
        max_results: int = 5,
        check_every_hours: int = 12,
    ) -> ResearchProject:
        state = await self.load_state()
        project = self._project(state, project_id)
        project.paper_watches.append(
            ProjectPaperWatch(
                query=query,
                source="semantic_scholar" if source == "semantic_scholar" else "arxiv",
                max_results=max(1, min(int(max_results), 20)),
                check_every_hours=max(1, int(check_every_hours)),
            ),
        )
        self._touch(project)
        await self.save_state(state)
        return project

    async def get_project_dashboard(self, project_id: str) -> dict[str, Any]:
        state = await self.load_state()
        project = self._project(state, project_id)
        workflow_limit = max(1, len(project.workflow_ids))
        experiment_limit = max(1, len(project.experiment_ids))
        artifact_limit = max(1, len(project.artifact_ids))
        workflows = self._project_recent_items(
            state.workflows,
            project.workflow_ids,
            limit=workflow_limit,
        )
        notes = self._project_recent_items(state.notes, project.note_ids, limit=5)
        experiments = self._project_recent_items(
            state.experiments,
            project.experiment_ids,
            limit=experiment_limit,
        )
        claims = self._project_recent_items(state.claims, project.claim_ids, limit=5)
        project_artifacts = self._project_recent_items(
            state.artifacts,
            project.artifact_ids,
            limit=artifact_limit,
        )
        drafts = [
            artifact for artifact in project_artifacts if artifact.artifact_type == "draft"
        ][:5]
        active_workflows = [
            workflow
            for workflow in workflows
            if workflow.status in {"queued", "running", "blocked", "paused"}
        ]
        now = datetime.now(timezone.utc)
        workflow_health = {
            "running": 0,
            "blocked": 0,
            "queued": 0,
            "paused": 0,
            "ready_for_retry": 0,
        }
        experiment_health = {
            "planned": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
            "contract_passed": 0,
            "contract_failed": 0,
            "bundle_passed": 0,
            "bundle_failed": 0,
            "bundle_pending": 0,
            "bundle_schema_missing": 0,
        }
        remediation_health = {
            "open_tasks": 0,
            "due_tasks": 0,
            "retry_exhausted": 0,
            "dispatch_attempts": 0,
            "execution_attempts": 0,
        }
        recent_blockers: list[dict[str, Any]] = []

        for workflow in workflows:
            if workflow.status in workflow_health:
                workflow_health[workflow.status] += 1
            remediation_context = self._workflow_contract_followup_context(state, workflow)
            if remediation_context.get("ready_for_retry"):
                workflow_health["ready_for_retry"] += 1
            remediation_tasks = list(remediation_context.get("remediation_tasks", []) or [])
            open_remediation_tasks = [
                task
                for task in remediation_tasks
                if str(task.get("status", "") or "").strip()
                not in {"completed", "cancelled"}
            ]
            remediation_health["open_tasks"] += len(open_remediation_tasks)
            remediation_health["retry_exhausted"] += int(
                remediation_context.get("retry_exhausted_count") or 0,
            )
            for task in open_remediation_tasks:
                remediation_health["dispatch_attempts"] += int(
                    task.get("dispatch_count") or 0,
                )
                remediation_health["execution_attempts"] += int(
                    task.get("execution_count") or 0,
                )
                due_at = _parse_iso(str(task.get("due_at") or "").strip() or None)
                if due_at is not None and due_at <= now:
                    remediation_health["due_tasks"] += 1
            if workflow.status == "blocked" or open_remediation_tasks:
                contract_failures = list(
                    remediation_context.get("contract_failures", []) or [],
                )
                actionable_tasks = [
                    {
                        "task_id": str(task.get("id", "") or ""),
                        "title": str(task.get("title", "") or ""),
                        "status": str(task.get("status", "") or ""),
                        "assignee": str(task.get("assignee", "") or ""),
                        "action_type": str(task.get("action_type", "") or ""),
                        "target": str(task.get("target", "") or ""),
                        "suggested_tool": str(task.get("suggested_tool", "") or ""),
                        "can_dispatch": bool(task.get("can_dispatch", False)),
                        "can_execute": bool(task.get("can_execute", False)),
                        "dispatch_count": int(task.get("dispatch_count") or 0),
                        "execution_count": int(task.get("execution_count") or 0),
                        "last_dispatch_summary": str(
                            task.get("last_dispatch_summary", "") or "",
                        ),
                        "last_execution_summary": str(
                            task.get("last_execution_summary", "") or "",
                        ),
                    }
                    for task in open_remediation_tasks[:3]
                ]
                recent_blockers.append(
                    {
                        "kind": "workflow_blocker",
                        "workflow_id": workflow.id,
                        "experiment_id": str(
                            contract_failures[0].get("experiment_id", ""),
                        )
                        if contract_failures
                        else "",
                        "title": workflow.title,
                        "status": workflow.status,
                        "stage": workflow.current_stage,
                        "summary": str(
                            remediation_context.get("remediation_summary")
                            or f"{workflow.title} is blocked."
                            or "",
                        ).strip(),
                        "blocked_task_id": str(
                            remediation_context.get("blocked_task_id", "") or "",
                        ),
                        "blocked_task_title": str(
                            remediation_context.get("blocked_task_title", "") or "",
                        ),
                        "open_remediation_tasks": len(open_remediation_tasks),
                        "ready_for_retry": bool(
                            remediation_context.get("ready_for_retry", False),
                        ),
                        "actionable_tasks": actionable_tasks,
                        "updated_at": workflow.updated_at,
                    },
                )

        for experiment in experiments:
            status = str(experiment.status or "").strip()
            if status in experiment_health:
                experiment_health[status] += 1
            contract_validation = self._evaluate_experiment_artifact_contract(
                state,
                experiment,
            )
            if contract_validation.get("enabled"):
                if contract_validation.get("passed", False):
                    experiment_health["contract_passed"] += 1
                else:
                    experiment_health["contract_failed"] += 1
            bundle_validation = dict(
                dict(getattr(experiment, "metadata", {}) or {}).get(
                    "result_bundle_validation",
                    {},
                )
                or {},
            )
            if bundle_validation.get("enabled"):
                if bundle_validation.get("passed", False):
                    experiment_health["bundle_passed"] += 1
                else:
                    experiment_health["bundle_failed"] += 1
                if bundle_validation.get("schema_found") is False:
                    experiment_health["bundle_schema_missing"] += 1
            elif str(getattr(experiment.execution, "result_bundle_schema", "") or "").strip():
                experiment_health["bundle_pending"] += 1

        recent_blockers.sort(
            key=lambda item: str(item.get("updated_at", "")),
            reverse=True,
        )
        return {
            "project": project,
            "counts": {
                "workflows": len(project.workflow_ids),
                "notes": len(project.note_ids),
                "experiments": len(project.experiment_ids),
                "claims": len(project.claim_ids),
                "artifacts": len(project.artifact_ids),
                "drafts": len(
                    [item for item in state.artifacts if item.id in set(project.artifact_ids) and item.artifact_type == "draft"],
                ),
                "paper_refs": len(project.paper_refs),
                "paper_watches": len(project.paper_watches),
                "execution_catalog": len(project.execution_catalog),
                "result_bundle_schemas": len(project.result_bundle_schemas),
            },
            "health": {
                "workflows": workflow_health,
                "experiments": experiment_health,
                "remediation": remediation_health,
            },
            "active_workflows": active_workflows[:5],
            "recent_notes": notes,
            "recent_experiments": experiments[:5],
            "recent_claims": claims,
            "recent_drafts": drafts,
            "recent_blockers": recent_blockers[:5],
        }

    async def get_overview(self) -> dict[str, Any]:
        state = await self.load_state()
        active_workflows = [
            item
            for item in state.workflows
            if item.status in {"queued", "running", "blocked", "paused"}
        ]
        return {
            "counts": {
                "projects": len(state.projects),
                "workflows": len(state.workflows),
                "active_workflows": len(active_workflows),
                "notes": len(state.notes),
                "claims": len(state.claims),
                "evidences": len(state.evidences),
                "experiments": len(state.experiments),
                "artifacts": len(state.artifacts),
            },
            "active_workflows": active_workflows[:10],
            "projects": state.projects[:10],
        }

    # ---- workflow APIs ----

    async def list_workflows(
        self,
        *,
        project_id: str = "",
        status: str = "",
    ) -> list[ResearchWorkflow]:
        state = await self.load_state()
        rows = list(state.workflows)
        if project_id:
            rows = [item for item in rows if item.project_id == project_id]
        if status:
            rows = [item for item in rows if item.status == status]
        return rows

    async def create_workflow(
        self,
        *,
        project_id: str,
        title: str,
        goal: str = "",
        bindings: dict[str, Any] | None = None,
        execution_policy: dict[str, Any] | None = None,
        experiment_runner: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        auto_start: bool = True,
    ) -> ResearchWorkflow:
        state = await self.load_state()
        project = self._project(state, project_id)
        workflow = ResearchWorkflow(
            project_id=project_id,
            title=title,
            goal=goal,
            status="running" if auto_start else "draft",
            bindings=self._merge_binding(
                base=project.default_binding,
                patch=bindings,
            ),
            execution_policy=self._merge_execution_policy(
                base=WorkflowExecutionPolicy(),
                patch=execution_policy,
            ),
            experiment_runner=self._merge_runner_profile(
                base=project.default_experiment_runner,
                patch=experiment_runner,
            ),
            stages=[WorkflowStageState(name=stage) for stage in WORKFLOW_STAGES],
            metadata=dict(metadata or {}),
        )
        if auto_start:
            workflow.started_at = utc_now()
            workflow.last_transition_at = workflow.started_at
            stage = self._workflow_stage(workflow, workflow.current_stage)
            stage.status = "running"
            stage.started_at = workflow.started_at
            stage.updated_at = workflow.started_at
            self._seed_stage_task(workflow)
            self._recompute_workflow(workflow, now=workflow.started_at)
        state.workflows.append(workflow)
        _append_unique(project.workflow_ids, workflow.id)
        self._touch(project)
        await self.save_state(state)
        return workflow

    async def get_workflow(self, workflow_id: str) -> ResearchWorkflow:
        state = await self.load_state()
        workflow = self._workflow(state, workflow_id)
        self._ensure_workflow_scaffold(workflow)
        return workflow

    async def get_workflow_task(
        self,
        *,
        workflow_id: str,
        task_id: str,
    ) -> WorkflowTask:
        state = await self.load_state()
        workflow = self._workflow(state, workflow_id)
        self._ensure_workflow_scaffold(workflow)
        return self._workflow_task(workflow, task_id)

    async def tick_workflow(self, workflow_id: str) -> ResearchWorkflow:
        state = await self.load_state()
        workflow = self._workflow(state, workflow_id)
        self._recompute_workflow(workflow)
        await self.save_state(state)
        return workflow

    async def update_workflow_binding(
        self,
        *,
        workflow_id: str,
        patch: dict[str, Any],
    ) -> ResearchWorkflow:
        state = await self.load_state()
        workflow = self._workflow(state, workflow_id)
        workflow.bindings = self._merge_binding(
            base=workflow.bindings,
            patch=patch,
        )
        self._touch(workflow)
        await self.save_state(state)
        return workflow

    async def update_workflow_execution_policy(
        self,
        *,
        workflow_id: str,
        patch: dict[str, Any],
    ) -> ResearchWorkflow:
        state = await self.load_state()
        workflow = self._workflow(state, workflow_id)
        workflow.execution_policy = self._merge_execution_policy(
            base=workflow.execution_policy,
            patch=patch,
        )
        self._touch(workflow)
        await self.save_state(state)
        return workflow

    async def update_workflow_experiment_runner(
        self,
        *,
        workflow_id: str,
        patch: dict[str, Any],
    ) -> ResearchWorkflow:
        state = await self.load_state()
        workflow = self._workflow(state, workflow_id)
        workflow.experiment_runner = self._merge_runner_profile(
            base=workflow.experiment_runner,
            patch=patch,
        )
        self._touch(workflow)
        await self.save_state(state)
        return workflow

    async def pause_workflow(self, workflow_id: str) -> ResearchWorkflow:
        state = await self.load_state()
        workflow = self._workflow(state, workflow_id)
        workflow.status = "paused"
        workflow.paused_at = utc_now()
        self._touch(workflow)
        stage = self._workflow_stage(workflow, workflow.current_stage)
        if stage.status == "running":
            stage.status = "pending"
            stage.updated_at = workflow.paused_at or utc_now()
        await self.save_state(state)
        return workflow

    async def resume_workflow(self, workflow_id: str) -> ResearchWorkflow:
        state = await self.load_state()
        workflow = self._workflow(state, workflow_id)
        workflow.status = "running"
        workflow.paused_at = None
        stage = self._workflow_stage(workflow, workflow.current_stage)
        stage.status = "running"
        if not stage.started_at:
            stage.started_at = utc_now()
        self._recompute_workflow(workflow)
        await self.save_state(state)
        return workflow

    async def cancel_workflow(self, workflow_id: str) -> ResearchWorkflow:
        state = await self.load_state()
        workflow = self._workflow(state, workflow_id)
        workflow.status = "cancelled"
        self._touch(workflow)
        for task in self._stage_task_list(workflow, workflow.current_stage):
            if task.status in {"pending", "running", "blocked"}:
                task.status = "cancelled"
                task.completed_at = utc_now()
                task.updated_at = task.completed_at
        await self.save_state(state)
        return workflow

    async def retry_workflow(self, workflow_id: str) -> ResearchWorkflow:
        state = await self.load_state()
        workflow = self._workflow(state, workflow_id)
        workflow.status = "running"
        workflow.retry_count += 1
        workflow.error = ""
        stage = self._workflow_stage(workflow, workflow.current_stage)
        stage.status = "running"
        stage.blocked_reason = ""
        stage.updated_at = utc_now()
        for task in self._stage_task_list(workflow, workflow.current_stage):
            if task.status in {"failed", "blocked"}:
                task.status = "pending"
                task.summary = ""
                task.updated_at = utc_now()
        self._recompute_workflow(workflow)
        await self.save_state(state)
        return workflow

    async def add_workflow_task(
        self,
        *,
        workflow_id: str,
        title: str,
        description: str = "",
        stage: str | None = None,
        depends_on: list[str] | None = None,
        due_at: str | None = None,
        assignee: str = "agent",
        metadata: dict[str, Any] | None = None,
    ) -> ResearchWorkflow:
        state = await self.load_state()
        workflow = self._workflow(state, workflow_id)
        stage_name = (stage or workflow.current_stage)
        if stage_name not in WORKFLOW_STAGES:
            raise ValueError(f"Unsupported workflow stage: {stage_name}")
        task = WorkflowTask(
            stage=stage_name,  # type: ignore[arg-type]
            title=title,
            description=description,
            depends_on=_remove_empty_strings(depends_on or []),
            due_at=due_at,
            assignee=assignee,
            metadata=dict(metadata or {}),
        )
        workflow.tasks.append(task)
        stage_state = self._workflow_stage(workflow, task.stage)
        _append_unique(stage_state.task_ids, task.id)
        stage_state.updated_at = utc_now()
        self._touch(workflow)
        await self.save_state(state)
        return workflow

    async def update_workflow_task(
        self,
        *,
        workflow_id: str,
        task_id: str,
        status: str | None = None,
        summary: str | None = None,
        due_at: str | None = None,
        note_ids: list[str] | None = None,
        claim_ids: list[str] | None = None,
        artifact_ids: list[str] | None = None,
    ) -> ResearchWorkflow:
        state = await self.load_state()
        workflow = self._workflow(state, workflow_id)
        task = self._workflow_task(workflow, task_id)
        if status:
            task.status = status  # type: ignore[assignment]
            if status in {"completed", "cancelled"}:
                task.completed_at = utc_now()
        if summary is not None:
            task.summary = summary
        if due_at is not None:
            task.due_at = due_at
        for note_id in _remove_empty_strings(note_ids or []):
            _append_unique(task.note_ids, note_id)
            _append_unique(workflow.note_ids, note_id)
        for claim_id in _remove_empty_strings(claim_ids or []):
            _append_unique(task.claim_ids, claim_id)
            _append_unique(workflow.claim_ids, claim_id)
        for artifact_id in _remove_empty_strings(artifact_ids or []):
            _append_unique(task.artifact_ids, artifact_id)
            _append_unique(workflow.artifact_ids, artifact_id)
        task.updated_at = utc_now()
        self._recompute_workflow(workflow)
        await self.save_state(state)
        return workflow

    async def record_workflow_task_dispatch(
        self,
        *,
        workflow_id: str,
        task_id: str,
        summary: str,
        error: str = "",
    ) -> WorkflowTask:
        state = await self.load_state()
        workflow = self._workflow(state, workflow_id)
        task = self._workflow_task(workflow, task_id)
        now = utc_now()
        task.dispatch_count += 1
        task.last_dispatch_at = now
        task.last_dispatch_summary = str(summary or "").strip()
        task.last_dispatch_error = str(error or "").strip()
        task.updated_at = now
        self._touch(workflow, now=now)
        await self.save_state(state)
        return task

    async def record_workflow_task_execution(
        self,
        *,
        workflow_id: str,
        task_id: str,
        summary: str,
        error: str = "",
    ) -> WorkflowTask:
        state = await self.load_state()
        workflow = self._workflow(state, workflow_id)
        task = self._workflow_task(workflow, task_id)
        now = utc_now()
        task.execution_count += 1
        task.last_execution_at = now
        task.last_execution_summary = str(summary or "").strip()
        task.last_execution_error = str(error or "").strip()
        task.updated_at = now
        self._touch(workflow, now=now)
        await self.save_state(state)
        return task

    async def record_workflow_automation_run(
        self,
        *,
        workflow_id: str,
        run_id: str,
        summary: str = "",
        session_id: str = "",
        dispatches: list[dict[str, str]] | None = None,
    ) -> ResearchWorkflow:
        state = await self.load_state()
        workflow = self._workflow(state, workflow_id)
        _append_unique(workflow.bindings.automation_run_ids, run_id)
        if session_id:
            workflow.bindings.session_id = session_id
        if dispatches:
            first = dispatches[0]
            workflow.bindings.channel = str(first.get("channel", "") or workflow.bindings.channel)
            workflow.bindings.user_id = str(first.get("user_id", "") or workflow.bindings.user_id)
            workflow.bindings.session_id = str(first.get("session_id", "") or workflow.bindings.session_id)
        if summary:
            workflow.bindings.last_summary = summary
        workflow.bindings.last_dispatch_at = utc_now()
        self._touch(workflow)
        await self.save_state(state)
        return workflow

    # ---- notes ----

    async def create_note(
        self,
        *,
        project_id: str,
        title: str,
        content: str,
        note_type: str = "idea_note",
        workflow_id: str = "",
        experiment_ids: list[str] | None = None,
        claim_ids: list[str] | None = None,
        artifact_ids: list[str] | None = None,
        paper_refs: list[str] | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ResearchNote:
        state = await self.load_state()
        project = self._project(state, project_id)
        note = ResearchNote(
            project_id=project_id,
            title=title,
            content=content,
            note_type=note_type,  # type: ignore[arg-type]
            workflow_id=workflow_id,
            experiment_ids=_remove_empty_strings(experiment_ids or []),
            claim_ids=_remove_empty_strings(claim_ids or []),
            artifact_ids=_remove_empty_strings(artifact_ids or []),
            paper_refs=_remove_empty_strings(paper_refs or []),
            tags=_remove_empty_strings(tags or []),
            metadata=dict(metadata or {}),
        )
        state.notes.append(note)
        _append_unique(project.note_ids, note.id)
        for paper_ref in note.paper_refs:
            _append_unique(project.paper_refs, paper_ref)
        self._touch(project)

        if workflow_id:
            workflow = self._workflow(state, workflow_id)
            _append_unique(workflow.note_ids, note.id)
            self._touch(workflow)

        for experiment_id in note.experiment_ids:
            experiment = self._experiment(state, experiment_id)
            _append_unique(experiment.note_ids, note.id)
            self._touch(experiment)

        for claim_id in note.claim_ids:
            claim = self._claim(state, claim_id)
            _append_unique(claim.note_ids, note.id)
            self._touch(claim)

        for artifact_id in note.artifact_ids:
            artifact = self._artifact(state, artifact_id)
            _append_unique(artifact.note_ids, note.id)
            self._touch(artifact)

        await self.save_state(state)
        return note

    async def list_notes(
        self,
        *,
        query: str = "",
        note_type: str = "",
        tags: list[str] | None = None,
        project_id: str = "",
        workflow_id: str = "",
        claim_id: str = "",
        experiment_id: str = "",
        limit: int = 50,
    ) -> list[ResearchNote]:
        state = await self.load_state()
        notes = [
            note
            for note in state.notes
            if self._note_matches(
                note,
                query=query,
                note_type=note_type,
                tags=tags,
                project_id=project_id,
                workflow_id=workflow_id,
                claim_id=claim_id,
                experiment_id=experiment_id,
            )
        ]
        notes.sort(key=lambda item: item.updated_at, reverse=True)
        return notes[: max(1, int(limit))]

    async def get_note_tag_counts(self, *, project_id: str = "") -> dict[str, int]:
        notes = await self.list_notes(project_id=project_id, limit=10_000)
        counts: dict[str, int] = {}
        for note in notes:
            for tag in note.tags:
                counts[tag] = counts.get(tag, 0) + 1
        return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))

    # ---- artifacts ----

    async def list_artifacts(
        self,
        *,
        project_id: str = "",
        workflow_id: str = "",
        artifact_type: str = "",
        source_type: str = "",
        limit: int = 100,
    ) -> list[ResearchArtifact]:
        state = await self.load_state()
        artifacts = list(state.artifacts)
        if project_id:
            artifacts = [item for item in artifacts if item.project_id == project_id]
        if workflow_id:
            artifacts = [item for item in artifacts if item.workflow_id == workflow_id]
        if artifact_type:
            artifacts = [item for item in artifacts if item.artifact_type == artifact_type]
        if source_type:
            artifacts = [item for item in artifacts if item.source_type == source_type]
        artifacts.sort(key=lambda item: item.updated_at or item.created_at, reverse=True)
        return artifacts[: max(1, int(limit))]

    async def upsert_artifact(
        self,
        *,
        project_id: str,
        title: str,
        artifact_type: str,
        workflow_id: str = "",
        description: str = "",
        path: str = "",
        uri: str = "",
        source_type: str = "",
        source_id: str = "",
        experiment_id: str = "",
        note_ids: list[str] | None = None,
        claim_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ResearchArtifact:
        state = await self.load_state()
        self._project(state, project_id)
        candidate: ResearchArtifact | None = None
        normalized_title = str(title or "").strip().lower()

        for item in state.artifacts:
            if item.project_id != project_id:
                continue
            if item.artifact_type != artifact_type:
                continue
            if source_id and item.source_type == source_type and item.source_id == source_id:
                candidate = item
                break
            if uri and item.uri == uri:
                candidate = item
                break
            if path and item.path == path:
                candidate = item
                break
            if (
                normalized_title
                and artifact_type == "paper"
                and item.title.strip().lower() == normalized_title
            ):
                candidate = item
                break

        if candidate is None:
            artifact = self._add_artifact_to_state(
                state,
                project_id=project_id,
                workflow_id=workflow_id,
                title=title,
                artifact_type=artifact_type,  # type: ignore[arg-type]
                description=description,
                path=path,
                uri=uri,
                source_type=source_type,
                source_id=source_id,
                experiment_id=experiment_id,
                note_ids=note_ids,
                claim_ids=claim_ids,
                metadata=metadata,
            )
            await self.save_state(state)
            return artifact

        if title:
            candidate.title = title
        if description:
            candidate.description = description
        if path:
            candidate.path = path
        if uri:
            candidate.uri = uri
        if source_type:
            candidate.source_type = source_type
        if source_id:
            candidate.source_id = source_id
        if experiment_id:
            candidate.experiment_id = experiment_id
        if workflow_id and not candidate.workflow_id:
            candidate.workflow_id = workflow_id
        if metadata:
            merged_metadata = dict(candidate.metadata)
            merged_metadata.update(dict(metadata))
            candidate.metadata = merged_metadata

        project = self._project(state, project_id)
        _append_unique(project.artifact_ids, candidate.id)
        self._touch(project)

        if workflow_id:
            workflow = self._workflow(state, workflow_id)
            _append_unique(workflow.artifact_ids, candidate.id)
            stage = self._workflow_stage(workflow, workflow.current_stage)
            _append_unique(stage.artifact_ids, candidate.id)
            stage.updated_at = utc_now()
            self._touch(workflow)

        for note_id in _remove_empty_strings(note_ids or []):
            _append_unique(candidate.note_ids, note_id)
            note = self._note(state, note_id)
            _append_unique(note.artifact_ids, candidate.id)
            self._touch(note)

        for claim_id in _remove_empty_strings(claim_ids or []):
            _append_unique(candidate.claim_ids, claim_id)
            claim = self._claim(state, claim_id)
            _append_unique(claim.artifact_ids, candidate.id)
            self._touch(claim)

        self._touch(candidate)
        await self.save_state(state)
        return candidate

    # ---- claims / evidences ----

    async def create_claim(
        self,
        *,
        project_id: str,
        text: str,
        workflow_id: str = "",
        status: str = "draft",
        confidence: float | None = None,
        note_ids: list[str] | None = None,
        artifact_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ResearchClaim:
        state = await self.load_state()
        project = self._project(state, project_id)
        claim = ResearchClaim(
            project_id=project_id,
            text=text,
            workflow_id=workflow_id,
            status=status,  # type: ignore[arg-type]
            confidence=confidence,
            note_ids=_remove_empty_strings(note_ids or []),
            artifact_ids=_remove_empty_strings(artifact_ids or []),
            metadata=dict(metadata or {}),
        )
        state.claims.append(claim)
        _append_unique(project.claim_ids, claim.id)
        self._touch(project)

        if workflow_id:
            workflow = self._workflow(state, workflow_id)
            _append_unique(workflow.claim_ids, claim.id)
            self._touch(workflow)

        for note_id in claim.note_ids:
            note = self._note(state, note_id)
            _append_unique(note.claim_ids, claim.id)
            self._touch(note)

        for artifact_id in claim.artifact_ids:
            artifact = self._artifact(state, artifact_id)
            _append_unique(artifact.claim_ids, claim.id)
            self._touch(artifact)

        await self.save_state(state)
        return claim

    async def list_claims(
        self,
        *,
        project_id: str = "",
        workflow_id: str = "",
        status: str = "",
        limit: int = 100,
    ) -> list[ResearchClaim]:
        state = await self.load_state()
        claims = list(state.claims)
        if project_id:
            claims = [item for item in claims if item.project_id == project_id]
        if workflow_id:
            claims = [item for item in claims if item.workflow_id == workflow_id]
        if status:
            claims = [item for item in claims if item.status == status]
        claims.sort(key=lambda item: item.updated_at, reverse=True)
        return claims[: max(1, int(limit))]

    async def update_claim(
        self,
        *,
        claim_id: str,
        text: str | None = None,
        status: str | None = None,
        confidence: float | None = None,
        note_ids: list[str] | None = None,
        artifact_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ResearchClaim:
        state = await self.load_state()
        claim = self._claim(state, claim_id)

        if text is not None:
            claim.text = text
        if status:
            claim.status = status  # type: ignore[assignment]
        if confidence is not None:
            claim.confidence = confidence
        if metadata:
            merged_metadata = dict(claim.metadata)
            merged_metadata.update(dict(metadata))
            claim.metadata = merged_metadata

        for note_id in _remove_empty_strings(note_ids or []):
            _append_unique(claim.note_ids, note_id)
            note = self._note(state, note_id)
            _append_unique(note.claim_ids, claim.id)
            self._touch(note)

        for artifact_id in _remove_empty_strings(artifact_ids or []):
            _append_unique(claim.artifact_ids, artifact_id)
            artifact = self._artifact(state, artifact_id)
            _append_unique(artifact.claim_ids, claim.id)
            self._touch(artifact)

        if claim.workflow_id:
            workflow = self._workflow(state, claim.workflow_id)
            _append_unique(workflow.claim_ids, claim.id)
            self._touch(workflow)

        self._touch(claim)
        await self.save_state(state)
        return claim

    async def attach_evidence(
        self,
        *,
        project_id: str,
        claim_ids: list[str],
        evidence_type: str,
        summary: str,
        source_type: str,
        source_id: str = "",
        title: str = "",
        locator: str = "",
        quote: str = "",
        url: str = "",
        workflow_id: str = "",
        artifact_id: str = "",
        note_id: str = "",
        experiment_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ResearchEvidence:
        state = await self.load_state()
        self._project(state, project_id)
        evidence = self._add_evidence_to_state(
            state,
            project_id=project_id,
            evidence_type=evidence_type,  # type: ignore[arg-type]
            summary=summary,
            claim_ids=_remove_empty_strings(claim_ids),
            workflow_id=workflow_id,
            artifact_id=artifact_id,
            note_id=note_id,
            experiment_id=experiment_id,
            source=EvidenceSource(
                source_type=source_type,  # type: ignore[arg-type]
                source_id=source_id,
                title=title,
                locator=locator,
                quote=quote,
                url=url,
                metadata=dict(metadata or {}),
            ),
            metadata=dict(metadata or {}),
        )
        await self.save_state(state)
        return evidence

    async def get_claim_graph(self, claim_id: str) -> dict[str, Any]:
        state = await self.load_state()
        claim = self._claim(state, claim_id)
        evidences = [
            item for item in state.evidences if item.id in set(claim.evidence_ids)
        ]
        notes = [item for item in state.notes if item.id in set(claim.note_ids)]
        artifacts = [
            item for item in state.artifacts if item.id in set(claim.artifact_ids)
        ]
        experiments = [
            item
            for item in state.experiments
            if claim.id in set(item.claim_ids) or any(
                evidence.experiment_id == item.id for evidence in evidences
            )
        ]
        workflow = (
            self._workflow(state, claim.workflow_id)
            if claim.workflow_id
            else None
        )
        project = self._project(state, claim.project_id)
        return {
            "project": project,
            "workflow": workflow,
            "claim": claim,
            "evidences": evidences,
            "notes": notes,
            "artifacts": artifacts,
            "experiments": experiments,
        }

    # ---- experiments ----

    async def get_experiment(self, experiment_id: str) -> ExperimentRun:
        state = await self.load_state()
        return self._experiment(state, experiment_id)

    async def get_experiment_artifact_contract_validation(
        self,
        experiment_id: str,
    ) -> dict[str, Any]:
        state = await self.load_state()
        experiment = self._experiment(state, experiment_id)
        validation = self._evaluate_experiment_artifact_contract(state, experiment)
        existing = dict(experiment.metadata).get("contract_validation")
        existing_without_timestamp = (
            {
                key: value
                for key, value in dict(existing).items()
                if key != "validated_at"
            }
            if isinstance(existing, dict)
            else None
        )
        current_without_timestamp = {
            key: value
            for key, value in validation.items()
            if key != "validated_at"
        }
        if existing_without_timestamp == current_without_timestamp:
            return dict(existing)
        if dict(experiment.metadata).get("contract_validation") != validation:
            experiment.metadata = {
                **dict(experiment.metadata),
                "contract_validation": validation,
            }
            self._touch(experiment)
            await self.save_state(state)
        return validation

    async def get_experiment_contract_remediation(
        self,
        experiment_id: str,
    ) -> dict[str, Any]:
        validation = await self.get_experiment_artifact_contract_validation(
            experiment_id,
        )
        remediation = validation.get("remediation")
        if isinstance(remediation, dict):
            return remediation
        return {
            "required": False,
            "summary": "No remediation actions are required.",
            "actions": [],
            "action_count": 0,
        }

    async def get_workflow_contract_remediation_context(
        self,
        workflow_id: str,
    ) -> dict[str, Any]:
        state = await self.load_state()
        workflow = self._workflow(state, workflow_id)
        return self._workflow_contract_followup_context(state, workflow)

    async def configure_experiment_execution(
        self,
        *,
        experiment_id: str,
        patch: dict[str, Any],
    ) -> dict[str, Any]:
        state = await self.load_state()
        experiment = self._experiment(state, experiment_id)
        before_mode = experiment.execution.mode
        experiment.execution = self._merge_experiment_execution(
            base=experiment.execution,
            patch=patch,
        )
        schema_name = str(experiment.execution.result_bundle_schema or "").strip()
        if schema_name:
            schema_contract = self._result_bundle_schema_contract(
                self._project_result_bundle_schema(
                    state,
                    project_id=experiment.project_id,
                    schema_name=schema_name,
                ),
            )
            if schema_contract:
                execution_metadata = dict(experiment.execution.metadata)
                execution_metadata["artifact_contract"] = self._merge_contract_dicts(
                    schema_contract,
                    execution_metadata.get("artifact_contract")
                    if isinstance(execution_metadata.get("artifact_contract"), dict)
                    else None,
                )
                experiment.execution.metadata = execution_metadata
        now = utc_now()
        if experiment.execution.mode != "inline" and not experiment.execution.submitted_at:
            experiment.execution.submitted_at = now
        event = self._add_experiment_event_to_state(
            state,
            experiment=experiment,
            event_type="binding",
            summary=(
                f"Configured experiment execution mode "
                f"{before_mode} -> {experiment.execution.mode}."
            ),
            metadata={
                "patch": patch,
                "before_mode": before_mode,
                "after_mode": experiment.execution.mode,
                "external_run_id": experiment.execution.external_run_id,
            },
        )
        self._touch(experiment, now=now)
        await self.save_state(state)
        return {
            "experiment": experiment,
            "event": event,
        }

    async def list_experiment_events(
        self,
        *,
        experiment_id: str,
        limit: int = 100,
    ) -> list[ExperimentEvent]:
        state = await self.load_state()
        rows = [
            item
            for item in state.experiment_events
            if item.experiment_id == experiment_id
        ]
        rows.sort(key=lambda item: item.created_at, reverse=True)
        return rows[: max(1, int(limit))]

    async def record_experiment_heartbeat(
        self,
        *,
        experiment_id: str,
        summary: str,
        status: str = "running",
        metrics: dict[str, Any] | None = None,
        output_files: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_status = str(status or "running").strip() or "running"
        experiment = await self.update_experiment(
            experiment_id=experiment_id,
            status=normalized_status,
            metrics=metrics,
            output_files=output_files,
            metadata=metadata,
        )
        state = await self.load_state()
        experiment = self._experiment(state, experiment_id)
        now = utc_now()
        if not experiment.execution.submitted_at:
            experiment.execution.submitted_at = now
        experiment.execution.last_heartbeat_at = now
        event = self._add_experiment_event_to_state(
            state,
            experiment=experiment,
            event_type="heartbeat",
            summary=summary,
            status=experiment.status,
            metrics=metrics,
            output_files=output_files,
            artifact_ids=experiment.artifact_ids,
            metadata=metadata,
        )
        self._touch(experiment, now=now)
        await self.save_state(state)
        return {
            "experiment": experiment,
            "event": event,
        }

    async def record_experiment_result(
        self,
        *,
        experiment_id: str,
        summary: str = "",
        status: str = "completed",
        metrics: dict[str, Any] | None = None,
        output_files: list[str] | None = None,
        notes: str | None = None,
        note_ids: list[str] | None = None,
        claim_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_status = str(status or "completed").strip() or "completed"
        experiment = await self.update_experiment(
            experiment_id=experiment_id,
            status=normalized_status,
            metrics=metrics,
            output_files=output_files,
            notes=notes,
            note_ids=note_ids,
            claim_ids=claim_ids,
            metadata=metadata,
        )
        state = await self.load_state()
        experiment = self._experiment(state, experiment_id)
        now = utc_now()
        if not experiment.execution.submitted_at:
            experiment.execution.submitted_at = now
        experiment.execution.last_heartbeat_at = now
        contract_validation = self._store_experiment_artifact_contract_validation(
            state,
            experiment,
        )
        event_type = "completion"
        if experiment.status in {"failed", "cancelled"}:
            event_type = "failure"
        elif experiment.status not in {"completed"}:
            event_type = "status"
        event = self._add_experiment_event_to_state(
            state,
            experiment=experiment,
            event_type=event_type,
            summary=summary or f"Experiment {experiment.name} updated to {experiment.status}.",
            status=experiment.status,
            metrics=metrics,
            output_files=output_files,
            note_ids=note_ids,
            artifact_ids=experiment.artifact_ids,
            metadata={
                **dict(metadata or {}),
                "contract_validation": contract_validation,
            },
        )
        self._touch(experiment, now=now)
        await self.save_state(state)
        return {
            "experiment": experiment,
            "event": event,
        }

    @staticmethod
    def _experiment_summary_parts(experiment: ExperimentRun) -> list[str]:
        summary_parts: list[str] = []
        if experiment.metrics:
            metric_preview = ", ".join(
                f"{key}={value}" for key, value in sorted(experiment.metrics.items())
            )
            summary_parts.append(f"Metrics: {metric_preview}")
        if experiment.output_files:
            summary_parts.append(
                "Outputs: "
                + ", ".join(Path(path).name or path for path in experiment.output_files[:5]),
            )
        return summary_parts

    def _sync_experiment_output_artifacts(
        self,
        state: ResearchState,
        experiment: ExperimentRun,
    ) -> None:
        project = self._project(state, experiment.project_id)
        workflow = (
            self._workflow(state, experiment.workflow_id)
            if experiment.workflow_id
            else None
        )

        for output_file in experiment.output_files:
            artifact = next(
                (
                    item
                    for item in state.artifacts
                    if item.experiment_id == experiment.id and item.path == output_file
                ),
                None,
            )
            if artifact is None:
                artifact = self._add_artifact_to_state(
                    state,
                    project_id=experiment.project_id,
                    workflow_id=experiment.workflow_id,
                    title=Path(output_file).name or output_file,
                    artifact_type=_artifact_type_from_path(output_file),
                    description=f"Archived output for experiment {experiment.name}",
                    path=output_file,
                    source_type="experiment",
                    source_id=experiment.id,
                    experiment_id=experiment.id,
                    claim_ids=experiment.claim_ids,
                )
            else:
                artifact.title = Path(output_file).name or output_file
                artifact.description = f"Archived output for experiment {experiment.name}"
                artifact.path = output_file
                artifact.source_type = "experiment"
                artifact.source_id = experiment.id
                artifact.experiment_id = experiment.id
                if experiment.workflow_id and not artifact.workflow_id:
                    artifact.workflow_id = experiment.workflow_id
                _append_unique(project.artifact_ids, artifact.id)
                self._touch(project)
                if workflow is not None:
                    _append_unique(workflow.artifact_ids, artifact.id)
                    stage = self._workflow_stage(workflow, workflow.current_stage)
                    _append_unique(stage.artifact_ids, artifact.id)
                    stage.updated_at = utc_now()
                    self._touch(workflow)
                self._touch(artifact)

            for claim_id in experiment.claim_ids:
                claim = self._claim(state, claim_id)
                _append_unique(artifact.claim_ids, claim_id)
                _append_unique(claim.artifact_ids, artifact.id)
                self._touch(claim)
            _append_unique(experiment.artifact_ids, artifact.id)

    def _sync_experiment_completion_evidence(
        self,
        state: ResearchState,
        experiment: ExperimentRun,
    ) -> None:
        if experiment.status != "completed":
            return
        if not experiment.claim_ids:
            return
        summary_parts = self._experiment_summary_parts(experiment)
        if not summary_parts:
            return

        summary = f"{experiment.name}: {'; '.join(summary_parts)}"
        evidence = next(
            (
                item
                for item in state.evidences
                if item.experiment_id == experiment.id
                and item.source.source_type == "experiment_result"
                and item.source.source_id == experiment.id
            ),
            None,
        )
        if evidence is None:
            self._add_evidence_to_state(
                state,
                project_id=experiment.project_id,
                evidence_type="experiment_result",
                summary=summary,
                claim_ids=experiment.claim_ids,
                workflow_id=experiment.workflow_id,
                experiment_id=experiment.id,
                source=EvidenceSource(
                    source_type="experiment_result",
                    source_id=experiment.id,
                    title=experiment.name,
                    locator="metrics",
                    quote=experiment.notes[:280],
                    metadata={"metrics": experiment.metrics},
                ),
                metadata={"experiment_id": experiment.id},
            )
            return

        evidence.summary = summary
        evidence.workflow_id = evidence.workflow_id or experiment.workflow_id
        evidence.source.title = experiment.name
        evidence.source.locator = "metrics"
        evidence.source.quote = experiment.notes[:280]
        evidence.source.metadata = {"metrics": experiment.metrics}
        merged_metadata = dict(evidence.metadata)
        merged_metadata.update({"experiment_id": experiment.id})
        evidence.metadata = merged_metadata
        for claim_id in experiment.claim_ids:
            _append_unique(evidence.claim_ids, claim_id)
            claim = self._claim(state, claim_id)
            _append_unique(claim.evidence_ids, evidence.id)
            self._touch(claim)
        _append_unique(experiment.evidence_ids, evidence.id)
        self._touch(evidence)

    def _experiment_artifact_contract(
        self,
        state: ResearchState,
        experiment: ExperimentRun,
    ) -> dict[str, Any]:
        execution_metadata = dict(getattr(experiment.execution, "metadata", {}) or {})
        schema_name = str(
            getattr(experiment.execution, "result_bundle_schema", "")
            or execution_metadata.get("result_bundle_schema", ""),
        ).strip()
        schema_contract = self._result_bundle_schema_contract(
            self._project_result_bundle_schema(
                state,
                project_id=experiment.project_id,
                schema_name=schema_name,
            ),
        )
        execution_contract = execution_metadata.get("artifact_contract")
        experiment_metadata = dict(getattr(experiment, "metadata", {}) or {})
        experiment_contract = experiment_metadata.get("artifact_contract")
        return self._merge_contract_dicts(
            schema_contract,
            execution_contract if isinstance(execution_contract, dict) else None,
            experiment_contract if isinstance(experiment_contract, dict) else None,
        )

    def _evaluate_experiment_artifact_contract(
        self,
        state: ResearchState,
        experiment: ExperimentRun,
    ) -> dict[str, Any]:
        contract = self._experiment_artifact_contract(state, experiment)
        if not contract:
            return {
                "enabled": False,
                "passed": True,
                "summary": "No artifact contract configured.",
            }

        required_metrics = _remove_empty_strings(contract.get("required_metrics", []))
        required_outputs = _remove_empty_strings(contract.get("required_outputs", []))
        required_artifact_types = _remove_empty_strings(
            contract.get("required_artifact_types", []),
        )

        present_metrics = sorted(str(key) for key in dict(experiment.metrics or {}).keys())
        metric_set = set(present_metrics)
        missing_metrics = [key for key in required_metrics if key not in metric_set]

        present_outputs = [str(item).strip() for item in list(experiment.output_files or []) if str(item).strip()]
        present_output_candidates = set(present_outputs)
        present_output_candidates.update(Path(item).name for item in present_outputs)
        missing_outputs = [
            value for value in required_outputs if value not in present_output_candidates
        ]

        experiment_artifacts = [
            item
            for item in state.artifacts
            if item.id in set(experiment.artifact_ids)
        ]
        present_artifact_types = sorted(
            {
                str(item.artifact_type)
                for item in experiment_artifacts
                if str(item.artifact_type).strip()
            },
        )
        artifact_type_set = set(present_artifact_types)
        missing_artifact_types = [
            value for value in required_artifact_types if value not in artifact_type_set
        ]

        passed = not any([missing_metrics, missing_outputs, missing_artifact_types])
        if passed:
            summary = "Artifact contract satisfied."
        else:
            issues: list[str] = []
            if missing_metrics:
                issues.append(f"{len(missing_metrics)} missing metric(s)")
            if missing_outputs:
                issues.append(f"{len(missing_outputs)} missing output file(s)")
            if missing_artifact_types:
                issues.append(f"{len(missing_artifact_types)} missing artifact type(s)")
            summary = "Artifact contract failed: " + ", ".join(issues) + "."

        return {
            "enabled": True,
            "passed": passed,
            "summary": summary,
            "required_metrics": required_metrics,
            "present_metrics": present_metrics,
            "missing_metrics": missing_metrics,
            "required_outputs": required_outputs,
            "present_outputs": present_outputs,
            "missing_outputs": missing_outputs,
            "required_artifact_types": required_artifact_types,
            "present_artifact_types": present_artifact_types,
            "missing_artifact_types": missing_artifact_types,
            "catalog_entry": str(
                dict(getattr(experiment.execution, "metadata", {}) or {}).get(
                    "catalog_entry",
                    "",
                )
                or "",
            ).strip(),
            "validated_at": utc_now(),
            "remediation": self._build_experiment_contract_remediation(
                experiment,
                missing_metrics=missing_metrics,
                missing_outputs=missing_outputs,
                missing_artifact_types=missing_artifact_types,
            ),
        }

    @staticmethod
    def _artifact_contract_output_hint(artifact_type: str) -> str:
        normalized = str(artifact_type or "").strip()
        if normalized == "generated_table":
            return "contract-table.json"
        if normalized == "generated_figure":
            return "contract-figure.png"
        if normalized == "summary":
            return "contract-summary.md"
        if normalized == "experiment_result":
            return "contract-result.bin"
        if normalized == "draft":
            return "contract-draft.md"
        if normalized == "analysis":
            return "contract-analysis.md"
        return f"contract-{normalized or 'artifact'}.bin"

    @classmethod
    def _build_experiment_contract_remediation(
        cls,
        experiment: ExperimentRun,
        *,
        missing_metrics: list[str],
        missing_outputs: list[str],
        missing_artifact_types: list[str],
    ) -> dict[str, Any]:
        action_rows: list[dict[str, Any]] = []
        run_name = str(experiment.name or experiment.id).strip() or experiment.id
        for metric_name in missing_metrics:
            action_rows.append(
                {
                    "action_key": f"{experiment.id}:metric:{metric_name}",
                    "action_type": "record_metric",
                    "target_type": "metric",
                    "target": metric_name,
                    "experiment_id": experiment.id,
                    "workflow_id": experiment.workflow_id,
                    "blocking": True,
                    "assignee": "analyst",
                    "due_in_hours": 4,
                    "retry_policy": {
                        "max_attempts": 2,
                        "backoff_minutes": 30,
                    },
                    "title": f"Record metric '{metric_name}' for {run_name}",
                    "instructions": (
                        f"Backfill the missing metric '{metric_name}' on experiment "
                        f"{run_name} before leaving experiment_run."
                    ),
                    "suggested_tool": "research_experiment_update",
                    "payload_hint": {
                        "experiment_id": experiment.id,
                        "metrics": {
                            metric_name: "<value>",
                        },
                    },
                },
            )
        for output_name in missing_outputs:
            action_rows.append(
                {
                    "action_key": f"{experiment.id}:output:{output_name}",
                    "action_type": "archive_output",
                    "target_type": "output_file",
                    "target": output_name,
                    "experiment_id": experiment.id,
                    "workflow_id": experiment.workflow_id,
                    "blocking": True,
                    "assignee": "analyst",
                    "due_in_hours": 4,
                    "retry_policy": {
                        "max_attempts": 2,
                        "backoff_minutes": 30,
                    },
                    "title": f"Archive output '{output_name}' for {run_name}",
                    "instructions": (
                        f"Produce or register the missing output file '{output_name}' "
                        f"for experiment {run_name}."
                    ),
                    "suggested_tool": "research_experiment_update",
                    "payload_hint": {
                        "experiment_id": experiment.id,
                        "output_files": [output_name],
                    },
                },
            )
        for artifact_type in missing_artifact_types:
            expected_path = cls._artifact_contract_output_hint(artifact_type)
            action_rows.append(
                {
                    "action_key": f"{experiment.id}:artifact:{artifact_type}",
                    "action_type": "publish_artifact",
                    "target_type": "artifact_type",
                    "target": artifact_type,
                    "experiment_id": experiment.id,
                    "workflow_id": experiment.workflow_id,
                    "blocking": True,
                    "assignee": "agent",
                    "due_in_hours": 6,
                    "retry_policy": {
                        "max_attempts": 2,
                        "backoff_minutes": 60,
                    },
                    "title": f"Publish artifact type '{artifact_type}' for {run_name}",
                    "instructions": (
                        f"Create or archive a '{artifact_type}' artifact linked to "
                        f"experiment {run_name}. A typical file name would be "
                        f"'{expected_path}'."
                    ),
                    "suggested_tool": "research_artifact_upsert",
                    "payload_hint": {
                        "project_id": experiment.project_id,
                        "workflow_id": experiment.workflow_id,
                        "experiment_id": experiment.id,
                        "artifact_type": artifact_type,
                        "title": f"{run_name} {artifact_type}",
                        "path": expected_path,
                        "source_type": "experiment",
                        "source_id": experiment.id,
                        "claim_ids": list(experiment.claim_ids),
                    },
                },
            )
        if not action_rows:
            return {
                "required": False,
                "summary": "No remediation actions are required.",
                "actions": [],
                "action_count": 0,
            }
        issue_parts: list[str] = []
        if missing_metrics:
            issue_parts.append(f"{len(missing_metrics)} metric(s)")
        if missing_outputs:
            issue_parts.append(f"{len(missing_outputs)} output file(s)")
        if missing_artifact_types:
            issue_parts.append(f"{len(missing_artifact_types)} artifact type(s)")
        return {
            "required": True,
            "summary": (
                f"Resolve missing {', '.join(issue_parts)} "
                f"for experiment {run_name}."
            ),
            "actions": action_rows,
            "action_count": len(action_rows),
        }

    def _store_experiment_artifact_contract_validation(
        self,
        state: ResearchState,
        experiment: ExperimentRun,
    ) -> dict[str, Any]:
        validation = self._evaluate_experiment_artifact_contract(state, experiment)
        experiment.metadata = {
            **dict(experiment.metadata),
            "contract_validation": validation,
        }
        return validation

    async def log_experiment(
        self,
        *,
        project_id: str,
        name: str,
        workflow_id: str = "",
        status: str = "planned",
        parameters: dict[str, Any] | None = None,
        input_data: dict[str, Any] | None = None,
        metrics: dict[str, Any] | None = None,
        notes: str = "",
        output_files: list[str] | None = None,
        baseline_of: str = "",
        ablation_of: str = "",
        comparison_group: str = "",
        related_run_ids: list[str] | None = None,
        claim_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExperimentRun:
        state = await self.load_state()
        project = self._project(state, project_id)
        experiment = ExperimentRun(
            project_id=project_id,
            name=name,
            workflow_id=workflow_id,
            status=status,  # type: ignore[arg-type]
            parameters=dict(parameters or {}),
            input_data=dict(input_data or {}),
            metrics=dict(metrics or {}),
            notes=notes,
            output_files=_remove_empty_strings(output_files or []),
            baseline_of=baseline_of,
            ablation_of=ablation_of,
            comparison_group=comparison_group,
            related_run_ids=_remove_empty_strings(related_run_ids or []),
            claim_ids=_remove_empty_strings(claim_ids or []),
            metadata=dict(metadata or {}),
        )
        now = utc_now()
        if experiment.status in {"running", "completed", "failed"}:
            experiment.started_at = now
        if experiment.status in {"completed", "failed", "cancelled"}:
            experiment.finished_at = now
        state.experiments.append(experiment)
        _append_unique(project.experiment_ids, experiment.id)
        self._touch(project)

        if workflow_id:
            workflow = self._workflow(state, workflow_id)
            _append_unique(workflow.experiment_ids, experiment.id)
            self._touch(workflow)

        for claim_id in experiment.claim_ids:
            claim = self._claim(state, claim_id)
            self._touch(claim)

        self._sync_experiment_output_artifacts(state, experiment)
        self._sync_experiment_completion_evidence(state, experiment)

        await self.save_state(state)
        return experiment

    async def update_experiment(
        self,
        *,
        experiment_id: str,
        status: str | None = None,
        parameters: dict[str, Any] | None = None,
        input_data: dict[str, Any] | None = None,
        metrics: dict[str, Any] | None = None,
        notes: str | None = None,
        output_files: list[str] | None = None,
        baseline_of: str | None = None,
        ablation_of: str | None = None,
        comparison_group: str | None = None,
        related_run_ids: list[str] | None = None,
        claim_ids: list[str] | None = None,
        note_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExperimentRun:
        state = await self.load_state()
        experiment = self._experiment(state, experiment_id)

        if status:
            experiment.status = status  # type: ignore[assignment]
        if parameters:
            merged_parameters = dict(experiment.parameters)
            merged_parameters.update(dict(parameters))
            experiment.parameters = merged_parameters
        if input_data:
            merged_input_data = dict(experiment.input_data)
            merged_input_data.update(dict(input_data))
            experiment.input_data = merged_input_data
        if metrics:
            merged_metrics = dict(experiment.metrics)
            merged_metrics.update(dict(metrics))
            experiment.metrics = merged_metrics
        if notes is not None:
            experiment.notes = notes
        if baseline_of is not None:
            experiment.baseline_of = baseline_of
        if ablation_of is not None:
            experiment.ablation_of = ablation_of
        if comparison_group is not None:
            experiment.comparison_group = comparison_group

        for output_file in _remove_empty_strings(output_files or []):
            _append_unique(experiment.output_files, output_file)
        for run_id in _remove_empty_strings(related_run_ids or []):
            _append_unique(experiment.related_run_ids, run_id)
        for claim_id in _remove_empty_strings(claim_ids or []):
            _append_unique(experiment.claim_ids, claim_id)
            claim = self._claim(state, claim_id)
            self._touch(claim)
        for note_id in _remove_empty_strings(note_ids or []):
            _append_unique(experiment.note_ids, note_id)
            note = self._note(state, note_id)
            _append_unique(note.experiment_ids, experiment.id)
            self._touch(note)

        if metadata:
            merged_metadata = dict(experiment.metadata)
            merged_metadata.update(dict(metadata))
            experiment.metadata = merged_metadata

        now = utc_now()
        if experiment.status in {"running", "completed", "failed"} and not experiment.started_at:
            experiment.started_at = now
        if experiment.status in {"completed", "failed", "cancelled"}:
            experiment.finished_at = now

        self._sync_experiment_output_artifacts(state, experiment)
        self._sync_experiment_completion_evidence(state, experiment)
        if experiment.status in {"completed", "failed", "cancelled"}:
            self._store_experiment_artifact_contract_validation(state, experiment)
        self._touch(experiment, now=now)
        await self.save_state(state)
        return experiment

    async def list_experiments(
        self,
        *,
        project_id: str = "",
        workflow_id: str = "",
        status: str = "",
        limit: int = 100,
    ) -> list[ExperimentRun]:
        state = await self.load_state()
        runs = list(state.experiments)
        if project_id:
            runs = [item for item in runs if item.project_id == project_id]
        if workflow_id:
            runs = [item for item in runs if item.workflow_id == workflow_id]
        if status:
            runs = [item for item in runs if item.status == status]
        runs.sort(
            key=lambda item: item.finished_at or item.started_at or item.created_at,
            reverse=True,
        )
        return runs[: max(1, int(limit))]

    async def compare_experiments(
        self,
        experiment_ids: list[str],
    ) -> dict[str, Any]:
        state = await self.load_state()
        selected = [
            item for item in state.experiments if item.id in set(experiment_ids)
        ]
        all_params: set[str] = set()
        all_metrics: set[str] = set()
        for run in selected:
            all_params.update(run.parameters.keys())
            all_metrics.update(run.metrics.keys())
        return {
            "experiment_ids": experiment_ids,
            "parameter_keys": sorted(all_params),
            "metric_keys": sorted(all_metrics),
            "runs": [
                {
                    "id": run.id,
                    "name": run.name,
                    "status": run.status,
                    "baseline_of": run.baseline_of,
                    "ablation_of": run.ablation_of,
                    "comparison_group": run.comparison_group,
                    "parameters": {
                        key: run.parameters.get(key) for key in sorted(all_params)
                    },
                    "metrics": {
                        key: run.metrics.get(key) for key in sorted(all_metrics)
                    },
                    "output_files": run.output_files,
                    "artifact_ids": run.artifact_ids,
                }
                for run in selected
            ],
        }

    # ---- proactive automation ----

    def _build_workflow_reminder(
        self,
        *,
        project: ResearchProject,
        workflow: ResearchWorkflow,
        reminder_type: str,
        title: str,
        summary: str,
        context: dict[str, Any] | None = None,
    ) -> ProactiveReminder:
        return ProactiveReminder(
            reminder_type=reminder_type,  # type: ignore[arg-type]
            project_id=project.id,
            workflow_id=workflow.id,
            stage=workflow.current_stage,
            title=title,
            summary=summary,
            binding=self._project_binding(project, workflow),
            context={
                "project_name": project.name,
                "workflow_title": workflow.title,
                "current_stage": workflow.current_stage,
                "goal": workflow.goal,
                **dict(context or {}),
            },
        )

    def _build_task_reminder(
        self,
        *,
        project: ResearchProject,
        workflow: ResearchWorkflow,
        task: WorkflowTask,
        reminder_type: str,
        title: str,
        summary: str,
        context: dict[str, Any] | None = None,
    ) -> ProactiveReminder:
        return ProactiveReminder(
            reminder_type=reminder_type,  # type: ignore[arg-type]
            project_id=project.id,
            workflow_id=workflow.id,
            task_id=task.id,
            stage=workflow.current_stage,
            title=title,
            summary=summary,
            binding=self._project_binding(project, workflow),
            context={
                "project_name": project.name,
                "workflow_title": workflow.title,
                "current_stage": workflow.current_stage,
                "goal": workflow.goal,
                "task_title": task.title,
                "task_assignee": task.assignee,
                "task_due_at": task.due_at,
                "task_status": task.status,
                "task_dispatch_count": task.dispatch_count,
                **dict(context or {}),
            },
        )

    def _workflow_contract_followup_context(
        self,
        state: ResearchState,
        workflow: ResearchWorkflow,
    ) -> dict[str, Any]:
        if workflow.current_stage != "experiment_run":
            return {}
        followup_task = next(
            (
                task
                for task in workflow.tasks
                if task.stage == "experiment_run"
                and str(task.metadata.get("task_kind", "") or "").strip()
                == "experiment_contract_followup"
            ),
            None,
        )
        remediation_tasks = [
            task
            for task in workflow.tasks
            if task.stage == "experiment_run"
            and str(task.metadata.get("task_kind", "") or "").strip()
            == "experiment_contract_remediation"
        ]
        if followup_task is None and workflow.status != "blocked":
            return {}
        preferred_run_ids = _remove_empty_strings(
            list(
                dict(getattr(followup_task, "metadata", {}) or {}).get(
                    "contract_failure_run_ids",
                    [],
                )
                or [],
            ),
        )
        experiments = [
            item
            for item in state.experiments
            if item.workflow_id == workflow.id
            and (
                not preferred_run_ids
                or item.id in set(preferred_run_ids)
            )
        ]
        contract_failures: list[dict[str, Any]] = []
        remediation_actions: list[dict[str, Any]] = []
        remediation_task_rows = [
            {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "assignee": task.assignee,
                "action_type": str(task.metadata.get("action_type", "") or ""),
                "target": str(task.metadata.get("target", "") or ""),
                "suggested_tool": str(task.metadata.get("suggested_tool", "") or ""),
                "due_at": task.due_at,
                "dispatch_count": task.dispatch_count,
                "last_dispatch_at": task.last_dispatch_at,
                "last_dispatch_summary": task.last_dispatch_summary,
                "last_dispatch_error": task.last_dispatch_error,
                "execution_count": task.execution_count,
                "last_execution_at": task.last_execution_at,
                "last_execution_summary": task.last_execution_summary,
                "last_execution_error": task.last_execution_error,
                "max_attempts": self._task_retry_policy(task)[0],
                "can_dispatch": self._eligible_for_task_dispatch(task=task, now=datetime.now(timezone.utc)),
                "can_execute": (
                    str(task.assignee or "").strip() == "agent"
                    and task.status not in {"completed", "cancelled"}
                ),
                "summary": task.summary,
                "remediation_key": str(task.metadata.get("remediation_key", "") or ""),
            }
            for task in remediation_tasks
        ]
        exhausted_tasks = [
            task
            for task in remediation_task_rows
            if int(task.get("dispatch_count") or 0) >= int(task.get("max_attempts") or 1)
        ]
        missing_metric_count = 0
        missing_output_count = 0
        missing_artifact_type_count = 0
        for experiment in experiments:
            validation = self._evaluate_experiment_artifact_contract(state, experiment)
            if not validation.get("enabled") or validation.get("passed", True):
                continue
            remediation = dict(validation.get("remediation") or {})
            missing_metrics = list(validation.get("missing_metrics", []) or [])
            missing_outputs = list(validation.get("missing_outputs", []) or [])
            missing_artifact_types = list(
                validation.get("missing_artifact_types", []) or [],
            )
            missing_metric_count += len(missing_metrics)
            missing_output_count += len(missing_outputs)
            missing_artifact_type_count += len(missing_artifact_types)
            contract_failures.append(
                {
                    "experiment_id": experiment.id,
                    "experiment_name": experiment.name,
                    "summary": validation.get("summary", ""),
                    "missing_metrics": missing_metrics,
                    "missing_outputs": missing_outputs,
                    "missing_artifact_types": missing_artifact_types,
                    "remediation": remediation,
                },
            )
            for action in list(remediation.get("actions", []) or []):
                if not isinstance(action, dict):
                    continue
                remediation_actions.append(action)
        if not contract_failures:
            if not followup_task and not remediation_tasks:
                return {}
            ready = all(
                task.status in {"completed", "cancelled"}
                for task in remediation_tasks
            )
            remediation_summary = (
                "All experiment contract remediation items are resolved."
                if ready
                else "Contract remediation tasks remain open."
            )
            if exhausted_tasks and not ready:
                remediation_summary = " ".join(
                    [
                        remediation_summary,
                        f"{len(exhausted_tasks)} remediation task(s) exhausted retry budget.",
                    ],
                ).strip()
            return {
                "contract_failures": [],
                "remediation_summary": remediation_summary,
                "remediation_actions": [],
                "blocked_task_id": getattr(followup_task, "id", ""),
                "blocked_task_title": getattr(followup_task, "title", ""),
                "remediation_tasks": remediation_task_rows,
                "ready_for_retry": ready,
                "retry_exhausted_count": len(exhausted_tasks),
                "retry_exhausted_tasks": exhausted_tasks,
            }
        remediation_summary = (
            f"{len(contract_failures)} run(s) need remediation: "
            f"{missing_metric_count} missing metric(s), "
            f"{missing_output_count} missing output file(s), "
            f"{missing_artifact_type_count} missing artifact type(s)."
        )
        if exhausted_tasks:
            remediation_summary = " ".join(
                [
                    remediation_summary,
                    f"{len(exhausted_tasks)} remediation task(s) exhausted retry budget.",
                ],
            ).strip()
        return {
            "contract_failures": contract_failures,
            "remediation_summary": remediation_summary,
            "remediation_actions": remediation_actions[:10],
            "blocked_task_id": getattr(followup_task, "id", ""),
            "blocked_task_title": getattr(followup_task, "title", ""),
            "remediation_tasks": remediation_task_rows,
            "ready_for_retry": False,
            "retry_exhausted_count": len(exhausted_tasks),
            "retry_exhausted_tasks": exhausted_tasks,
        }

    @staticmethod
    def _eligible_for_reminder(
        *,
        last_reminder_at: str | None,
        now: datetime,
        cooldown_hours: int = 6,
    ) -> bool:
        hours = _hours_since(last_reminder_at, now=now)
        return hours is None or hours >= cooldown_hours

    @staticmethod
    def _task_retry_policy(task: WorkflowTask) -> tuple[int, int]:
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
    def _eligible_for_task_dispatch(
        cls,
        *,
        task: WorkflowTask,
        now: datetime,
    ) -> bool:
        if task.status not in {"pending", "blocked", "running"}:
            return False
        max_attempts, backoff_minutes = cls._task_retry_policy(task)
        if int(getattr(task, "dispatch_count", 0) or 0) >= max_attempts:
            return False
        hours = _hours_since(getattr(task, "last_dispatch_at", None), now=now)
        if hours is None:
            return True
        return hours * 60 >= backoff_minutes

    async def preview_due_reminders(
        self,
        *,
        project_id: str = "",
        stale_hours: int = 24,
    ) -> list[ProactiveReminder]:
        state = await self.load_state()
        now = datetime.now(timezone.utc)
        reminders: list[ProactiveReminder] = []

        projects = state.projects
        if project_id:
            projects = [item for item in projects if item.id == project_id]

        for project in projects:
            workflows = [
                item
                for item in state.workflows
                if item.project_id == project.id
                and item.status in {"running", "blocked", "paused"}
            ]
            for workflow in workflows:
                stage_tasks = self._stage_task_list(workflow, workflow.current_stage)
                pending_tasks = [
                    task
                    for task in stage_tasks
                    if task.status in {"pending", "running", "blocked"}
                ]
                age_hours = _hours_since(
                    workflow.last_run_at or workflow.updated_at,
                    now=now,
                ) or 0.0
                if workflow.status == "blocked":
                    contract_context = self._workflow_contract_followup_context(
                        state,
                        workflow,
                    )
                    summary = (
                        f"Project {project.name} is blocked in "
                        f"{workflow.current_stage}. "
                        f"Reason: {workflow.error or 'manual follow-up needed'}."
                    )
                    if contract_context:
                        summary = " ".join(
                            [
                                summary,
                                str(
                                    contract_context.get(
                                        "remediation_summary",
                                        "",
                                    )
                                    or "",
                                ).strip(),
                            ],
                        ).strip()
                    reminders.append(
                        self._build_workflow_reminder(
                            project=project,
                            workflow=workflow,
                            reminder_type="stage_stuck_followup",
                            title=f"Stage stuck: {workflow.title}",
                            summary=summary,
                            context=contract_context,
                        ),
                    )
                    for task in stage_tasks:
                        if (
                            str(task.metadata.get("task_kind", "") or "").strip()
                            != "experiment_contract_remediation"
                        ):
                            continue
                        if not self._eligible_for_task_dispatch(task=task, now=now):
                            continue
                        metadata = dict(task.metadata or {})
                        payload_hint = dict(metadata.get("payload_hint", {}) or {})
                        suggested_tool = str(metadata.get("suggested_tool", "") or "").strip()
                        max_attempts, backoff_minutes = self._task_retry_policy(task)
                        task_summary = " ".join(
                            part
                            for part in [
                                (
                                    f"Assignee {task.assignee} should resolve "
                                    f"'{task.title}'."
                                ),
                                str(task.summary or task.description or "").strip(),
                                f"Use {suggested_tool}." if suggested_tool else "",
                                f"Dispatch attempt {task.dispatch_count + 1}/{max_attempts}.",
                            ]
                            if part
                        ).strip()
                        reminders.append(
                            self._build_task_reminder(
                                project=project,
                                workflow=workflow,
                                task=task,
                                reminder_type="remediation_task_followup",
                                title=f"Remediation task: {task.title}",
                                summary=task_summary,
                                context={
                                    "suggested_tool": suggested_tool,
                                    "payload_hint": payload_hint,
                                    "task_backoff_minutes": backoff_minutes,
                                    "task_max_attempts": max_attempts,
                                },
                            ),
                        )
                    continue
                if workflow.current_stage == "writing_tasks" and pending_tasks:
                    reminders.append(
                        self._build_workflow_reminder(
                            project=project,
                            workflow=workflow,
                            reminder_type="writing_todo",
                            title=f"Writing follow-up: {workflow.title}",
                            summary=(
                                f"{len(pending_tasks)} writing task(s) are still open "
                                f"for project {project.name}."
                            ),
                        ),
                    )
                    continue
                if age_hours >= stale_hours:
                    reminders.append(
                        self._build_workflow_reminder(
                            project=project,
                            workflow=workflow,
                            reminder_type="workflow_timeout",
                            title=f"Workflow idle: {workflow.title}",
                            summary=(
                                f"Project {project.name} has not advanced workflow "
                                f"{workflow.title} for about {int(age_hours)} hour(s)."
                            ),
                        ),
                    )

            experiments = [
                item
                for item in state.experiments
                if item.project_id == project.id and item.status == "completed"
            ]
            for experiment in experiments:
                validation = self._evaluate_experiment_artifact_contract(
                    state,
                    experiment,
                )
                if validation.get("enabled") and not validation.get("passed", True):
                    continue
                if not self._eligible_for_reminder(
                    last_reminder_at=experiment.last_reminder_at,
                    now=now,
                ):
                    continue
                reminders.append(
                    ProactiveReminder(
                        reminder_type="experiment_complete",
                        project_id=project.id,
                        experiment_id=experiment.id,
                        title=f"Experiment completed: {experiment.name}",
                        summary=(
                            f"Experiment {experiment.name} finished with "
                            f"{len(experiment.metrics)} metric(s) and "
                            f"{len(experiment.output_files)} archived output file(s)."
                        ),
                        binding=self._project_binding(project),
                        context={
                            "project_name": project.name,
                            "metrics": experiment.metrics,
                            "workflow_id": experiment.workflow_id,
                        },
                    ),
                )

        return reminders

    def _search_papers(
        self,
        *,
        source: str,
        query: str,
        max_results: int,
    ) -> list[dict[str, Any]]:
        if source == "semantic_scholar":
            from researchclaw.agents.tools.semantic_scholar import (
                semantic_scholar_search,
            )

            return semantic_scholar_search(query=query, max_results=max_results)

        from researchclaw.agents.skills.arxiv.tools import arxiv_search

        return arxiv_search(query=query, max_results=max_results)

    async def generate_proactive_reminders(
        self,
        *,
        project_id: str = "",
        stale_hours: int = 24,
    ) -> list[ProactiveReminder]:
        state = await self.load_state()
        now = datetime.now(timezone.utc)
        now_iso = utc_now()
        reminders = await self.preview_due_reminders(
            project_id=project_id,
            stale_hours=stale_hours,
        )

        projects = state.projects
        if project_id:
            projects = [item for item in projects if item.id == project_id]

        emitted_workflow_ids = {item.workflow_id for item in reminders if item.workflow_id}
        emitted_experiment_ids = {item.experiment_id for item in reminders if item.experiment_id}
        emitted_task_ids = {item.task_id for item in reminders if item.task_id}

        for project in projects:
            for workflow in state.workflows:
                if workflow.project_id != project.id:
                    continue
                if workflow.id in emitted_workflow_ids and self._eligible_for_reminder(
                    last_reminder_at=workflow.last_reminder_at,
                    now=now,
                ):
                    workflow.last_reminder_at = now_iso
                    self._touch(workflow, now=now_iso)
                for task in workflow.tasks:
                    if task.id not in emitted_task_ids:
                        continue
                    task.dispatch_count = max(0, int(task.dispatch_count or 0)) + 1
                    task.last_dispatch_at = now_iso
                    task.last_dispatch_summary = "Proactive remediation dispatch emitted."
                    task.last_dispatch_error = ""
                    task.updated_at = now_iso
                    self._touch(workflow, now=now_iso)

            for experiment in state.experiments:
                if experiment.project_id != project.id:
                    continue
                if experiment.id in emitted_experiment_ids:
                    experiment.last_reminder_at = now_iso
                    self._touch(experiment, now=now_iso)

            for watch in project.paper_watches:
                last_checked = _parse_iso(watch.last_checked_at)
                if (
                    last_checked is not None
                    and now - last_checked < timedelta(hours=max(1, watch.check_every_hours))
                ):
                    continue
                results = self._search_papers(
                    source=watch.source,
                    query=watch.query,
                    max_results=max(1, watch.max_results),
                )
                watch.last_checked_at = now_iso
                watch.last_error = ""
                watch.last_result_count = len(results)
                clean_results = [
                    item for item in results if isinstance(item, dict) and not item.get("error")
                ]
                seen = set(watch.seen_paper_ids)
                new_items: list[dict[str, Any]] = []
                for item in clean_results:
                    paper_id = str(
                        item.get("arxiv_id")
                        or item.get("paper_id")
                        or item.get("doi")
                        or item.get("title")
                        or ""
                    ).strip()
                    if not paper_id:
                        continue
                    if paper_id not in seen:
                        new_items.append(item)
                    seen.add(paper_id)
                if new_items:
                    watch.seen_paper_ids = list(seen)
                    for item in new_items:
                        paper_ref = str(
                            item.get("arxiv_id")
                            or item.get("paper_id")
                            or item.get("doi")
                            or ""
                        ).strip()
                        _append_unique(project.paper_refs, paper_ref)
                    preview = "; ".join(
                        str(item.get("title", "") or "").strip()
                        for item in new_items[:3]
                        if str(item.get("title", "") or "").strip()
                    )
                    reminders.append(
                        ProactiveReminder(
                            reminder_type="new_paper_tracking",
                            project_id=project.id,
                            title=f"New papers for {project.name}",
                            summary=(
                                f"Watch query '{watch.query}' found {len(new_items)} new paper(s). "
                                f"{preview}"
                            ).strip(),
                            binding=self._project_binding(project),
                            context={
                                "project_name": project.name,
                                "watch_query": watch.query,
                                "new_items": new_items[:10],
                            },
                        ),
                    )
                elif results and isinstance(results[0], dict) and results[0].get("error"):
                    watch.last_error = str(results[0].get("error", ""))
                self._touch(project, now=now_iso)

        await self.save_state(state)
        return reminders

    async def get_runtime_stats(self) -> dict[str, Any]:
        overview = await self.get_overview()
        preview = await self.preview_due_reminders()
        return {
            **overview["counts"],
            "due_reminders": len(preview),
            "state_path": str(self.path),
        }
