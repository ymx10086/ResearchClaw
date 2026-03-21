"""Structured schemas for ResearchClaw's long-running research system."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> str:
    """Return an ISO-8601 timestamp in UTC."""
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    """Build a stable prefixed identifier."""
    return f"{prefix}_{uuid4().hex[:12]}"


WORKFLOW_STAGES: tuple[str, ...] = (
    "literature_search",
    "paper_reading",
    "note_synthesis",
    "hypothesis_queue",
    "experiment_plan",
    "experiment_run",
    "result_analysis",
    "writing_tasks",
    "review_and_followup",
)

WorkflowStageName = Literal[
    "literature_search",
    "paper_reading",
    "note_synthesis",
    "hypothesis_queue",
    "experiment_plan",
    "experiment_run",
    "result_analysis",
    "writing_tasks",
    "review_and_followup",
]
WorkflowStatus = Literal[
    "draft",
    "queued",
    "running",
    "paused",
    "blocked",
    "completed",
    "cancelled",
    "failed",
]
WorkflowStageStatus = Literal[
    "pending",
    "running",
    "blocked",
    "completed",
    "skipped",
]
WorkflowTaskStatus = Literal[
    "pending",
    "running",
    "blocked",
    "completed",
    "cancelled",
    "failed",
]
WorkflowExecutionMode = Literal["stale_only", "stale_or_blocked"]
ProjectStatus = Literal["active", "on_hold", "completed", "archived"]
NoteType = Literal[
    "paper_note",
    "idea_note",
    "experiment_note",
    "writing_note",
    "decision_log",
]
ClaimStatus = Literal["draft", "supported", "needs_review", "disputed"]
EvidenceType = Literal[
    "paper",
    "pdf_chunk",
    "citation",
    "note",
    "experiment_result",
    "generated_table",
    "generated_figure",
    "artifact",
]
ArtifactType = Literal[
    "paper",
    "pdf_chunk",
    "citation",
    "note",
    "experiment_result",
    "generated_table",
    "generated_figure",
    "draft",
    "summary",
    "analysis",
]
ExperimentStatus = Literal[
    "planned",
    "running",
    "completed",
    "failed",
    "cancelled",
]
ExperimentExecutionMode = Literal[
    "inline",
    "command",
    "notebook",
    "external",
    "file_watch",
]
ExperimentEventType = Literal[
    "binding",
    "status",
    "heartbeat",
    "artifact",
    "metric",
    "note",
    "completion",
    "failure",
]
ReminderType = Literal[
    "new_paper_tracking",
    "workflow_timeout",
    "experiment_complete",
    "writing_todo",
    "stage_stuck_followup",
    "remediation_task_followup",
]


class WorkflowBinding(BaseModel):
    """Runtime bindings that connect a workflow to external surfaces."""

    agent_id: str = "main"
    channel: str = "console"
    user_id: str = "main"
    session_id: str = "main"
    cron_job_id: str = ""
    automation_run_ids: list[str] = Field(default_factory=list)
    last_dispatch_at: str | None = None
    last_summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowExecutionPolicy(BaseModel):
    """Guardrails for proactive workflow auto-advancement."""

    enabled: bool = False
    mode: WorkflowExecutionMode = "stale_only"
    stale_hours: int = 24
    cooldown_minutes: int = 120
    max_auto_runs_per_day: int = 4
    allowed_stages: list[WorkflowStageName] = Field(
        default_factory=lambda: list(WORKFLOW_STAGES),
    )
    notify_after_execution: bool = True
    last_auto_run_at: str | None = None
    last_auto_run_reason: str = ""
    last_auto_run_note_id: str = ""
    auto_run_window_started_at: str | None = None
    auto_run_count_in_window: int = 0


class ExperimentRunnerTemplate(BaseModel):
    """Template used to attach execution bindings to planned experiments."""

    catalog_entry: str = ""
    mode: ExperimentExecutionMode = "inline"
    command: list[str] = Field(default_factory=list)
    entrypoint: str = ""
    working_dir: str = ""
    notebook_path: str = ""
    result_bundle_file: str = ""
    result_bundle_schema: str = ""
    environment: dict[str, str] = Field(default_factory=dict)
    requested_by: str = ""
    instructions: str = ""
    parameter_overrides: dict[str, Any] = Field(default_factory=dict)
    input_data_overrides: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentRunnerRule(BaseModel):
    """Ordered selection rule that refines runner templates for planned runs."""

    name: str
    stages: list[WorkflowStageName] = Field(default_factory=list)
    experiment_kinds: list[str] = Field(default_factory=list)
    comparison_groups: list[str] = Field(default_factory=list)
    hypothesis_kinds: list[str] = Field(default_factory=list)
    template: ExperimentRunnerTemplate = Field(
        default_factory=ExperimentRunnerTemplate,
    )


class ExperimentRunnerProfile(BaseModel):
    """Project/workflow-level defaults for future experiment runs."""

    enabled: bool = False
    default: ExperimentRunnerTemplate = Field(
        default_factory=ExperimentRunnerTemplate,
    )
    kind_overrides: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
    )
    rules: list[ExperimentRunnerRule] = Field(default_factory=list)


class ExperimentExecutionCatalogEntry(BaseModel):
    """Named execution preset reusable across workflows in the same project."""

    name: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    template: ExperimentRunnerTemplate = Field(
        default_factory=ExperimentRunnerTemplate,
    )
    artifact_contract: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResultBundleSchemaDefinition(BaseModel):
    """Project-level registry entry describing expected result bundle structure."""

    name: str
    description: str = ""
    required_sections: list[str] = Field(default_factory=list)
    required_metrics: list[str] = Field(default_factory=list)
    required_outputs: list[str] = Field(default_factory=list)
    required_artifact_types: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectPaperWatch(BaseModel):
    """A saved search used for proactive new-paper tracking."""

    id: str = Field(default_factory=lambda: new_id("watch"))
    query: str
    source: Literal["arxiv", "semantic_scholar"] = "arxiv"
    max_results: int = 5
    check_every_hours: int = 12
    seen_paper_ids: list[str] = Field(default_factory=list)
    last_checked_at: str | None = None
    last_result_count: int = 0
    last_error: str = ""


class WorkflowTask(BaseModel):
    """A concrete unit of work inside a workflow stage."""

    id: str = Field(default_factory=lambda: new_id("task"))
    stage: WorkflowStageName
    title: str
    description: str = ""
    status: WorkflowTaskStatus = "pending"
    depends_on: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    note_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    assignee: str = "agent"
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    completed_at: str | None = None
    due_at: str | None = None
    dispatch_count: int = 0
    last_dispatch_at: str | None = None
    last_dispatch_summary: str = ""
    last_dispatch_error: str = ""
    execution_count: int = 0
    last_execution_at: str | None = None
    last_execution_summary: str = ""
    last_execution_error: str = ""
    summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowStageState(BaseModel):
    """Runtime state for a stage in the research workflow."""

    name: WorkflowStageName
    status: WorkflowStageStatus = "pending"
    summary: str = ""
    task_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None
    blocked_reason: str = ""
    updated_at: str = Field(default_factory=utc_now)


class ResearchArtifact(BaseModel):
    """A durable artifact generated or referenced by the research system."""

    id: str = Field(default_factory=lambda: new_id("artifact"))
    project_id: str
    workflow_id: str = ""
    title: str
    artifact_type: ArtifactType
    description: str = ""
    path: str = ""
    uri: str = ""
    source_type: str = ""
    source_id: str = ""
    experiment_id: str = ""
    note_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class ResearchWorkflow(BaseModel):
    """A long-running research workflow with structured state."""

    id: str = Field(default_factory=lambda: new_id("workflow"))
    project_id: str
    title: str
    goal: str = ""
    status: WorkflowStatus = "draft"
    current_stage: WorkflowStageName = "literature_search"
    stages: list[WorkflowStageState] = Field(default_factory=list)
    tasks: list[WorkflowTask] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    note_ids: list[str] = Field(default_factory=list)
    experiment_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    bindings: WorkflowBinding = Field(default_factory=WorkflowBinding)
    execution_policy: WorkflowExecutionPolicy = Field(
        default_factory=WorkflowExecutionPolicy,
    )
    experiment_runner: ExperimentRunnerProfile = Field(
        default_factory=ExperimentRunnerProfile,
    )
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    started_at: str | None = None
    completed_at: str | None = None
    paused_at: str | None = None
    last_run_at: str | None = None
    last_transition_at: str | None = None
    last_reminder_at: str | None = None
    error: str = ""
    retry_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchNote(BaseModel):
    """A structured note linked to the research graph."""

    id: str = Field(default_factory=lambda: new_id("note"))
    project_id: str
    title: str
    content: str
    note_type: NoteType = "idea_note"
    workflow_id: str = ""
    experiment_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    paper_refs: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class ResearchClaim(BaseModel):
    """A claim that should be backed by explicit evidence."""

    id: str = Field(default_factory=lambda: new_id("claim"))
    project_id: str
    text: str
    workflow_id: str = ""
    status: ClaimStatus = "draft"
    confidence: float | None = None
    note_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class EvidenceSource(BaseModel):
    """Source information for a piece of evidence."""

    source_type: EvidenceType
    source_id: str = ""
    title: str = ""
    locator: str = ""
    quote: str = ""
    url: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchEvidence(BaseModel):
    """Evidence attached to one or more claims."""

    id: str = Field(default_factory=lambda: new_id("evidence"))
    project_id: str
    evidence_type: EvidenceType
    summary: str
    claim_ids: list[str] = Field(default_factory=list)
    workflow_id: str = ""
    artifact_id: str = ""
    note_id: str = ""
    experiment_id: str = ""
    source: EvidenceSource
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class ExperimentExecutionBinding(BaseModel):
    """Execution metadata for external or delegated experiment runs."""

    mode: ExperimentExecutionMode = "inline"
    command: list[str] = Field(default_factory=list)
    entrypoint: str = ""
    working_dir: str = ""
    notebook_path: str = ""
    result_bundle_file: str = ""
    result_bundle_schema: str = ""
    environment: dict[str, str] = Field(default_factory=dict)
    external_run_id: str = ""
    requested_by: str = ""
    instructions: str = ""
    submitted_at: str | None = None
    last_heartbeat_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentRun(BaseModel):
    """A tracked experiment run linked to workflows and claims."""

    id: str = Field(default_factory=lambda: new_id("run"))
    project_id: str
    name: str
    workflow_id: str = ""
    status: ExperimentStatus = "planned"
    parameters: dict[str, Any] = Field(default_factory=dict)
    input_data: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""
    output_files: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    note_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    baseline_of: str = ""
    ablation_of: str = ""
    comparison_group: str = ""
    related_run_ids: list[str] = Field(default_factory=list)
    execution: ExperimentExecutionBinding = Field(
        default_factory=ExperimentExecutionBinding,
    )
    created_at: str = Field(default_factory=utc_now)
    started_at: str | None = None
    finished_at: str | None = None
    last_reminder_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentEvent(BaseModel):
    """Immutable timeline event for an experiment run."""

    id: str = Field(default_factory=lambda: new_id("exp_event"))
    experiment_id: str
    project_id: str
    workflow_id: str = ""
    event_type: ExperimentEventType
    summary: str
    status: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)
    output_files: list[str] = Field(default_factory=list)
    note_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)


class ResearchProject(BaseModel):
    """Long-lived project container for related research entities."""

    id: str = Field(default_factory=lambda: new_id("project"))
    name: str
    description: str = ""
    status: ProjectStatus = "active"
    tags: list[str] = Field(default_factory=list)
    workflow_ids: list[str] = Field(default_factory=list)
    note_ids: list[str] = Field(default_factory=list)
    experiment_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    paper_refs: list[str] = Field(default_factory=list)
    paper_watches: list[ProjectPaperWatch] = Field(default_factory=list)
    execution_catalog: list[ExperimentExecutionCatalogEntry] = Field(
        default_factory=list,
    )
    result_bundle_schemas: list[ResultBundleSchemaDefinition] = Field(
        default_factory=list,
    )
    default_binding: WorkflowBinding = Field(default_factory=WorkflowBinding)
    default_experiment_runner: ExperimentRunnerProfile = Field(
        default_factory=ExperimentRunnerProfile,
    )
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProactiveReminder(BaseModel):
    """A reminder emitted by the proactive runtime."""

    id: str = Field(default_factory=lambda: new_id("reminder"))
    reminder_type: ReminderType
    project_id: str
    title: str
    summary: str
    workflow_id: str = ""
    experiment_id: str = ""
    task_id: str = ""
    stage: str = ""
    binding: WorkflowBinding = Field(default_factory=WorkflowBinding)
    created_at: str = Field(default_factory=utc_now)
    context: dict[str, Any] = Field(default_factory=dict)


class ResearchState(BaseModel):
    """Persistent state for research projects, workflows, and linked data."""

    version: int = 1
    projects: list[ResearchProject] = Field(default_factory=list)
    workflows: list[ResearchWorkflow] = Field(default_factory=list)
    notes: list[ResearchNote] = Field(default_factory=list)
    claims: list[ResearchClaim] = Field(default_factory=list)
    evidences: list[ResearchEvidence] = Field(default_factory=list)
    experiments: list[ExperimentRun] = Field(default_factory=list)
    experiment_events: list[ExperimentEvent] = Field(default_factory=list)
    artifacts: list[ResearchArtifact] = Field(default_factory=list)
