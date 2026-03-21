"""Research workflow and project APIs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from researchclaw.constant import RESEARCH_WORKFLOW_STALE_HOURS

router = APIRouter()


def _get_research_service(req: Request):
    service = getattr(req.app.state, "research_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Research service not initialized")
    return service


def _get_research_runtime(req: Request):
    runtime = getattr(req.app.state, "research_runtime", None)
    if runtime is None:
        raise HTTPException(status_code=503, detail="Research runtime not initialized")
    return runtime


def _translate_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, HTTPException):
        return exc
    if isinstance(exc, ValueError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    default_binding: dict[str, Any] = Field(default_factory=dict)
    execution_catalog: list[dict[str, Any]] = Field(default_factory=list)
    result_bundle_schemas: list[dict[str, Any]] = Field(default_factory=list)
    default_experiment_runner: dict[str, Any] = Field(default_factory=dict)
    paper_watches: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectUpdateRequest(BaseModel):
    description: str | None = None
    status: str | None = None
    tags: list[str] | None = None
    default_binding: dict[str, Any] = Field(default_factory=dict)
    execution_catalog: list[dict[str, Any]] | None = None
    result_bundle_schemas: list[dict[str, Any]] | None = None
    default_experiment_runner: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PaperWatchCreateRequest(BaseModel):
    query: str = Field(..., min_length=1)
    source: str = "arxiv"
    max_results: int = 5
    check_every_hours: int = 12


class WorkflowCreateRequest(BaseModel):
    project_id: str
    title: str = Field(..., min_length=1)
    goal: str = ""
    bindings: dict[str, Any] = Field(default_factory=dict)
    execution_policy: dict[str, Any] = Field(default_factory=dict)
    experiment_runner: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    auto_start: bool = True


class WorkflowTaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = ""
    stage: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    due_at: str | None = None
    assignee: str = "agent"
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowTaskUpdateRequest(BaseModel):
    status: str | None = None
    summary: str | None = None
    due_at: str | None = None
    note_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)


class NoteCreateRequest(BaseModel):
    project_id: str
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    note_type: str = "idea_note"
    workflow_id: str = ""
    experiment_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    paper_refs: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactUpsertRequest(BaseModel):
    project_id: str
    title: str = Field(..., min_length=1)
    artifact_type: str
    workflow_id: str = ""
    description: str = ""
    path: str = ""
    uri: str = ""
    source_type: str = ""
    source_id: str = ""
    experiment_id: str = ""
    note_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClaimCreateRequest(BaseModel):
    project_id: str
    text: str = Field(..., min_length=1)
    workflow_id: str = ""
    status: str = "draft"
    confidence: float | None = None
    note_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceCreateRequest(BaseModel):
    project_id: str
    claim_ids: list[str] = Field(default_factory=list)
    evidence_type: str
    summary: str = Field(..., min_length=1)
    source_type: str
    source_id: str = ""
    title: str = ""
    locator: str = ""
    quote: str = ""
    url: str = ""
    workflow_id: str = ""
    artifact_id: str = ""
    note_id: str = ""
    experiment_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentCreateRequest(BaseModel):
    project_id: str
    name: str = Field(..., min_length=1)
    workflow_id: str = ""
    status: str = "planned"
    parameters: dict[str, Any] = Field(default_factory=dict)
    input_data: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""
    output_files: list[str] = Field(default_factory=list)
    baseline_of: str = ""
    ablation_of: str = ""
    comparison_group: str = ""
    related_run_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentUpdateRequest(BaseModel):
    status: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    input_data: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None
    output_files: list[str] = Field(default_factory=list)
    baseline_of: str | None = None
    ablation_of: str | None = None
    comparison_group: str | None = None
    related_run_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    note_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentExecutionConfigureRequest(BaseModel):
    mode: str | None = None
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
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentHeartbeatRequest(BaseModel):
    summary: str = Field(..., min_length=1)
    status: str = "running"
    metrics: dict[str, Any] = Field(default_factory=dict)
    output_files: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentResultRequest(BaseModel):
    summary: str = ""
    status: str = "completed"
    metrics: dict[str, Any] = Field(default_factory=dict)
    output_files: list[str] = Field(default_factory=list)
    notes: str | None = None
    note_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CompareExperimentsRequest(BaseModel):
    experiment_ids: list[str] = Field(default_factory=list)


class ReminderRunRequest(BaseModel):
    project_id: str = ""
    stale_hours: int = RESEARCH_WORKFLOW_STALE_HOURS


class WorkflowExecuteRequest(BaseModel):
    agent_id: str = ""
    session_id: str = ""


class WorkflowExecutionPolicyUpdateRequest(BaseModel):
    enabled: bool | None = None
    mode: str | None = None
    stale_hours: int | None = None
    cooldown_minutes: int | None = None
    max_auto_runs_per_day: int | None = None
    allowed_stages: list[str] | None = None
    notify_after_execution: bool | None = None


class ExperimentRunnerProfileUpdateRequest(BaseModel):
    enabled: bool | None = None
    default: dict[str, Any] = Field(default_factory=dict)
    kind_overrides: dict[str, dict[str, Any] | None] = Field(default_factory=dict)
    rules: list[dict[str, Any]] | None = None


@router.get("/overview")
async def overview(req: Request):
    service = _get_research_service(req)
    return await service.get_overview()


@router.get("/projects")
async def list_projects(req: Request):
    service = _get_research_service(req)
    return await service.list_projects()


@router.post("/projects")
async def create_project(payload: ProjectCreateRequest, req: Request):
    service = _get_research_service(req)
    try:
        return await service.create_project(**payload.model_dump(mode="json"))
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.get("/projects/{project_id}")
async def get_project(project_id: str, req: Request):
    service = _get_research_service(req)
    try:
        return await service.get_project(project_id)
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.patch("/projects/{project_id}")
async def update_project(project_id: str, payload: ProjectUpdateRequest, req: Request):
    service = _get_research_service(req)
    try:
        return await service.update_project(
            project_id=project_id,
            **payload.model_dump(
                mode="json",
                exclude_none=True,
                exclude_unset=True,
            ),
        )
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.get("/projects/{project_id}/dashboard")
async def project_dashboard(project_id: str, req: Request):
    service = _get_research_service(req)
    try:
        return await service.get_project_dashboard(project_id)
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.post("/projects/{project_id}/blockers/dispatch")
async def dispatch_project_blockers(
    project_id: str,
    req: Request,
    workflow_limit: int = Query(3, ge=1, le=20),
    task_limit: int = Query(2, ge=1, le=10),
):
    runtime = _get_research_runtime(req)
    try:
        return await runtime.dispatch_project_blocker_tasks(
            project_id,
            workflow_limit=workflow_limit,
            task_limit=task_limit,
        )
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.post("/projects/{project_id}/blockers/execute")
async def execute_project_blockers(
    project_id: str,
    req: Request,
    workflow_limit: int = Query(3, ge=1, le=20),
    task_limit: int = Query(2, ge=1, le=10),
):
    runtime = _get_research_runtime(req)
    try:
        return await runtime.execute_project_blocker_tasks(
            project_id,
            workflow_limit=workflow_limit,
            task_limit=task_limit,
        )
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.post("/projects/{project_id}/blockers/resume")
async def resume_project_blockers(
    project_id: str,
    req: Request,
    workflow_limit: int = Query(3, ge=1, le=20),
):
    runtime = _get_research_runtime(req)
    try:
        return await runtime.resume_project_ready_workflows(
            project_id,
            workflow_limit=workflow_limit,
        )
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.post("/projects/{project_id}/paper-watches")
async def add_project_paper_watch(
    project_id: str,
    payload: PaperWatchCreateRequest,
    req: Request,
):
    service = _get_research_service(req)
    try:
        return await service.add_project_paper_watch(project_id=project_id, **payload.model_dump(mode="json"))
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.get("/workflows")
async def list_workflows(
    req: Request,
    project_id: str = Query("", description="Filter by project ID"),
    status: str = Query("", description="Filter by workflow status"),
):
    service = _get_research_service(req)
    return await service.list_workflows(project_id=project_id, status=status)


@router.post("/workflows")
async def create_workflow(payload: WorkflowCreateRequest, req: Request):
    service = _get_research_service(req)
    try:
        return await service.create_workflow(**payload.model_dump(mode="json"))
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str, req: Request):
    service = _get_research_service(req)
    try:
        return await service.get_workflow(workflow_id)
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.get("/workflows/{workflow_id}/remediation")
async def get_workflow_contract_remediation(workflow_id: str, req: Request):
    service = _get_research_service(req)
    try:
        return await service.get_workflow_contract_remediation_context(workflow_id)
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.post("/workflows/{workflow_id}/remediation/dispatch")
async def dispatch_workflow_remediation(
    workflow_id: str,
    req: Request,
    limit: int = Query(3, ge=1, le=10),
):
    runtime = _get_research_runtime(req)
    try:
        return await runtime.dispatch_workflow_remediation_tasks(
            workflow_id,
            limit=limit,
        )
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.post("/workflows/{workflow_id}/remediation/execute")
async def execute_workflow_remediation(
    workflow_id: str,
    req: Request,
    limit: int = Query(3, ge=1, le=10),
):
    runtime = _get_research_runtime(req)
    try:
        return await runtime.execute_workflow_remediation_tasks(
            workflow_id,
            limit=limit,
        )
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.post("/workflows/{workflow_id}/tick")
async def tick_workflow(workflow_id: str, req: Request):
    runtime = _get_research_runtime(req)
    try:
        return await runtime.tick_workflow(workflow_id)
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.post("/workflows/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    payload: WorkflowExecuteRequest,
    req: Request,
):
    runtime = _get_research_runtime(req)
    try:
        return await runtime.execute_workflow_step(
            workflow_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
        )
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.patch("/workflows/{workflow_id}/execution-policy")
async def update_workflow_execution_policy(
    workflow_id: str,
    payload: WorkflowExecutionPolicyUpdateRequest,
    req: Request,
):
    service = _get_research_service(req)
    try:
        return await service.update_workflow_execution_policy(
            workflow_id=workflow_id,
            patch=payload.model_dump(mode="json", exclude_none=True),
        )
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.patch("/workflows/{workflow_id}/experiment-runner")
async def update_workflow_experiment_runner(
    workflow_id: str,
    payload: ExperimentRunnerProfileUpdateRequest,
    req: Request,
):
    service = _get_research_service(req)
    try:
        return await service.update_workflow_experiment_runner(
            workflow_id=workflow_id,
            patch=payload.model_dump(
                mode="json",
                exclude_none=True,
                exclude_unset=True,
            ),
        )
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.post("/workflows/{workflow_id}/pause")
async def pause_workflow(workflow_id: str, req: Request):
    service = _get_research_service(req)
    try:
        return await service.pause_workflow(workflow_id)
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.post("/workflows/{workflow_id}/resume")
async def resume_workflow(workflow_id: str, req: Request):
    service = _get_research_service(req)
    try:
        return await service.resume_workflow(workflow_id)
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.post("/workflows/{workflow_id}/cancel")
async def cancel_workflow(workflow_id: str, req: Request):
    service = _get_research_service(req)
    try:
        return await service.cancel_workflow(workflow_id)
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.post("/workflows/{workflow_id}/retry")
async def retry_workflow(workflow_id: str, req: Request):
    service = _get_research_service(req)
    try:
        return await service.retry_workflow(workflow_id)
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.post("/workflows/{workflow_id}/tasks")
async def add_workflow_task(
    workflow_id: str,
    payload: WorkflowTaskCreateRequest,
    req: Request,
):
    service = _get_research_service(req)
    try:
        return await service.add_workflow_task(
            workflow_id=workflow_id,
            **payload.model_dump(mode="json"),
        )
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.get("/workflows/{workflow_id}/tasks/{task_id}")
async def get_workflow_task(
    workflow_id: str,
    task_id: str,
    req: Request,
):
    service = _get_research_service(req)
    try:
        return await service.get_workflow_task(
            workflow_id=workflow_id,
            task_id=task_id,
        )
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.patch("/workflows/{workflow_id}/tasks/{task_id}")
async def update_workflow_task(
    workflow_id: str,
    task_id: str,
    payload: WorkflowTaskUpdateRequest,
    req: Request,
):
    service = _get_research_service(req)
    try:
        return await service.update_workflow_task(
            workflow_id=workflow_id,
            task_id=task_id,
            **payload.model_dump(mode="json"),
        )
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.post("/workflows/{workflow_id}/tasks/{task_id}/dispatch")
async def dispatch_workflow_task(
    workflow_id: str,
    task_id: str,
    req: Request,
):
    runtime = _get_research_runtime(req)
    try:
        return await runtime.dispatch_workflow_task_followup(
            workflow_id=workflow_id,
            task_id=task_id,
        )
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.post("/workflows/{workflow_id}/tasks/{task_id}/execute")
async def execute_workflow_task(
    workflow_id: str,
    task_id: str,
    req: Request,
):
    runtime = _get_research_runtime(req)
    try:
        return await runtime.execute_workflow_task(
            workflow_id=workflow_id,
            task_id=task_id,
        )
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.get("/notes")
async def list_notes(
    req: Request,
    query: str = "",
    note_type: str = "",
    project_id: str = "",
    workflow_id: str = "",
    claim_id: str = "",
    experiment_id: str = "",
    limit: int = 50,
):
    service = _get_research_service(req)
    return await service.list_notes(
        query=query,
        note_type=note_type,
        project_id=project_id,
        workflow_id=workflow_id,
        claim_id=claim_id,
        experiment_id=experiment_id,
        limit=limit,
    )


@router.get("/artifacts")
async def list_artifacts(
    req: Request,
    project_id: str = "",
    workflow_id: str = "",
    artifact_type: str = "",
    source_type: str = "",
    limit: int = 100,
):
    service = _get_research_service(req)
    return await service.list_artifacts(
        project_id=project_id,
        workflow_id=workflow_id,
        artifact_type=artifact_type,
        source_type=source_type,
        limit=limit,
    )


@router.post("/artifacts")
async def upsert_artifact(payload: ArtifactUpsertRequest, req: Request):
    service = _get_research_service(req)
    try:
        return await service.upsert_artifact(**payload.model_dump(mode="json"))
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.post("/notes")
async def create_note(payload: NoteCreateRequest, req: Request):
    service = _get_research_service(req)
    try:
        return await service.create_note(**payload.model_dump(mode="json"))
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.get("/claims")
async def list_claims(
    req: Request,
    project_id: str = "",
    workflow_id: str = "",
    status: str = "",
    limit: int = 100,
):
    service = _get_research_service(req)
    return await service.list_claims(
        project_id=project_id,
        workflow_id=workflow_id,
        status=status,
        limit=limit,
    )


@router.post("/claims")
async def create_claim(payload: ClaimCreateRequest, req: Request):
    service = _get_research_service(req)
    try:
        return await service.create_claim(**payload.model_dump(mode="json"))
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.get("/claims/{claim_id}/graph")
async def claim_graph(claim_id: str, req: Request):
    service = _get_research_service(req)
    try:
        return await service.get_claim_graph(claim_id)
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.post("/evidences")
async def create_evidence(payload: EvidenceCreateRequest, req: Request):
    service = _get_research_service(req)
    try:
        return await service.attach_evidence(**payload.model_dump(mode="json"))
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.get("/experiments")
async def list_experiments(
    req: Request,
    project_id: str = "",
    workflow_id: str = "",
    status: str = "",
    limit: int = 100,
):
    service = _get_research_service(req)
    return await service.list_experiments(
        project_id=project_id,
        workflow_id=workflow_id,
        status=status,
        limit=limit,
    )


@router.post("/experiments")
async def create_experiment(payload: ExperimentCreateRequest, req: Request):
    service = _get_research_service(req)
    try:
        return await service.log_experiment(**payload.model_dump(mode="json"))
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str, req: Request):
    service = _get_research_service(req)
    try:
        return await service.get_experiment(experiment_id)
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.get("/experiments/{experiment_id}/contract")
async def get_experiment_artifact_contract(experiment_id: str, req: Request):
    service = _get_research_service(req)
    try:
        return await service.get_experiment_artifact_contract_validation(experiment_id)
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.get("/experiments/{experiment_id}/remediation")
async def get_experiment_contract_remediation(experiment_id: str, req: Request):
    service = _get_research_service(req)
    try:
        return await service.get_experiment_contract_remediation(experiment_id)
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.patch("/experiments/{experiment_id}")
async def update_experiment(
    experiment_id: str,
    payload: ExperimentUpdateRequest,
    req: Request,
):
    service = _get_research_service(req)
    try:
        return await service.update_experiment(
            experiment_id=experiment_id,
            **payload.model_dump(
                mode="json",
                exclude_none=True,
                exclude_unset=True,
            ),
        )
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.patch("/experiments/{experiment_id}/execution")
async def configure_experiment_execution(
    experiment_id: str,
    payload: ExperimentExecutionConfigureRequest,
    req: Request,
):
    service = _get_research_service(req)
    try:
        return await service.configure_experiment_execution(
            experiment_id=experiment_id,
            patch=payload.model_dump(
                mode="json",
                exclude_none=True,
                exclude_unset=True,
            ),
        )
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.get("/experiments/{experiment_id}/events")
async def list_experiment_events(
    experiment_id: str,
    req: Request,
    limit: int = 100,
):
    service = _get_research_service(req)
    try:
        return await service.list_experiment_events(
            experiment_id=experiment_id,
            limit=limit,
        )
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.post("/experiments/{experiment_id}/heartbeat")
async def record_experiment_heartbeat(
    experiment_id: str,
    payload: ExperimentHeartbeatRequest,
    req: Request,
):
    service = _get_research_service(req)
    try:
        return await service.record_experiment_heartbeat(
            experiment_id=experiment_id,
            **payload.model_dump(mode="json"),
        )
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.post("/experiments/{experiment_id}/result")
async def record_experiment_result(
    experiment_id: str,
    payload: ExperimentResultRequest,
    req: Request,
):
    service = _get_research_service(req)
    try:
        return await service.record_experiment_result(
            experiment_id=experiment_id,
            **payload.model_dump(mode="json", exclude_none=True),
        )
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.post("/experiments/{experiment_id}/launch")
async def launch_experiment(
    experiment_id: str,
    req: Request,
):
    runtime = _get_research_runtime(req)
    try:
        return await runtime.execute_experiment(experiment_id)
    except Exception as exc:
        raise _translate_errors(exc) from exc


@router.post("/experiments/compare")
async def compare_experiments(
    payload: CompareExperimentsRequest,
    req: Request,
):
    service = _get_research_service(req)
    return await service.compare_experiments(payload.experiment_ids)


@router.get("/reminders")
async def preview_reminders(
    req: Request,
    project_id: str = "",
    stale_hours: int = RESEARCH_WORKFLOW_STALE_HOURS,
):
    runtime = _get_research_runtime(req)
    return await runtime.preview_reminders(
        project_id=project_id,
        stale_hours=stale_hours,
    )


@router.post("/reminders/run")
async def run_reminders(payload: ReminderRunRequest, req: Request):
    runtime = _get_research_runtime(req)
    return await runtime.run_proactive_cycle(
        project_id=payload.project_id,
        stale_hours=payload.stale_hours,
    )
