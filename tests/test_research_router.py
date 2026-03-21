from __future__ import annotations

import asyncio
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

from researchclaw.app.routers import research as research_router
from researchclaw.research import (
    JsonResearchStore,
    ResearchService,
    ResearchWorkflowRuntime,
)
from researchclaw.research.models import WorkflowTask


class _FakeChannelManager:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    async def send_text(
        self,
        *,
        channel: str,
        user_id: str,
        session_id: str,
        text: str,
        meta=None,
    ) -> None:
        self.messages.append(
            {
                "channel": channel,
                "user_id": user_id,
                "session_id": session_id,
                "text": text,
            },
        )


class _FakeRunner:
    def __init__(self, handler=None) -> None:
        self.handler = handler
        self.calls: list[dict[str, str]] = []

    async def chat(
        self,
        message: str,
        session_id: str | None = None,
        *,
        agent_id: str | None = None,
    ) -> str:
        self.calls.append(
            {
                "message": message,
                "session_id": session_id or "",
                "agent_id": agent_id or "",
            },
        )
        if self.handler is None:
            return "no-op execution"
        return await self.handler(message, session_id=session_id, agent_id=agent_id)


def test_research_router_end_to_end(tmp_path, monkeypatch) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    channels = _FakeChannelManager()
    runtime = ResearchWorkflowRuntime(service=service, channel_manager=channels)
    monkeypatch.setattr(
        service,
        "_search_papers",
        lambda **_: [{"title": "Fresh Paper", "arxiv_id": "2502.00001"}],
    )

    app = FastAPI()
    app.state.research_service = service
    app.state.research_runtime = runtime
    app.include_router(research_router.router, prefix="/api/research")
    client = TestClient(app)

    project = client.post(
        "/api/research/projects",
        json={
            "name": "Router Project",
            "default_binding": {
                "channel": "console",
                "user_id": "owner",
                "session_id": "project:1",
            },
        },
    ).json()

    workflow = client.post(
        "/api/research/workflows",
        json={
            "project_id": project["id"],
            "title": "Pipeline",
            "goal": "Reach a claim with evidence.",
        },
    ).json()

    note = client.post(
        "/api/research/notes",
        json={
            "project_id": project["id"],
            "workflow_id": workflow["id"],
            "title": "Idea",
            "content": "Need to validate the baseline carefully.",
            "note_type": "idea_note",
        },
    ).json()

    claim = client.post(
        "/api/research/claims",
        json={
            "project_id": project["id"],
            "workflow_id": workflow["id"],
            "text": "Baseline quality materially affects downstream variance.",
            "note_ids": [note["id"]],
        },
    ).json()

    evidence = client.post(
        "/api/research/evidences",
        json={
            "project_id": project["id"],
            "claim_ids": [claim["id"]],
            "evidence_type": "note",
            "summary": "The note records the baseline variance concern.",
            "source_type": "note",
            "source_id": note["id"],
            "note_id": note["id"],
            "workflow_id": workflow["id"],
        },
    ).json()

    graph = client.get(f"/api/research/claims/{claim['id']}/graph").json()

    assert graph["claim"]["id"] == claim["id"]
    assert graph["notes"][0]["id"] == note["id"]
    assert graph["evidences"][0]["id"] == evidence["id"]

    asyncio.run(
        service.add_project_paper_watch(
            project_id=project["id"],
            query="baseline variance",
            max_results=3,
            check_every_hours=1,
        ),
    )
    state = asyncio.run(service.load_state())
    state.workflows[0].last_run_at = "2000-01-01T00:00:00+00:00"
    asyncio.run(service.save_state(state))

    reminder_result = client.post(
        "/api/research/reminders/run",
        json={"project_id": project["id"], "stale_hours": 1},
    ).json()

    assert reminder_result["reminder_count"] >= 1
    assert channels.messages


def test_research_router_workflow_execute(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    channels = _FakeChannelManager()

    async def _handler(message: str, session_id: str | None = None, agent_id: str | None = None) -> str:
        workflow = await service.list_workflows()
        current = workflow[0]
        await service.update_workflow_task(
            workflow_id=current.id,
            task_id=current.tasks[0].id,
            status="completed",
            summary="Literature shortlist recorded by the workflow executor.",
        )
        return "Completed the literature_search stage and recorded the shortlist."

    runner = _FakeRunner(handler=_handler)
    runtime = ResearchWorkflowRuntime(
        service=service,
        channel_manager=channels,
        runner=runner,
    )

    app = FastAPI()
    app.state.research_service = service
    app.state.research_runtime = runtime
    app.include_router(research_router.router, prefix="/api/research")
    client = TestClient(app)

    project = client.post(
        "/api/research/projects",
        json={"name": "Executor Project"},
    ).json()
    workflow = client.post(
        "/api/research/workflows",
        json={
            "project_id": project["id"],
            "title": "Executable workflow",
            "goal": "Move beyond static workflow state.",
        },
    ).json()

    execution = client.post(
        f"/api/research/workflows/{workflow['id']}/execute",
        json={
            "agent_id": "planner",
            "session_id": "research:exec-test",
        },
    ).json()

    assert execution["mutated_by_agent"] is True
    assert execution["workflow"]["current_stage"] == "paper_reading"
    assert execution["workflow"]["bindings"]["agent_id"] == "planner"
    assert execution["workflow"]["bindings"]["session_id"] == "research:exec-test"
    assert execution["note"]["note_type"] == "decision_log"
    assert runner.calls[0]["agent_id"] == "planner"
    assert runner.calls[0]["session_id"] == "research:exec-test"


def test_research_runtime_auto_executes_due_workflows(tmp_path, monkeypatch) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    channels = _FakeChannelManager()
    runtime = ResearchWorkflowRuntime(
        service=service,
        channel_manager=channels,
    )
    monkeypatch.setattr(
        "researchclaw.agents.tools.semantic_scholar.semantic_scholar_search",
        lambda **_: [
            {
                "title": "Robust Paper A",
                "authors": ["Alice", "Bob"],
                "abstract": "Paper A studies robustness under distribution shift.",
                "paper_id": "paper-a",
                "url": "https://example.com/paper-a",
                "year": 2025,
            },
            {
                "title": "Robust Paper B",
                "authors": ["Carol"],
                "abstract": "Paper B provides a strong baseline.",
                "paper_id": "paper-b",
                "url": "https://example.com/paper-b",
                "year": 2024,
            },
        ],
    )
    monkeypatch.setattr(
        "researchclaw.agents.tools.semantic_scholar.semantic_scholar_get_paper",
        lambda paper_id: {
            "title": f"Fetched {paper_id}",
            "abstract": f"Detailed abstract for {paper_id}.",
            "authors": ["Reader"],
            "venue": "ICLR",
            "year": 2025,
        },
    )

    async def _run() -> None:
        project = await service.create_project(
            name="Auto Project",
            default_binding={
                "channel": "console",
                "user_id": "owner",
                "session_id": "research:auto",
            },
        )
        workflow = await service.create_workflow(
            project_id=project.id,
            title="Autopilot workflow",
            execution_policy={
                "enabled": True,
                "mode": "stale_only",
                "stale_hours": 1,
                "cooldown_minutes": 1,
                "max_auto_runs_per_day": 10,
            },
        )

        async def _force_stale() -> None:
            state = await service.load_state()
            state.workflows[0].last_run_at = "2000-01-01T00:00:00+00:00"
            state.workflows[0].execution_policy.last_auto_run_at = (
                "2000-01-01T00:00:00+00:00"
            )
            await service.save_state(state)

        await _force_stale()
        first = await runtime.run_proactive_cycle(
            project_id=project.id,
            stale_hours=1,
        )
        updated = await service.get_workflow(workflow.id)
        artifacts = await service.list_artifacts(
            project_id=project.id,
            workflow_id=workflow.id,
            artifact_type="paper",
        )

        assert first["auto_execution_count"] == 1
        assert updated.current_stage == "paper_reading"
        assert len(artifacts) == 2
        assert updated.execution_policy.last_auto_run_at is not None
        assert updated.execution_policy.auto_run_count_in_window == 1
        assert any(
            item["text"].startswith("[Research Auto-Advance]")
            for item in channels.messages
        )

        await _force_stale()
        second = await runtime.run_proactive_cycle(
            project_id=project.id,
            stale_hours=1,
        )
        updated = await service.get_workflow(workflow.id)
        notes = await service.list_notes(
            project_id=project.id,
            workflow_id=workflow.id,
            note_type="paper_note",
            limit=20,
        )

        assert second["auto_execution_count"] == 1
        assert updated.current_stage == "note_synthesis"
        assert len(notes) >= 3

        await _force_stale()
        third = await runtime.run_proactive_cycle(
            project_id=project.id,
            stale_hours=1,
        )
        updated = await service.get_workflow(workflow.id)
        synthesis_notes = await service.list_notes(
            project_id=project.id,
            workflow_id=workflow.id,
            tags=["note_synthesis"],
            limit=10,
        )

        assert third["auto_execution_count"] == 1
        assert updated.current_stage == "hypothesis_queue"
        assert synthesis_notes

        await _force_stale()
        fourth = await runtime.run_proactive_cycle(
            project_id=project.id,
            stale_hours=1,
        )
        updated = await service.get_workflow(workflow.id)
        claims = await service.list_claims(
            project_id=project.id,
            workflow_id=workflow.id,
            limit=20,
        )
        graph = await service.get_claim_graph(claims[0].id)

        assert fourth["auto_execution_count"] == 1
        assert updated.current_stage == "experiment_plan"
        assert len(claims) >= 3
        assert graph["evidences"]
        assert graph["notes"]

        await _force_stale()
        fifth = await runtime.run_proactive_cycle(
            project_id=project.id,
            stale_hours=1,
        )
        updated = await service.get_workflow(workflow.id)
        planned_runs = await service.list_experiments(
            project_id=project.id,
            workflow_id=workflow.id,
            limit=20,
        )

        assert fifth["auto_execution_count"] == 1
        assert updated.current_stage == "experiment_run"
        assert len(planned_runs) >= 3
        assert {run.status for run in planned_runs[:3]} == {"planned"}

        await _force_stale()
        sixth = await runtime.run_proactive_cycle(
            project_id=project.id,
            stale_hours=1,
        )
        updated = await service.get_workflow(workflow.id)
        completed_runs = await service.list_experiments(
            project_id=project.id,
            workflow_id=workflow.id,
            status="completed",
            limit=20,
        )

        assert sixth["auto_execution_count"] == 1
        assert updated.current_stage == "result_analysis"
        assert len(completed_runs) >= 3
        assert all(run.artifact_ids for run in completed_runs[:3])

        await _force_stale()
        seventh = await runtime.run_proactive_cycle(
            project_id=project.id,
            stale_hours=1,
        )
        updated = await service.get_workflow(workflow.id)
        analyzed_claims = await service.list_claims(
            project_id=project.id,
            workflow_id=workflow.id,
            limit=20,
        )
        result_notes = await service.list_notes(
            project_id=project.id,
            workflow_id=workflow.id,
            tags=["result_analysis"],
            limit=10,
        )
        supported_claims = [claim for claim in analyzed_claims if claim.status == "supported"]
        analyzed_graph = await service.get_claim_graph(supported_claims[0].id)

        assert seventh["auto_execution_count"] == 1
        assert updated.current_stage == "writing_tasks"
        assert result_notes
        assert supported_claims
        assert analyzed_graph["experiments"]
        assert analyzed_graph["artifacts"]

        await _force_stale()
        eighth = await runtime.run_proactive_cycle(
            project_id=project.id,
            stale_hours=1,
        )
        updated = await service.get_workflow(workflow.id)
        writing_notes = await service.list_notes(
            project_id=project.id,
            workflow_id=workflow.id,
            note_type="writing_note",
            limit=10,
        )
        draft_artifacts = await service.list_artifacts(
            project_id=project.id,
            workflow_id=workflow.id,
            artifact_type="draft",
            limit=10,
        )

        assert eighth["auto_execution_count"] == 1
        assert updated.current_stage == "review_and_followup"
        assert writing_notes
        assert draft_artifacts

        await _force_stale()
        ninth = await runtime.run_proactive_cycle(
            project_id=project.id,
            stale_hours=1,
        )
        updated = await service.get_workflow(workflow.id)
        review_notes = await service.list_notes(
            project_id=project.id,
            workflow_id=workflow.id,
            tags=["review_and_followup"],
            limit=10,
        )

        assert ninth["auto_execution_count"] == 1
        assert updated.current_stage == "review_and_followup"
        assert updated.status == "completed"
        assert review_notes

    asyncio.run(_run())


def test_research_router_experiment_execution_ingest(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    app = FastAPI()
    app.state.research_service = service
    app.state.research_runtime = runtime
    app.include_router(research_router.router, prefix="/api/research")
    client = TestClient(app)

    project = client.post(
        "/api/research/projects",
        json={"name": "Execution API Project"},
    ).json()
    workflow = client.post(
        "/api/research/workflows",
        json={
            "project_id": project["id"],
            "title": "Execution API workflow",
        },
    ).json()
    claim = client.post(
        "/api/research/claims",
        json={
            "project_id": project["id"],
            "workflow_id": workflow["id"],
            "text": "The API-ingested run should appear in the claim graph.",
        },
    ).json()
    experiment = client.post(
        "/api/research/experiments",
        json={
            "project_id": project["id"],
            "workflow_id": workflow["id"],
            "name": "api-external-run",
            "status": "planned",
            "claim_ids": [claim["id"]],
        },
    ).json()

    configured = client.patch(
        f"/api/research/experiments/{experiment['id']}/execution",
        json={
            "mode": "external",
            "external_run_id": "api-job-1",
            "requested_by": "router-test",
            "metadata": {
                "artifact_contract": {
                    "required_metrics": ["accuracy"],
                    "required_outputs": ["api-result.json"],
                },
            },
        },
    ).json()
    heartbeat = client.post(
        f"/api/research/experiments/{experiment['id']}/heartbeat",
        json={
            "summary": "External execution started.",
            "metrics": {"step": 5},
        },
    ).json()
    result = client.post(
        f"/api/research/experiments/{experiment['id']}/result",
        json={
            "summary": "External execution finished.",
            "status": "completed",
            "metrics": {"accuracy": 0.93},
            "output_files": ["outputs/api-result.json"],
        },
    ).json()
    events = client.get(
        f"/api/research/experiments/{experiment['id']}/events",
    ).json()
    contract = client.get(
        f"/api/research/experiments/{experiment['id']}/contract",
    ).json()

    assert configured["experiment"]["execution"]["mode"] == "external"
    assert heartbeat["experiment"]["status"] == "running"
    assert result["experiment"]["status"] == "completed"
    assert result["experiment"]["artifact_ids"]
    assert events[0]["event_type"] == "completion"
    assert contract["passed"] is True
    assert contract["remediation"]["action_count"] == 0


def test_research_router_experiment_contract_remediation_and_artifact_upsert(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    app = FastAPI()
    app.state.research_service = service
    app.state.research_runtime = runtime
    app.include_router(research_router.router, prefix="/api/research")
    client = TestClient(app)

    project = client.post(
        "/api/research/projects",
        json={"name": "Remediation API Project"},
    ).json()
    workflow = client.post(
        "/api/research/workflows",
        json={
            "project_id": project["id"],
            "title": "Remediation workflow",
        },
    ).json()
    experiment = client.post(
        "/api/research/experiments",
        json={
            "project_id": project["id"],
            "workflow_id": workflow["id"],
            "name": "remediation-run",
            "status": "planned",
        },
    ).json()
    client.patch(
        f"/api/research/experiments/{experiment['id']}/execution",
        json={
            "mode": "external",
            "metadata": {
                "artifact_contract": {
                    "required_metrics": ["accuracy"],
                    "required_outputs": ["report.json"],
                    "required_artifact_types": ["analysis"],
                },
            },
        },
    )
    client.patch(
        f"/api/research/experiments/{experiment['id']}",
        json={
            "status": "completed",
            "metrics": {},
            "output_files": [],
            "notes": "Missing contract deliverables.",
        },
    )

    remediation = client.get(
        f"/api/research/experiments/{experiment['id']}/remediation",
    ).json()

    assert remediation["required"] is True
    assert remediation["action_count"] == 3
    assert remediation["actions"][2]["suggested_tool"] == "research_artifact_upsert"

    artifact = client.post(
        "/api/research/artifacts",
        json={
            "project_id": project["id"],
            "workflow_id": workflow["id"],
            "experiment_id": experiment["id"],
            "artifact_type": "analysis",
            "title": "Analysis report",
            "path": "outputs/analysis.md",
            "source_type": "experiment",
            "source_id": experiment["id"],
        },
    ).json()
    client.patch(
        f"/api/research/experiments/{experiment['id']}",
        json={
            "metrics": {"accuracy": 0.94},
            "output_files": ["outputs/report.json"],
        },
    )
    contract = client.get(
        f"/api/research/experiments/{experiment['id']}/contract",
    ).json()

    assert artifact["artifact_type"] == "analysis"
    assert contract["passed"] is True


def test_research_router_workflow_remediation_context(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    app = FastAPI()
    app.state.research_service = service
    app.state.research_runtime = runtime
    app.include_router(research_router.router, prefix="/api/research")
    client = TestClient(app)

    project = client.post(
        "/api/research/projects",
        json={"name": "Workflow Remediation API Project"},
    ).json()
    workflow = client.post(
        "/api/research/workflows",
        json={
            "project_id": project["id"],
            "title": "Workflow remediation query",
        },
    ).json()
    task = workflow["tasks"][0]
    client.post(
        f"/api/research/workflows/{workflow['id']}/tasks",
        json={
            "stage": "experiment_run",
            "title": "Resolve missing accuracy metric",
            "description": "Backfill the missing metric before analysis.",
            "assignee": "analyst",
            "metadata": {
                "task_kind": "experiment_contract_remediation",
                "remediation_key": "run-1:metric:accuracy",
            },
        },
    )
    state = asyncio.run(service.load_state())
    state.workflows[0].current_stage = "experiment_run"
    state.workflows[0].status = "blocked"
    state.workflows[0].error = "Artifact contract failed."
    state.workflows[0].tasks[0].status = "blocked"
    asyncio.run(service.save_state(state))
    remediation = client.get(
        f"/api/research/workflows/{workflow['id']}/remediation",
    ).json()

    assert remediation["blocked_task_id"] == ""
    assert remediation["remediation_tasks"][0]["assignee"] == "analyst"
    assert remediation["remediation_tasks"][0]["dispatch_count"] == 0
    assert remediation["ready_for_retry"] is False


def test_research_router_dispatches_workflow_task_followup(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    channels = _FakeChannelManager()
    runtime = ResearchWorkflowRuntime(service=service, channel_manager=channels)

    app = FastAPI()
    app.state.research_service = service
    app.state.research_runtime = runtime
    app.include_router(research_router.router, prefix="/api/research")
    client = TestClient(app)

    project = client.post(
        "/api/research/projects",
        json={
            "name": "Task Dispatch Project",
            "default_binding": {
                "channel": "console",
                "user_id": "owner",
                "session_id": "project:dispatch",
            },
        },
    ).json()
    workflow = client.post(
        "/api/research/workflows",
        json={
            "project_id": project["id"],
            "title": "Dispatchable workflow",
        },
    ).json()
    task_workflow = client.post(
        f"/api/research/workflows/{workflow['id']}/tasks",
        json={
            "title": "Backfill missing analysis artifact",
            "description": "Create the missing analysis artifact before review.",
            "assignee": "analyst",
            "stage": "experiment_run",
            "metadata": {
                "task_kind": "experiment_contract_remediation",
                "suggested_tool": "research_artifact_upsert",
                "payload_hint": {
                    "artifact_type": "analysis",
                    "path": "outputs/analysis.md",
                },
                "retry_policy": {
                    "max_attempts": 2,
                    "backoff_minutes": 30,
                },
            },
        },
    ).json()
    task_id = task_workflow["tasks"][-1]["id"]
    state = asyncio.run(service.load_state())
    state.workflows[0].current_stage = "experiment_run"
    state.workflows[0].status = "blocked"
    state.workflows[0].error = "Waiting for remediation task completion."
    asyncio.run(service.save_state(state))

    task = client.get(
        f"/api/research/workflows/{workflow['id']}/tasks/{task_id}",
    ).json()
    dispatched = client.post(
        f"/api/research/workflows/{workflow['id']}/tasks/{task_id}/dispatch",
    ).json()
    refreshed = client.get(
        f"/api/research/workflows/{workflow['id']}/tasks/{task_id}",
    ).json()
    remediation = client.get(
        f"/api/research/workflows/{workflow['id']}/remediation",
    ).json()

    assert task["id"] == task_id
    assert dispatched["delivery"]["ok"] is True
    assert dispatched["task"]["dispatch_count"] == 1
    assert refreshed["dispatch_count"] == 1
    assert refreshed["last_dispatch_at"] is not None
    assert remediation["remediation_tasks"][0]["last_dispatch_summary"] != ""
    assert remediation["remediation_tasks"][0]["last_dispatch_error"] == ""
    assert "research_artifact_upsert" in dispatched["message"]
    assert "Payload hint:" in dispatched["message"]
    assert channels.messages
    assert "Backfill missing analysis artifact" in channels.messages[-1]["text"]


def test_research_router_dashboard_includes_actionable_blocker_tasks(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    app = FastAPI()
    app.state.research_service = service
    app.state.research_runtime = runtime
    app.include_router(research_router.router, prefix="/api/research")
    client = TestClient(app)

    project = client.post(
        "/api/research/projects",
        json={"name": "Dashboard Blocker Project"},
    ).json()
    workflow = client.post(
        "/api/research/workflows",
        json={
            "project_id": project["id"],
            "title": "Dashboard blocker workflow",
        },
    ).json()
    task_workflow = client.post(
        f"/api/research/workflows/{workflow['id']}/tasks",
        json={
            "title": "Publish missing analysis artifact",
            "description": "Register the analysis artifact before retry.",
            "assignee": "agent",
            "stage": "experiment_run",
            "metadata": {
                "task_kind": "experiment_contract_remediation",
                "target": "analysis",
                "suggested_tool": "research_artifact_upsert",
                "retry_policy": {
                    "max_attempts": 2,
                    "backoff_minutes": 30,
                },
            },
        },
    ).json()
    task_id = task_workflow["tasks"][-1]["id"]
    state = asyncio.run(service.load_state())
    state.workflows[0].current_stage = "experiment_run"
    state.workflows[0].status = "blocked"
    state.workflows[0].error = "Waiting for remediation task completion."
    asyncio.run(service.save_state(state))

    dashboard = client.get(
        f"/api/research/projects/{project['id']}/dashboard",
    ).json()

    assert dashboard["recent_blockers"][0]["workflow_id"] == workflow["id"]
    assert dashboard["recent_blockers"][0]["actionable_tasks"][0]["task_id"] == task_id
    assert dashboard["recent_blockers"][0]["actionable_tasks"][0]["suggested_tool"] == "research_artifact_upsert"
    assert dashboard["recent_blockers"][0]["actionable_tasks"][0]["can_execute"] is True


def test_research_router_dispatches_workflow_remediation_batch(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    channels = _FakeChannelManager()
    runtime = ResearchWorkflowRuntime(service=service, channel_manager=channels)

    app = FastAPI()
    app.state.research_service = service
    app.state.research_runtime = runtime
    app.include_router(research_router.router, prefix="/api/research")
    client = TestClient(app)

    project = client.post(
        "/api/research/projects",
        json={
            "name": "Remediation Batch Dispatch Project",
            "default_binding": {
                "channel": "console",
                "user_id": "owner",
                "session_id": "project:dispatch-batch",
            },
        },
    ).json()
    workflow = client.post(
        "/api/research/workflows",
        json={
            "project_id": project["id"],
            "title": "Workflow remediation dispatch batch",
        },
    ).json()
    run = asyncio.run(
        service.log_experiment(
            project_id=project["id"],
            workflow_id=workflow["id"],
            name="dispatch-batch-gap-run",
            status="completed",
            metadata={"experiment_kind": "baseline"},
        ),
    )
    asyncio.run(
        service.configure_experiment_execution(
            experiment_id=run.id,
            patch={
                "mode": "external",
                "metadata": {
                    "artifact_contract": {
                        "required_artifact_types": ["analysis"],
                    },
                },
            },
        ),
    )
    state = asyncio.run(service.load_state())
    state.workflows[0].current_stage = "experiment_run"
    state.workflows[0].status = "blocked"
    state.workflows[0].error = "Waiting for remediation task completion."
    asyncio.run(service.save_state(state))

    dispatched = client.post(
        f"/api/research/workflows/{workflow['id']}/remediation/dispatch",
        params={"limit": 2},
    ).json()

    assert dispatched["dispatched_count"] == 1
    assert dispatched["results"][0]["task"]["status"] in {"pending", "blocked"}
    assert dispatched["results"][0]["delivery"]["ok"] is True
    assert channels.messages


def test_research_router_executes_workflow_remediation_batch(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    app = FastAPI()
    app.state.research_service = service
    app.state.research_runtime = runtime
    app.include_router(research_router.router, prefix="/api/research")
    client = TestClient(app)

    project = client.post(
        "/api/research/projects",
        json={"name": "Remediation Batch Execute Project"},
    ).json()
    workflow = client.post(
        "/api/research/workflows",
        json={
            "project_id": project["id"],
            "title": "Workflow remediation execute batch",
        },
    ).json()
    artifact_path = tmp_path / "batch-analysis.md"
    artifact_path.write_text("analysis output", encoding="utf-8")

    run = asyncio.run(
        service.log_experiment(
            project_id=project["id"],
            workflow_id=workflow["id"],
            name="batch-artifact-gap-run",
            status="completed",
            metadata={"experiment_kind": "baseline"},
        ),
    )
    asyncio.run(
        service.configure_experiment_execution(
            experiment_id=run.id,
            patch={
                "mode": "external",
                "metadata": {
                    "artifact_contract": {
                        "required_artifact_types": ["analysis"],
                    },
                },
            },
        ),
    )
    state = asyncio.run(service.load_state())
    workflow_state = state.workflows[0]
    workflow_state.current_stage = "experiment_run"
    workflow_state.status = "blocked"
    workflow_state.error = "Artifact contract failed."
    asyncio.run(service.save_state(state))

    client.post(
        f"/api/research/workflows/{workflow['id']}/tasks",
        json={
            "stage": "experiment_run",
            "title": "Publish missing analysis artifact",
            "description": "Register the generated analysis markdown file.",
            "assignee": "agent",
            "metadata": {
                "task_kind": "experiment_contract_remediation",
                "remediation_key": f"{run.id}:artifact:analysis",
                "experiment_id": run.id,
                "action_type": "publish_artifact",
                "target": "analysis",
                "suggested_tool": "research_artifact_upsert",
                "payload_hint": {
                    "project_id": project["id"],
                    "workflow_id": workflow["id"],
                    "experiment_id": run.id,
                    "artifact_type": "analysis",
                    "title": "batch-artifact-gap-run analysis",
                    "path": str(artifact_path),
                    "source_type": "experiment",
                    "source_id": run.id,
                },
                "retry_policy": {
                    "max_attempts": 2,
                    "backoff_minutes": 30,
                },
            },
        },
    ).json()

    executed = client.post(
        f"/api/research/workflows/{workflow['id']}/remediation/execute",
        params={"limit": 2},
    ).json()
    contract = client.get(
        f"/api/research/experiments/{run.id}/contract",
    ).json()

    assert executed["executed_count"] == 1
    assert executed["results"][0]["executed"] is True
    assert contract["passed"] is True


def test_research_router_dispatches_project_blocker_batch(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    channels = _FakeChannelManager()
    runtime = ResearchWorkflowRuntime(service=service, channel_manager=channels)

    app = FastAPI()
    app.state.research_service = service
    app.state.research_runtime = runtime
    app.include_router(research_router.router, prefix="/api/research")
    client = TestClient(app)

    project = client.post(
        "/api/research/projects",
        json={
            "name": "Project Blocker Dispatch",
            "default_binding": {
                "channel": "console",
                "user_id": "owner",
                "session_id": "project:blocker-dispatch",
            },
        },
    ).json()
    workflow = client.post(
        "/api/research/workflows",
        json={
            "project_id": project["id"],
            "title": "Project blocker dispatch workflow",
        },
    ).json()
    run = asyncio.run(
        service.log_experiment(
            project_id=project["id"],
            workflow_id=workflow["id"],
            name="project-dispatch-gap-run",
            status="completed",
            metadata={"experiment_kind": "baseline"},
        ),
    )
    asyncio.run(
        service.configure_experiment_execution(
            experiment_id=run.id,
            patch={
                "mode": "external",
                "metadata": {
                    "artifact_contract": {
                        "required_artifact_types": ["analysis"],
                    },
                },
            },
        ),
    )
    state = asyncio.run(service.load_state())
    state.workflows[0].current_stage = "experiment_run"
    state.workflows[0].status = "blocked"
    state.workflows[0].error = "Waiting for project remediation dispatch."
    asyncio.run(service.save_state(state))

    dispatched = client.post(
        f"/api/research/projects/{project['id']}/blockers/dispatch",
        params={"workflow_limit": 3, "task_limit": 2},
    ).json()

    assert dispatched["dispatched_count"] == 1
    assert dispatched["workflow_results"][0]["results"][0]["delivery"]["ok"] is True
    assert dispatched["dashboard"]["recent_blockers"][0]["workflow_id"] == workflow["id"]
    assert channels.messages


def test_research_router_executes_project_blocker_batch(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    app = FastAPI()
    app.state.research_service = service
    app.state.research_runtime = runtime
    app.include_router(research_router.router, prefix="/api/research")
    client = TestClient(app)

    project = client.post(
        "/api/research/projects",
        json={"name": "Project Blocker Execute"},
    ).json()
    workflow = client.post(
        "/api/research/workflows",
        json={
            "project_id": project["id"],
            "title": "Project blocker execute workflow",
        },
    ).json()
    artifact_path = tmp_path / "project-blocker-analysis.md"
    artifact_path.write_text("analysis output", encoding="utf-8")

    run = asyncio.run(
        service.log_experiment(
            project_id=project["id"],
            workflow_id=workflow["id"],
            name="project-execute-gap-run",
            status="completed",
            metadata={"experiment_kind": "baseline"},
        ),
    )
    asyncio.run(
        service.configure_experiment_execution(
            experiment_id=run.id,
            patch={
                "mode": "external",
                "metadata": {
                    "artifact_contract": {
                        "required_artifact_types": ["analysis"],
                    },
                },
            },
        ),
    )
    state = asyncio.run(service.load_state())
    workflow_state = state.workflows[0]
    workflow_state.current_stage = "experiment_run"
    workflow_state.status = "blocked"
    workflow_state.error = "Project blocker artifact contract failed."
    asyncio.run(service.save_state(state))

    client.post(
        f"/api/research/workflows/{workflow['id']}/tasks",
        json={
            "title": "Publish missing analysis artifact",
            "description": "Attach the analysis artifact back to the experiment.",
            "stage": "experiment_run",
            "assignee": "agent",
            "metadata": {
                "task_kind": "experiment_contract_remediation",
                "remediation_key": f"{run.id}:artifact:analysis",
                "experiment_id": run.id,
                "action_type": "publish_artifact",
                "target": "analysis",
                "suggested_tool": "research_artifact_upsert",
                "payload_hint": {
                    "artifact_type": "analysis",
                    "title": "Recovered analysis artifact",
                    "path": str(artifact_path),
                },
            },
        },
    )

    executed = client.post(
        f"/api/research/projects/{project['id']}/blockers/execute",
        params={"workflow_limit": 3, "task_limit": 2},
    ).json()
    validation = asyncio.run(service.get_experiment_artifact_contract_validation(run.id))

    assert executed["executed_count"] == 1
    assert executed["workflow_results"][0]["results"][0]["executed"] is True
    assert validation["passed"] is True


def test_research_router_resumes_ready_project_blockers(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    app = FastAPI()
    app.state.research_service = service
    app.state.research_runtime = runtime
    app.include_router(research_router.router, prefix="/api/research")
    client = TestClient(app)

    project = client.post(
        "/api/research/projects",
        json={"name": "Project Blocker Resume"},
    ).json()
    workflow = client.post(
        "/api/research/workflows",
        json={
            "project_id": project["id"],
            "title": "Project blocker resume workflow",
        },
    ).json()
    run = asyncio.run(
        service.log_experiment(
            project_id=project["id"],
            workflow_id=workflow["id"],
            name="project-resume-run",
            status="completed",
            metrics={"accuracy": 0.91, "robust_accuracy": 0.87},
            output_files=["outputs/resume-metrics.json"],
            metadata={"experiment_kind": "baseline"},
        ),
    )
    asyncio.run(
        service.add_workflow_task(
            workflow_id=workflow["id"],
            title="Completed remediation task",
            description="This remediation task has already been resolved.",
            stage="experiment_run",
            assignee="agent",
            metadata={
                "task_kind": "experiment_contract_remediation",
                "experiment_id": run.id,
                "action_type": "record_metric",
                "target": "accuracy",
            },
        ),
    )
    workflow_state = asyncio.run(service.get_workflow(workflow["id"]))
    remediation_task = next(
        task
        for task in workflow_state.tasks
        if task.metadata.get("task_kind") == "experiment_contract_remediation"
    )
    asyncio.run(
        service.update_workflow_task(
            workflow_id=workflow["id"],
            task_id=remediation_task.id,
            status="completed",
            summary="Already resolved.",
        ),
    )
    state = asyncio.run(service.load_state())
    state.workflows[0].current_stage = "experiment_run"
    state.workflows[0].status = "blocked"
    state.workflows[0].error = "Ready for project resume."
    asyncio.run(service.save_state(state))

    resumed = client.post(
        f"/api/research/projects/{project['id']}/blockers/resume",
        params={"workflow_limit": 3},
    ).json()
    refreshed = asyncio.run(service.get_workflow(workflow["id"]))

    assert resumed["resumed_count"] == 1
    assert resumed["workflow_results"][0]["workflow"]["id"] == workflow["id"]
    assert refreshed.current_stage == "result_analysis"
    assert refreshed.status == "running"


def test_research_router_executes_safe_remediation_task(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    app = FastAPI()
    app.state.research_service = service
    app.state.research_runtime = runtime
    app.include_router(research_router.router, prefix="/api/research")
    client = TestClient(app)

    project = client.post(
        "/api/research/projects",
        json={"name": "Task Execute Project"},
    ).json()
    workflow = client.post(
        "/api/research/workflows",
        json={
            "project_id": project["id"],
            "title": "Executable remediation workflow",
        },
    ).json()
    artifact_path = tmp_path / "contract-analysis.md"
    artifact_path.write_text("analysis output", encoding="utf-8")

    run = asyncio.run(
        service.log_experiment(
            project_id=project["id"],
            workflow_id=workflow["id"],
            name="artifact-gap-run",
            status="completed",
            metadata={"experiment_kind": "baseline"},
        ),
    )
    asyncio.run(
        service.configure_experiment_execution(
            experiment_id=run.id,
            patch={
                "mode": "external",
                "metadata": {
                    "artifact_contract": {
                        "required_artifact_types": ["analysis"],
                    },
                },
            },
        ),
    )
    state = asyncio.run(service.load_state())
    workflow_state = state.workflows[0]
    workflow_state.current_stage = "experiment_run"
    workflow_state.status = "blocked"
    workflow_state.error = "Artifact contract failed."
    asyncio.run(service.save_state(state))

    task_workflow = client.post(
        f"/api/research/workflows/{workflow['id']}/tasks",
        json={
            "stage": "experiment_run",
            "title": "Publish missing analysis artifact",
            "description": "Register the generated analysis markdown file.",
            "assignee": "agent",
            "metadata": {
                "task_kind": "experiment_contract_remediation",
                "remediation_key": f"{run.id}:artifact:analysis",
                "experiment_id": run.id,
                "action_type": "publish_artifact",
                "target": "analysis",
                "suggested_tool": "research_artifact_upsert",
                "payload_hint": {
                    "project_id": project["id"],
                    "workflow_id": workflow["id"],
                    "experiment_id": run.id,
                    "artifact_type": "analysis",
                    "title": "artifact-gap-run analysis",
                    "path": str(artifact_path),
                    "source_type": "experiment",
                    "source_id": run.id,
                },
                "retry_policy": {
                    "max_attempts": 2,
                    "backoff_minutes": 30,
                },
            },
        },
    ).json()
    task_id = task_workflow["tasks"][-1]["id"]

    executed = client.post(
        f"/api/research/workflows/{workflow['id']}/tasks/{task_id}/execute",
    ).json()
    refreshed_task = client.get(
        f"/api/research/workflows/{workflow['id']}/tasks/{task_id}",
    ).json()
    contract = client.get(
        f"/api/research/experiments/{run.id}/contract",
    ).json()
    remediation = client.get(
        f"/api/research/workflows/{workflow['id']}/remediation",
    ).json()
    artifacts = client.get(
        "/api/research/artifacts",
        params={
            "project_id": project["id"],
            "artifact_type": "analysis",
        },
    ).json()

    assert executed["executed"] is True
    assert refreshed_task["status"] == "completed"
    assert refreshed_task["execution_count"] == 1
    assert refreshed_task["last_execution_at"] is not None
    assert "Published artifact type 'analysis'" in executed["reason"]
    assert contract["passed"] is True
    assert remediation == {}
    assert artifacts[0]["path"] == str(artifact_path)


def test_research_router_executes_bundle_artifact_remediation_task(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    app = FastAPI()
    app.state.research_service = service
    app.state.research_runtime = runtime
    app.include_router(research_router.router, prefix="/api/research")
    client = TestClient(app)

    project = client.post(
        "/api/research/projects",
        json={"name": "Bundle Artifact Task Project"},
    ).json()
    workflow = client.post(
        "/api/research/workflows",
        json={
            "project_id": project["id"],
            "title": "Bundle artifact remediation workflow",
        },
    ).json()
    workdir = tmp_path / "bundle-artifact-remediation"
    workdir.mkdir()
    artifact_path = workdir / "analysis.md"
    artifact_path.write_text("bundle analysis output", encoding="utf-8")
    bundle_path = workdir / "analysis-summary.json"
    bundle_path.write_text(
        '{"result_bundle":{"artifacts":[{"artifact_type":"analysis","path":"analysis.md","title":"Bundle analysis artifact"}]}}',
        encoding="utf-8",
    )

    run = asyncio.run(
        service.log_experiment(
            project_id=project["id"],
            workflow_id=workflow["id"],
            name="bundle-artifact-gap-run",
            status="completed",
            output_files=[str(bundle_path)],
            metadata={"experiment_kind": "baseline"},
        ),
    )
    asyncio.run(
        service.configure_experiment_execution(
            experiment_id=run.id,
            patch={
                "mode": "external",
                "working_dir": str(workdir),
                "metadata": {
                    "artifact_contract": {
                        "required_artifact_types": ["analysis"],
                    },
                },
            },
        ),
    )

    task_workflow = client.post(
        f"/api/research/workflows/{workflow['id']}/tasks",
        json={
            "stage": "experiment_run",
            "title": "Publish analysis artifact from bundle",
            "description": "Resolve the missing analysis artifact from analysis-summary.json.",
            "assignee": "agent",
            "metadata": {
                "task_kind": "experiment_contract_remediation",
                "remediation_key": f"{run.id}:artifact:analysis",
                "experiment_id": run.id,
                "action_type": "publish_artifact",
                "target": "analysis",
                "suggested_tool": "research_artifact_upsert",
                "payload_hint": {
                    "project_id": project["id"],
                    "workflow_id": workflow["id"],
                    "experiment_id": run.id,
                    "artifact_type": "analysis",
                },
                "retry_policy": {
                    "max_attempts": 2,
                    "backoff_minutes": 30,
                },
            },
        },
    ).json()
    task_id = task_workflow["tasks"][-1]["id"]

    executed = client.post(
        f"/api/research/workflows/{workflow['id']}/tasks/{task_id}/execute",
    ).json()
    refreshed_task = client.get(
        f"/api/research/workflows/{workflow['id']}/tasks/{task_id}",
    ).json()
    contract = client.get(
        f"/api/research/experiments/{run.id}/contract",
    ).json()
    artifacts = client.get(
        "/api/research/artifacts",
        params={
            "project_id": project["id"],
            "artifact_type": "analysis",
        },
    ).json()

    assert executed["executed"] is True
    assert refreshed_task["status"] == "completed"
    assert "Published artifact type 'analysis' from result bundle" in executed["reason"]
    assert contract["passed"] is True
    assert artifacts[0]["path"] == str(artifact_path)


def test_research_router_executes_metric_remediation_task(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    app = FastAPI()
    app.state.research_service = service
    app.state.research_runtime = runtime
    app.include_router(research_router.router, prefix="/api/research")
    client = TestClient(app)

    project = client.post(
        "/api/research/projects",
        json={"name": "Metric Task Execute Project"},
    ).json()
    workflow = client.post(
        "/api/research/workflows",
        json={
            "project_id": project["id"],
            "title": "Metric remediation workflow",
        },
    ).json()
    workdir = tmp_path / "metric-remediation"
    workdir.mkdir()
    metrics_path = workdir / "metrics.json"
    metrics_path.write_text('{"accuracy": 0.93}', encoding="utf-8")

    run = asyncio.run(
        service.log_experiment(
            project_id=project["id"],
            workflow_id=workflow["id"],
            name="metric-gap-run",
            status="completed",
            metadata={"experiment_kind": "baseline"},
        ),
    )
    asyncio.run(
        service.configure_experiment_execution(
            experiment_id=run.id,
            patch={
                "mode": "external",
                "working_dir": str(workdir),
                "metadata": {
                    "metrics_file": "metrics.json",
                    "artifact_contract": {
                        "required_metrics": ["accuracy"],
                    },
                },
            },
        ),
    )

    task_workflow = client.post(
        f"/api/research/workflows/{workflow['id']}/tasks",
        json={
            "stage": "experiment_run",
            "title": "Record missing accuracy metric",
            "description": "Recover the missing metric from the existing metrics file.",
            "assignee": "analyst",
            "metadata": {
                "task_kind": "experiment_contract_remediation",
                "remediation_key": f"{run.id}:metric:accuracy",
                "experiment_id": run.id,
                "action_type": "record_metric",
                "target": "accuracy",
                "suggested_tool": "research_experiment_update",
                "retry_policy": {
                    "max_attempts": 2,
                    "backoff_minutes": 30,
                },
            },
        },
    ).json()
    task_id = task_workflow["tasks"][-1]["id"]

    executed = client.post(
        f"/api/research/workflows/{workflow['id']}/tasks/{task_id}/execute",
    ).json()
    refreshed_task = client.get(
        f"/api/research/workflows/{workflow['id']}/tasks/{task_id}",
    ).json()
    refreshed_experiment = client.get(
        f"/api/research/experiments/{run.id}",
    ).json()
    contract = client.get(
        f"/api/research/experiments/{run.id}/contract",
    ).json()

    assert executed["executed"] is True
    assert refreshed_task["status"] == "completed"
    assert refreshed_task["execution_count"] == 1
    assert "Recorded metric 'accuracy'=0.93" in executed["reason"]
    assert refreshed_experiment["metrics"]["accuracy"] == 0.93
    assert any(path.endswith("metrics.json") for path in refreshed_experiment["output_files"])
    assert contract["passed"] is True


def test_research_router_executes_metric_remediation_from_report_output(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    app = FastAPI()
    app.state.research_service = service
    app.state.research_runtime = runtime
    app.include_router(research_router.router, prefix="/api/research")
    client = TestClient(app)

    project = client.post(
        "/api/research/projects",
        json={"name": "Report Metric Task Project"},
    ).json()
    workflow = client.post(
        "/api/research/workflows",
        json={
            "project_id": project["id"],
            "title": "Report-backed metric remediation workflow",
        },
    ).json()
    workdir = tmp_path / "report-metric-remediation"
    workdir.mkdir()
    report_path = workdir / "report.json"
    report_path.write_text(
        '{"summary": {"metrics": {"accuracy": 0.91}}, "rows": [{"metric": "accuracy", "value": 0.91}]}',
        encoding="utf-8",
    )

    run = asyncio.run(
        service.log_experiment(
            project_id=project["id"],
            workflow_id=workflow["id"],
            name="report-metric-gap-run",
            status="completed",
            output_files=[str(report_path)],
            metadata={"experiment_kind": "baseline"},
        ),
    )
    asyncio.run(
        service.configure_experiment_execution(
            experiment_id=run.id,
            patch={
                "mode": "external",
                "working_dir": str(workdir),
                "metadata": {
                    "artifact_contract": {
                        "required_metrics": ["accuracy"],
                    },
                },
            },
        ),
    )

    task_workflow = client.post(
        f"/api/research/workflows/{workflow['id']}/tasks",
        json={
            "stage": "experiment_run",
            "title": "Record accuracy metric from report",
            "description": "Resolve the missing metric from report.json.",
            "assignee": "analyst",
            "metadata": {
                "task_kind": "experiment_contract_remediation",
                "remediation_key": f"{run.id}:metric:accuracy",
                "experiment_id": run.id,
                "action_type": "record_metric",
                "target": "accuracy",
                "suggested_tool": "research_experiment_update",
                "retry_policy": {
                    "max_attempts": 2,
                    "backoff_minutes": 30,
                },
            },
        },
    ).json()
    task_id = task_workflow["tasks"][-1]["id"]

    executed = client.post(
        f"/api/research/workflows/{workflow['id']}/tasks/{task_id}/execute",
    ).json()
    refreshed_experiment = client.get(
        f"/api/research/experiments/{run.id}",
    ).json()
    contract = client.get(
        f"/api/research/experiments/{run.id}/contract",
    ).json()

    assert executed["executed"] is True
    assert "Recorded metric 'accuracy'=0.91" in executed["reason"]
    assert refreshed_experiment["metrics"]["accuracy"] == 0.91
    assert contract["passed"] is True


def test_research_router_executes_metric_remediation_from_notebook_output(
    tmp_path,
) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    app = FastAPI()
    app.state.research_service = service
    app.state.research_runtime = runtime
    app.include_router(research_router.router, prefix="/api/research")
    client = TestClient(app)

    project = client.post(
        "/api/research/projects",
        json={"name": "Notebook Metric Task Project"},
    ).json()
    workflow = client.post(
        "/api/research/workflows",
        json={
            "project_id": project["id"],
            "title": "Notebook-backed metric remediation workflow",
        },
    ).json()
    workdir = tmp_path / "notebook-metric-remediation"
    workdir.mkdir()
    notebook_path = workdir / "analysis.ipynb"
    notebook_path.write_text(
        '{"cells":[{"cell_type":"code","execution_count":1,"metadata":{},'
        '"outputs":[{"output_type":"display_data","data":{"application/json":{"metrics":{"accuracy":0.96}}},"metadata":{}}],'
        '"source":["print(\'done\')"]}],"metadata":{},"nbformat":4,"nbformat_minor":5}',
        encoding="utf-8",
    )

    run = asyncio.run(
        service.log_experiment(
            project_id=project["id"],
            workflow_id=workflow["id"],
            name="notebook-metric-gap-run",
            status="completed",
            output_files=[str(notebook_path)],
            metadata={"experiment_kind": "baseline"},
        ),
    )
    asyncio.run(
        service.configure_experiment_execution(
            experiment_id=run.id,
            patch={
                "mode": "external",
                "working_dir": str(workdir),
                "metadata": {
                    "artifact_contract": {
                        "required_metrics": ["accuracy"],
                    },
                },
            },
        ),
    )

    task_workflow = client.post(
        f"/api/research/workflows/{workflow['id']}/tasks",
        json={
            "stage": "experiment_run",
            "title": "Record accuracy metric from notebook",
            "description": "Resolve the missing metric from analysis.ipynb.",
            "assignee": "analyst",
            "metadata": {
                "task_kind": "experiment_contract_remediation",
                "remediation_key": f"{run.id}:metric:accuracy",
                "experiment_id": run.id,
                "action_type": "record_metric",
                "target": "accuracy",
                "suggested_tool": "research_experiment_update",
                "retry_policy": {
                    "max_attempts": 2,
                    "backoff_minutes": 30,
                },
            },
        },
    ).json()
    task_id = task_workflow["tasks"][-1]["id"]

    executed = client.post(
        f"/api/research/workflows/{workflow['id']}/tasks/{task_id}/execute",
    ).json()
    refreshed_experiment = client.get(
        f"/api/research/experiments/{run.id}",
    ).json()
    contract = client.get(
        f"/api/research/experiments/{run.id}/contract",
    ).json()

    assert executed["executed"] is True
    assert "Recorded metric 'accuracy'=0.96" in executed["reason"]
    assert refreshed_experiment["metrics"]["accuracy"] == 0.96
    assert contract["passed"] is True


def test_research_router_launches_command_experiment(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    app = FastAPI()
    app.state.research_service = service
    app.state.research_runtime = runtime
    app.include_router(research_router.router, prefix="/api/research")
    client = TestClient(app)

    workdir = tmp_path / "command-run"
    workdir.mkdir()
    project = client.post(
        "/api/research/projects",
        json={"name": "Command Launch Project"},
    ).json()
    workflow = client.post(
        "/api/research/workflows",
        json={
            "project_id": project["id"],
            "title": "Command launch workflow",
        },
    ).json()
    claim = client.post(
        "/api/research/claims",
        json={
            "project_id": project["id"],
            "workflow_id": workflow["id"],
            "text": "The command launcher should complete and archive outputs.",
        },
    ).json()
    experiment = client.post(
        "/api/research/experiments",
        json={
            "project_id": project["id"],
            "workflow_id": workflow["id"],
            "name": "command-run",
            "status": "planned",
            "claim_ids": [claim["id"]],
            "metadata": {"experiment_kind": "baseline"},
        },
    ).json()
    client.patch(
        f"/api/research/experiments/{experiment['id']}/execution",
        json={
            "mode": "command",
            "command": [
                sys.executable,
                "-c",
                (
                    "import json, os, pathlib; "
                    "pathlib.Path('metrics.json').write_text("
                    "json.dumps({"
                    "'accuracy': 0.94, "
                    "'robust_accuracy': 0.9, "
                    "'launch_env': os.environ.get('RC_LAUNCH_MODE', '')"
                    "}), "
                    "encoding='utf-8')"
                ),
            ],
            "working_dir": str(workdir),
            "environment": {
                "RC_LAUNCH_MODE": "router-command",
            },
            "metadata": {
                "metrics_file": "metrics.json",
                "output_files": ["metrics.json"],
            },
        },
    )

    launched = client.post(
        f"/api/research/experiments/{experiment['id']}/launch",
    ).json()

    assert launched["executed"] is True
    assert launched["mode"] == "command"
    assert launched["experiment"]["status"] == "completed"
    assert launched["experiment"]["metrics"]["accuracy"] == 0.94
    assert launched["experiment"]["metrics"]["launch_env"] == "router-command"
    assert any(path.endswith("metrics.json") for path in launched["experiment"]["output_files"])


def test_research_router_launches_command_experiment_from_result_bundle(
    tmp_path,
) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    app = FastAPI()
    app.state.research_service = service
    app.state.research_runtime = runtime
    app.include_router(research_router.router, prefix="/api/research")
    client = TestClient(app)

    workdir = tmp_path / "command-bundle-run"
    workdir.mkdir()
    project = client.post(
        "/api/research/projects",
        json={"name": "Command Bundle Project"},
    ).json()
    workflow = client.post(
        "/api/research/workflows",
        json={
            "project_id": project["id"],
            "title": "Command bundle workflow",
        },
    ).json()
    claim = client.post(
        "/api/research/claims",
        json={
            "project_id": project["id"],
            "workflow_id": workflow["id"],
            "text": "The launcher should ingest the declared result bundle.",
        },
    ).json()
    experiment = client.post(
        "/api/research/experiments",
        json={
            "project_id": project["id"],
            "workflow_id": workflow["id"],
            "name": "command-bundle-run",
            "status": "planned",
            "claim_ids": [claim["id"]],
            "metadata": {"experiment_kind": "baseline"},
        },
    ).json()
    client.patch(
        f"/api/research/experiments/{experiment['id']}/execution",
        json={
            "mode": "command",
            "command": [
                sys.executable,
                "-c",
                (
                    "import json, pathlib; "
                    "pathlib.Path('report.json').write_text(json.dumps({'status':'ok'}), encoding='utf-8'); "
                    "pathlib.Path('analysis.md').write_text('bundle analysis', encoding='utf-8'); "
                    "pathlib.Path('analysis-summary.json').write_text("
                    "json.dumps({"
                    "'result_bundle': {"
                    "'metrics': {'accuracy': 0.97}, "
                    "'outputs': [{'name': 'report.json', 'path': 'report.json'}], "
                    "'artifacts': [{'artifact_type': 'analysis', 'path': 'analysis.md', 'title': 'Bundle analysis'}]"
                    "}"
                    "}), "
                    "encoding='utf-8')"
                ),
            ],
            "working_dir": str(workdir),
            "result_bundle_file": "analysis-summary.json",
            "result_bundle_schema": "analysis_summary.v1",
            "metadata": {
                "artifact_contract": {
                    "required_metrics": ["accuracy"],
                    "required_outputs": ["report.json"],
                    "required_artifact_types": ["analysis"],
                },
            },
        },
    )

    launched = client.post(
        f"/api/research/experiments/{experiment['id']}/launch",
    ).json()
    contract = client.get(
        f"/api/research/experiments/{experiment['id']}/contract",
    ).json()
    artifacts = client.get(
        "/api/research/artifacts",
        params={
            "project_id": project["id"],
            "artifact_type": "analysis",
        },
    ).json()

    assert launched["executed"] is True
    assert launched["experiment"]["execution"]["result_bundle_file"] == "analysis-summary.json"
    assert launched["experiment"]["execution"]["result_bundle_schema"] == "analysis_summary.v1"
    assert launched["experiment"]["metrics"]["accuracy"] == 0.97
    assert any(path.endswith("analysis-summary.json") for path in launched["experiment"]["output_files"])
    assert any(path.endswith("report.json") for path in launched["experiment"]["output_files"])
    assert contract["passed"] is True
    assert any(item["title"] == "Bundle analysis" for item in artifacts)


def test_research_router_uses_project_result_bundle_schema_registry(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    app = FastAPI()
    app.state.research_service = service
    app.state.research_runtime = runtime
    app.include_router(research_router.router, prefix="/api/research")
    client = TestClient(app)

    workdir = tmp_path / "schema-registry-bundle-run"
    workdir.mkdir()
    project = client.post(
        "/api/research/projects",
        json={
            "name": "Schema Registry Project",
            "result_bundle_schemas": [
                {
                    "name": "analysis_summary.v1",
                    "required_sections": ["metrics", "outputs", "artifacts"],
                    "required_metrics": ["accuracy"],
                    "required_outputs": ["report.json"],
                    "required_artifact_types": ["analysis"],
                },
            ],
        },
    ).json()
    workflow = client.post(
        "/api/research/workflows",
        json={
            "project_id": project["id"],
            "title": "Schema registry workflow",
        },
    ).json()
    experiment = client.post(
        "/api/research/experiments",
        json={
            "project_id": project["id"],
            "workflow_id": workflow["id"],
            "name": "schema-registry-run",
            "status": "planned",
            "metadata": {"experiment_kind": "baseline"},
        },
    ).json()
    configured = client.patch(
        f"/api/research/experiments/{experiment['id']}/execution",
        json={
            "mode": "command",
            "command": [
                sys.executable,
                "-c",
                (
                    "import json, pathlib; "
                    "pathlib.Path('report.json').write_text(json.dumps({'status':'ok'}), encoding='utf-8'); "
                    "pathlib.Path('analysis.md').write_text('schema registry analysis', encoding='utf-8'); "
                    "pathlib.Path('analysis-summary.json').write_text("
                    "json.dumps({"
                    "'result_bundle': {"
                    "'metrics': {'accuracy': 0.96}, "
                    "'outputs': [{'name': 'report.json', 'path': 'report.json'}], "
                    "'artifacts': [{'artifact_type': 'analysis', 'path': 'analysis.md', 'title': 'Schema analysis'}]"
                    "}"
                    "}), "
                    "encoding='utf-8')"
                ),
            ],
            "working_dir": str(workdir),
            "result_bundle_file": "analysis-summary.json",
            "result_bundle_schema": "analysis_summary.v1",
        },
    ).json()

    launched = client.post(
        f"/api/research/experiments/{experiment['id']}/launch",
    ).json()
    contract = client.get(
        f"/api/research/experiments/{experiment['id']}/contract",
    ).json()

    assert configured["experiment"]["execution"]["metadata"]["artifact_contract"] == {
        "required_metrics": ["accuracy"],
        "required_outputs": ["report.json"],
        "required_artifact_types": ["analysis"],
    }
    assert launched["experiment"]["metrics"]["accuracy"] == 0.96
    assert launched["experiment"]["metadata"]["result_bundle_validation"]["schema_name"] == "analysis_summary.v1"
    assert launched["experiment"]["metadata"]["result_bundle_validation"]["passed"] is True
    assert launched["experiment"]["metadata"]["result_bundle_validation"]["available_sections"] == [
        "artifacts",
        "metrics",
        "outputs",
    ]
    assert contract["enabled"] is True
    assert contract["passed"] is True


def test_research_router_runner_profiles_attach_execution_bindings(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    app = FastAPI()
    app.state.research_service = service
    app.state.research_runtime = runtime
    app.include_router(research_router.router, prefix="/api/research")
    client = TestClient(app)

    project = client.post(
        "/api/research/projects",
        json={
            "name": "Runner Profile API Project",
            "execution_catalog": [
                {
                    "name": "local-benchmark",
                    "template": {
                        "mode": "command",
                        "command": [
                            sys.executable,
                            "-c",
                            (
                                "import json, os, pathlib; "
                                "pathlib.Path('metrics.json').write_text("
                                "json.dumps({"
                                "'accuracy': 0.93, "
                                "'robust_accuracy': 0.88, "
                                "'dataset': os.environ.get('RC_DATASET', ''), "
                                "'stage': os.environ.get('RC_STAGE', '')"
                                "}), "
                                "encoding='utf-8')"
                            ),
                        ],
                        "working_dir": "{output_dir}",
                        "environment": {
                            "RC_DATASET": "{experiment_kind}",
                            "RC_STAGE": "{current_stage}",
                        },
                        "parameter_overrides": {
                            "dataset": "{experiment_kind}_suite",
                        },
                        "input_data_overrides": {
                            "planner_stage": "{current_stage}",
                        },
                        "result_bundle_file": "analysis-summary.json",
                        "result_bundle_schema": "analysis_summary.v1",
                        "metadata": {
                            "metrics_file": "metrics.json",
                            "output_files": ["metrics.json"],
                        },
                    },
                    "artifact_contract": {
                        "required_metrics": ["accuracy", "robust_accuracy"],
                    },
                },
                {
                    "name": "remote-stress",
                    "template": {
                        "mode": "external",
                        "instructions": "Run the stress test on the remote queue.",
                        "environment": {
                            "RC_QUEUE": "remote-shift",
                        },
                    },
                    "artifact_contract": {
                        "required_outputs": ["stress-report.json"],
                    },
                },
                {
                    "name": "ablation-lab",
                    "template": {
                        "catalog_entry": "local-benchmark",
                        "environment": {
                            "RC_HYPOTHESIS_KIND": "assumption_ablation",
                        },
                        "parameter_overrides": {
                            "ablation_target": "core_assumption",
                        },
                    },
                },
            ],
            "default_experiment_runner": {
                "enabled": True,
                "default": {
                    "catalog_entry": "local-benchmark",
                },
                "kind_overrides": {
                    "stress_test": {
                        "catalog_entry": "remote-stress",
                    },
                },
            },
        },
    ).json()
    workflow = client.post(
        "/api/research/workflows",
        json={
            "project_id": project["id"],
            "title": "Runner profile workflow",
            "execution_policy": {
                "enabled": True,
                "mode": "stale_only",
                "stale_hours": 1,
                "cooldown_minutes": 1,
                "max_auto_runs_per_day": 4,
                "allowed_stages": ["experiment_plan", "experiment_run"],
            },
        },
    ).json()
    updated_workflow = client.patch(
        f"/api/research/workflows/{workflow['id']}/experiment-runner",
        json={
            "kind_overrides": {
                "baseline": {
                    "metadata": {
                        "profile_name": "baseline-auto",
                    },
                },
            },
            "rules": [
                {
                    "name": "assumption-ablation-rule",
                    "stages": ["experiment_plan"],
                    "experiment_kinds": ["ablation"],
                    "hypothesis_kinds": ["assumption_ablation"],
                    "template": {
                        "catalog_entry": "ablation-lab",
                    },
                },
            ],
        },
    ).json()
    client.post(
        "/api/research/claims",
        json={
            "project_id": project["id"],
            "workflow_id": workflow["id"],
            "text": "The runner profile should attach bindings during experiment planning.",
        },
    ).json()
    client.post(
        "/api/research/claims",
        json={
            "project_id": project["id"],
            "workflow_id": workflow["id"],
            "text": "Ablating the core assumption should reduce robustness.",
            "metadata": {
                "hypothesis_kind": "assumption_ablation",
            },
        },
    ).json()
    client.post(
        "/api/research/claims",
        json={
            "project_id": project["id"],
            "workflow_id": workflow["id"],
            "text": "The hard-shift slice should expose at least one failure mode.",
            "metadata": {
                "hypothesis_kind": "failure_mode_probe",
            },
        },
    ).json()
    client.post(
        "/api/research/claims",
        json={
            "project_id": project["id"],
            "workflow_id": workflow["id"],
            "text": "Baseline quality materially affects downstream variance.",
            "metadata": {
                "hypothesis_kind": "baseline_risk",
            },
        },
    ).json()

    async def _run() -> None:
        state = await service.load_state()
        workflow_state = state.workflows[0]
        workflow_state.current_stage = "experiment_plan"
        workflow_state.status = "running"
        workflow_state.last_run_at = "2000-01-01T00:00:00+00:00"
        workflow_state.execution_policy.last_auto_run_at = "2000-01-01T00:00:00+00:00"
        experiment_plan_stage = next(
            stage for stage in workflow_state.stages if stage.name == "experiment_plan"
        )
        experiment_plan_stage.status = "running"
        if not any(task.stage == "experiment_plan" for task in workflow_state.tasks):
            workflow_state.tasks.append(
                WorkflowTask(
                    stage="experiment_plan",
                    title="Define an experiment plan",
                    status="pending",
                ),
            )
        await service.save_state(state)

        first = await runtime.run_proactive_cycle(
            project_id=project["id"],
            stale_hours=1,
        )
        planned = await service.list_experiments(
            project_id=project["id"],
            workflow_id=workflow["id"],
            limit=10,
        )
        by_kind = {
            run.metadata.get("experiment_kind", ""): run
            for run in planned
        }

        assert first["auto_execution_count"] == 1
        assert updated_workflow["experiment_runner"]["kind_overrides"]["baseline"]["metadata"]["profile_name"] == "baseline-auto"
        assert updated_workflow["experiment_runner"]["rules"][0]["name"] == "assumption-ablation-rule"
        assert project["execution_catalog"][0]["name"] == "local-benchmark"
        assert by_kind["baseline"].execution.mode == "command"
        assert by_kind["baseline"].execution.metadata["catalog_entry"] == "local-benchmark"
        assert by_kind["baseline"].execution.metadata["artifact_contract"]["required_metrics"] == [
            "accuracy",
            "robust_accuracy",
        ]
        assert by_kind["baseline"].execution.metadata["profile_name"] == "baseline-auto"
        assert by_kind["baseline"].execution.result_bundle_file == "analysis-summary.json"
        assert by_kind["baseline"].execution.result_bundle_schema == "analysis_summary.v1"
        assert by_kind["baseline"].execution.environment["RC_DATASET"] == "baseline"
        assert by_kind["baseline"].parameters["dataset"] == "baseline_suite"
        assert by_kind["baseline"].input_data["planner_stage"] == "experiment_plan"
        assert by_kind["ablation"].execution.mode == "command"
        assert by_kind["ablation"].execution.metadata["catalog_entry"] == "ablation-lab"
        assert by_kind["ablation"].execution.environment["RC_HYPOTHESIS_KIND"] == "assumption_ablation"
        assert by_kind["ablation"].parameters["ablation_target"] == "core_assumption"
        assert by_kind["stress_test"].execution.mode == "external"
        assert by_kind["stress_test"].execution.metadata["catalog_entry"] == "remote-stress"
        assert by_kind["stress_test"].execution.environment["RC_QUEUE"] == "remote-shift"

        state = await service.load_state()
        state.workflows[0].last_run_at = "2000-01-01T00:00:00+00:00"
        state.workflows[0].execution_policy.last_auto_run_at = "2000-01-01T00:00:00+00:00"
        await service.save_state(state)

        second = await runtime.run_proactive_cycle(
            project_id=project["id"],
            stale_hours=1,
        )
        updated = await service.get_workflow(workflow["id"])
        planned = await service.list_experiments(
            project_id=project["id"],
            workflow_id=workflow["id"],
            limit=10,
        )
        by_kind = {
            run.metadata.get("experiment_kind", ""): run
            for run in planned
        }

        assert second["auto_execution_count"] == 1
        assert updated.current_stage == "experiment_run"
        assert by_kind["baseline"].status == "completed"
        assert by_kind["ablation"].status == "completed"
        assert by_kind["baseline"].metrics["dataset"] == "baseline"
        assert by_kind["baseline"].metrics["stage"] == "experiment_plan"
        assert by_kind["stress_test"].status == "running"

    asyncio.run(_run())


def test_research_runtime_waits_for_external_experiment_results(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    async def _run() -> None:
        project = await service.create_project(name="External Runtime Project")
        workflow = await service.create_workflow(
            project_id=project.id,
            title="External runtime workflow",
            execution_policy={
                "enabled": True,
                "mode": "stale_only",
                "stale_hours": 1,
                "cooldown_minutes": 1,
                "max_auto_runs_per_day": 4,
                "allowed_stages": ["experiment_run"],
            },
        )
        claim = await service.create_claim(
            project_id=project.id,
            workflow_id=workflow.id,
            text="The external executor should unblock experiment_run once results arrive.",
        )
        run = await service.log_experiment(
            project_id=project.id,
            workflow_id=workflow.id,
            name="external-runtime-run",
            status="planned",
            claim_ids=[claim.id],
            metadata={"experiment_kind": "baseline"},
        )
        await service.configure_experiment_execution(
            experiment_id=run.id,
            patch={
                "mode": "external",
                "external_run_id": "runtime-job-1",
                "requested_by": "runtime-test",
            },
        )

        state = await service.load_state()
        workflow_state = state.workflows[0]
        workflow_state.current_stage = "experiment_run"
        workflow_state.status = "running"
        workflow_state.last_run_at = "2000-01-01T00:00:00+00:00"
        workflow_state.execution_policy.last_auto_run_at = "2000-01-01T00:00:00+00:00"
        experiment_stage = next(
            stage for stage in workflow_state.stages if stage.name == "experiment_run"
        )
        experiment_stage.status = "running"
        if not any(task.stage == "experiment_run" for task in workflow_state.tasks):
            workflow_state.tasks.append(
                WorkflowTask(
                    stage="experiment_run",
                    title="Run or collect experiments",
                    status="pending",
                ),
            )
        await service.save_state(state)

        first = await runtime.run_proactive_cycle(
            project_id=project.id,
            stale_hours=1,
        )
        waiting = await service.get_workflow(workflow.id)
        pending_run = await service.get_experiment(run.id)

        assert first["auto_execution_count"] == 1
        assert waiting.current_stage == "experiment_run"
        assert waiting.status == "running"
        assert pending_run.status == "running"

        await service.record_experiment_result(
            experiment_id=run.id,
            summary="External runtime run completed.",
            status="completed",
            metrics={"accuracy": 0.9, "robust_accuracy": 0.85},
            output_files=["outputs/runtime-result.json"],
            notes="The external executor pushed final results back.",
        )

        state = await service.load_state()
        state.workflows[0].last_run_at = "2000-01-01T00:00:00+00:00"
        state.workflows[0].execution_policy.last_auto_run_at = "2000-01-01T00:00:00+00:00"
        await service.save_state(state)

        second = await runtime.run_proactive_cycle(
            project_id=project.id,
            stale_hours=1,
        )
        resumed = await service.get_workflow(workflow.id)

        assert second["auto_execution_count"] == 1
        assert resumed.current_stage == "result_analysis"

    asyncio.run(_run())


def test_research_runtime_executes_command_experiment_in_stage(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    async def _run() -> None:
        workdir = tmp_path / "stage-command-run"
        workdir.mkdir()
        project = await service.create_project(name="Command Runtime Project")
        workflow = await service.create_workflow(
            project_id=project.id,
            title="Command runtime workflow",
            execution_policy={
                "enabled": True,
                "mode": "stale_only",
                "stale_hours": 1,
                "cooldown_minutes": 1,
                "max_auto_runs_per_day": 4,
                "allowed_stages": ["experiment_run"],
            },
        )
        claim = await service.create_claim(
            project_id=project.id,
            workflow_id=workflow.id,
            text="The command executor should advance experiment_run automatically.",
        )
        run = await service.log_experiment(
            project_id=project.id,
            workflow_id=workflow.id,
            name="command-stage-run",
            status="planned",
            claim_ids=[claim.id],
            metadata={"experiment_kind": "baseline"},
        )
        await service.configure_experiment_execution(
            experiment_id=run.id,
            patch={
                "mode": "command",
                "command": [
                    sys.executable,
                    "-c",
                    (
                        "import json, pathlib; "
                        "pathlib.Path('metrics.json').write_text("
                        "json.dumps({'accuracy': 0.91, 'robust_accuracy': 0.87}), "
                        "encoding='utf-8')"
                    ),
                ],
                "working_dir": str(workdir),
                "metadata": {
                    "metrics_file": "metrics.json",
                    "output_files": ["metrics.json"],
                },
            },
        )

        state = await service.load_state()
        workflow_state = state.workflows[0]
        workflow_state.current_stage = "experiment_run"
        workflow_state.status = "running"
        workflow_state.last_run_at = "2000-01-01T00:00:00+00:00"
        workflow_state.execution_policy.last_auto_run_at = "2000-01-01T00:00:00+00:00"
        experiment_stage = next(
            stage for stage in workflow_state.stages if stage.name == "experiment_run"
        )
        experiment_stage.status = "running"
        if not any(task.stage == "experiment_run" for task in workflow_state.tasks):
            workflow_state.tasks.append(
                WorkflowTask(
                    stage="experiment_run",
                    title="Run or collect experiments",
                    status="pending",
                ),
            )
        await service.save_state(state)

        result = await runtime.run_proactive_cycle(
            project_id=project.id,
            stale_hours=1,
        )
        updated_workflow = await service.get_workflow(workflow.id)
        completed_run = await service.get_experiment(run.id)
        events = await service.list_experiment_events(
            experiment_id=run.id,
            limit=10,
        )

        assert result["auto_execution_count"] == 1
        assert updated_workflow.current_stage == "result_analysis"
        assert completed_run.status == "completed"
        assert completed_run.metrics["robust_accuracy"] == 0.87
        assert events[0].event_type == "completion"

    asyncio.run(_run())


def test_research_runtime_blocks_on_experiment_contract_gaps(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    channels = _FakeChannelManager()
    runtime = ResearchWorkflowRuntime(service=service, channel_manager=channels)

    async def _run() -> None:
        workdir = tmp_path / "contract-gap-run"
        workdir.mkdir()
        project = await service.create_project(name="Contract Gap Project")
        workflow = await service.create_workflow(
            project_id=project.id,
            title="Contract gap workflow",
            execution_policy={
                "enabled": True,
                "mode": "stale_only",
                "stale_hours": 1,
                "cooldown_minutes": 1,
                "max_auto_runs_per_day": 4,
                "allowed_stages": ["experiment_run"],
            },
        )
        claim = await service.create_claim(
            project_id=project.id,
            workflow_id=workflow.id,
            text="Missing contract outputs should block experiment_run.",
        )
        run = await service.log_experiment(
            project_id=project.id,
            workflow_id=workflow.id,
            name="contract-gap-run",
            status="planned",
            claim_ids=[claim.id],
            metadata={"experiment_kind": "baseline"},
        )
        await service.configure_experiment_execution(
            experiment_id=run.id,
            patch={
                "mode": "command",
                "command": [
                    sys.executable,
                    "-c",
                    (
                        "import json, pathlib; "
                        "pathlib.Path('metrics.json').write_text("
                        "json.dumps({'accuracy': 0.92}), "
                        "encoding='utf-8')"
                    ),
                ],
                "working_dir": str(workdir),
                "metadata": {
                    "metrics_file": "metrics.json",
                    "output_files": ["metrics.json"],
                    "artifact_contract": {
                        "required_metrics": ["accuracy", "calibration_error"],
                        "required_outputs": ["metrics.json", "report.json"],
                        "required_artifact_types": ["analysis"],
                    },
                },
            },
        )

        state = await service.load_state()
        workflow_state = state.workflows[0]
        workflow_state.current_stage = "experiment_run"
        workflow_state.status = "running"
        workflow_state.last_run_at = "2000-01-01T00:00:00+00:00"
        workflow_state.execution_policy.last_auto_run_at = "2000-01-01T00:00:00+00:00"
        experiment_stage = next(
            stage for stage in workflow_state.stages if stage.name == "experiment_run"
        )
        experiment_stage.status = "running"
        if not any(task.stage == "experiment_run" for task in workflow_state.tasks):
            workflow_state.tasks.append(
                WorkflowTask(
                    stage="experiment_run",
                    title="Run or collect experiments",
                    status="pending",
                ),
            )
        await service.save_state(state)

        first = await runtime.run_proactive_cycle(
            project_id=project.id,
            stale_hours=1,
        )
        blocked = await service.get_workflow(workflow.id)
        validation = await service.get_experiment_artifact_contract_validation(run.id)
        notes = await service.list_notes(
            project_id=project.id,
            workflow_id=workflow.id,
            tags=["contract_validation"],
            limit=10,
        )
        followup_tasks = [
            task
            for task in blocked.tasks
            if task.stage == "experiment_run"
            and task.metadata.get("task_kind") == "experiment_contract_followup"
        ]

        assert first["auto_execution_count"] == 1
        assert blocked.current_stage == "experiment_run"
        assert blocked.status == "blocked"
        assert validation["passed"] is False
        assert validation["missing_metrics"] == ["calibration_error"]
        assert validation["missing_outputs"] == ["report.json"]
        assert validation["missing_artifact_types"] == ["analysis"]
        assert notes
        assert followup_tasks
        assert followup_tasks[0].status == "pending"
        remediation_tasks = [
            task
            for task in blocked.tasks
            if task.stage == "experiment_run"
            and task.metadata.get("task_kind") == "experiment_contract_remediation"
        ]
        assert len(remediation_tasks) == 3
        assert remediation_tasks[0].due_at is not None
        assert remediation_tasks[0].dispatch_count == 1
        assert remediation_tasks[0].last_dispatch_at is not None
        assert {task.assignee for task in remediation_tasks} == {"agent", "analyst"}
        assert channels.messages
        reminder_text = "\n".join(item["text"] for item in channels.messages)
        assert "Recommended actions:" in reminder_text
        assert "Suggested tool: research_experiment_update" in reminder_text
        assert "Retry backoff:" in reminder_text
        assert "calibration_error" in reminder_text
        assert "report.json" in reminder_text
        assert "research_artifact_upsert" in reminder_text
        assert any(
            item["reminder_type"] == "remediation_task_followup"
            for item in first["delivery_results"]
        )

        await service.update_experiment(
            experiment_id=run.id,
            metrics={"calibration_error": 0.05},
            output_files=["outputs/report.json"],
            notes="Backfilled missing report artifact and calibration metric.",
        )
        await service.upsert_artifact(
            project_id=project.id,
            workflow_id=workflow.id,
            experiment_id=run.id,
            artifact_type="analysis",
            title="Backfilled analysis artifact",
            path="outputs/analysis.md",
            source_type="experiment",
            source_id=run.id,
            claim_ids=[claim.id],
        )
        state = await service.load_state()
        state.workflows[0].last_run_at = "2000-01-01T00:00:00+00:00"
        state.workflows[0].execution_policy.last_auto_run_at = "2000-01-01T00:00:00+00:00"
        await service.save_state(state)

        second = await runtime.run_proactive_cycle(
            project_id=project.id,
            stale_hours=1,
        )
        resumed = await service.get_workflow(workflow.id)
        validation = await service.get_experiment_artifact_contract_validation(run.id)
        followup_tasks = [
            task
            for task in resumed.tasks
            if task.stage == "experiment_run"
            and task.metadata.get("task_kind") == "experiment_contract_followup"
        ]
        remediation_tasks = [
            task
            for task in resumed.tasks
            if task.stage == "experiment_run"
            and task.metadata.get("task_kind") == "experiment_contract_remediation"
        ]

        assert second["auto_execution_count"] == 1
        assert resumed.current_stage == "result_analysis"
        assert resumed.status == "running"
        assert validation["passed"] is True
        assert followup_tasks[0].status == "completed"
        assert all(task.status == "completed" for task in remediation_tasks)

    asyncio.run(_run())


def test_research_runtime_auto_executes_safe_remediation_tasks(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    async def _run() -> None:
        artifact_path = tmp_path / "auto-contract-analysis.md"
        artifact_path.write_text("auto analysis output", encoding="utf-8")

        project = await service.create_project(name="Auto Remediation Project")
        workflow = await service.create_workflow(
            project_id=project.id,
            title="Auto remediation workflow",
            execution_policy={
                "enabled": True,
                "mode": "stale_only",
                "stale_hours": 1,
                "cooldown_minutes": 1,
                "max_auto_runs_per_day": 4,
                "allowed_stages": ["experiment_run"],
            },
        )
        run = await service.log_experiment(
            project_id=project.id,
            workflow_id=workflow.id,
            name="auto-remediation-run",
            status="completed",
            metadata={"experiment_kind": "baseline"},
        )
        await service.configure_experiment_execution(
            experiment_id=run.id,
            patch={
                "mode": "external",
                "metadata": {
                    "artifact_contract": {
                        "required_artifact_types": ["analysis"],
                    },
                },
            },
        )
        workflow = await service.add_workflow_task(
            workflow_id=workflow.id,
            stage="experiment_run",
            title="Publish analysis artifact automatically",
            description="Use the generated markdown file to satisfy the contract.",
            assignee="agent",
            metadata={
                "task_kind": "experiment_contract_remediation",
                "remediation_key": f"{run.id}:artifact:analysis",
                "experiment_id": run.id,
                "action_type": "publish_artifact",
                "target": "analysis",
                "suggested_tool": "research_artifact_upsert",
                "payload_hint": {
                    "project_id": project.id,
                    "workflow_id": workflow.id,
                    "experiment_id": run.id,
                    "artifact_type": "analysis",
                    "title": "auto-remediation-run analysis",
                    "path": str(artifact_path),
                    "source_type": "experiment",
                    "source_id": run.id,
                },
                "retry_policy": {
                    "max_attempts": 2,
                    "backoff_minutes": 15,
                },
            },
        )

        state = await service.load_state()
        workflow_state = state.workflows[0]
        workflow_state.current_stage = "experiment_run"
        workflow_state.status = "blocked"
        workflow_state.error = "Artifact contract failed."
        workflow_state.last_run_at = "2000-01-01T00:00:00+00:00"
        workflow_state.execution_policy.last_auto_run_at = "2000-01-01T00:00:00+00:00"
        experiment_stage = next(
            stage for stage in workflow_state.stages if stage.name == "experiment_run"
        )
        experiment_stage.status = "blocked"
        if not any(
            task.stage == "experiment_run"
            and task.metadata.get("task_kind") != "experiment_contract_remediation"
            for task in workflow_state.tasks
        ):
            workflow_state.tasks.append(
                WorkflowTask(
                    stage="experiment_run",
                    title="Run or collect experiments",
                    status="pending",
                ),
            )
        await service.save_state(state)

        result = await runtime.run_proactive_cycle(
            project_id=project.id,
            stale_hours=1,
        )
        updated_workflow = await service.get_workflow(workflow.id)
        validation = await service.get_experiment_artifact_contract_validation(run.id)
        remediation_task = next(
            task
            for task in updated_workflow.tasks
            if task.metadata.get("task_kind") == "experiment_contract_remediation"
        )

        assert result["task_execution_count"] == 1
        assert result["task_execution_results"][0]["executed"] is True
        assert remediation_task.status == "completed"
        assert remediation_task.execution_count == 1
        assert validation["passed"] is True
        assert result["auto_execution_count"] == 1
        assert updated_workflow.current_stage == "result_analysis"

    asyncio.run(_run())


def test_research_runtime_auto_executes_bundle_output_remediation_tasks(
    tmp_path,
) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    async def _run() -> None:
        workdir = tmp_path / "auto-bundle-output-remediation"
        workdir.mkdir()
        report_path = workdir / "report.json"
        report_path.write_text('{"status":"ok"}', encoding="utf-8")
        bundle_path = workdir / "analysis-summary.json"
        bundle_path.write_text(
            '{"result_bundle":{"outputs":[{"name":"report.json","path":"report.json"}]}}',
            encoding="utf-8",
        )

        project = await service.create_project(name="Auto Bundle Output Project")
        workflow = await service.create_workflow(
            project_id=project.id,
            title="Auto bundle output remediation workflow",
            execution_policy={
                "enabled": True,
                "mode": "stale_only",
                "stale_hours": 1,
                "cooldown_minutes": 1,
                "max_auto_runs_per_day": 4,
                "allowed_stages": ["experiment_run"],
            },
        )
        run = await service.log_experiment(
            project_id=project.id,
            workflow_id=workflow.id,
            name="auto-bundle-output-run",
            status="completed",
            output_files=[str(bundle_path)],
            metadata={"experiment_kind": "baseline"},
        )
        await service.configure_experiment_execution(
            experiment_id=run.id,
            patch={
                "mode": "external",
                "working_dir": str(workdir),
                "metadata": {
                    "artifact_contract": {
                        "required_outputs": ["report.json"],
                    },
                },
            },
        )
        workflow = await service.add_workflow_task(
            workflow_id=workflow.id,
            stage="experiment_run",
            title="Archive report output from bundle",
            description="Resolve the missing report output from analysis-summary.json.",
            assignee="agent",
            metadata={
                "task_kind": "experiment_contract_remediation",
                "remediation_key": f"{run.id}:output:report.json",
                "experiment_id": run.id,
                "action_type": "archive_output",
                "target": "report.json",
                "retry_policy": {
                    "max_attempts": 2,
                    "backoff_minutes": 15,
                },
            },
        )

        state = await service.load_state()
        workflow_state = state.workflows[0]
        workflow_state.current_stage = "experiment_run"
        workflow_state.status = "blocked"
        workflow_state.error = "Artifact contract failed."
        workflow_state.last_run_at = "2000-01-01T00:00:00+00:00"
        workflow_state.execution_policy.last_auto_run_at = "2000-01-01T00:00:00+00:00"
        experiment_stage = next(
            stage for stage in workflow_state.stages if stage.name == "experiment_run"
        )
        experiment_stage.status = "blocked"
        if not any(
            task.stage == "experiment_run"
            and task.metadata.get("task_kind") != "experiment_contract_remediation"
            for task in workflow_state.tasks
        ):
            workflow_state.tasks.append(
                WorkflowTask(
                    stage="experiment_run",
                    title="Run or collect experiments",
                    status="pending",
                ),
            )
        await service.save_state(state)

        result = await runtime.run_proactive_cycle(
            project_id=project.id,
            stale_hours=1,
        )
        updated_workflow = await service.get_workflow(workflow.id)
        updated_experiment = await service.get_experiment(run.id)
        validation = await service.get_experiment_artifact_contract_validation(run.id)

        assert result["task_execution_count"] == 1
        assert result["task_execution_results"][0]["executed"] is True
        assert any(path.endswith("report.json") for path in updated_experiment.output_files)
        assert validation["passed"] is True
        assert result["auto_execution_count"] == 1
        assert updated_workflow.current_stage == "result_analysis"

    asyncio.run(_run())


def test_research_runtime_auto_executes_metric_remediation_tasks(tmp_path) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    async def _run() -> None:
        workdir = tmp_path / "auto-metric-remediation"
        workdir.mkdir()
        metrics_path = workdir / "metrics.json"
        metrics_path.write_text('{"accuracy": 0.95}', encoding="utf-8")

        project = await service.create_project(name="Auto Metric Remediation Project")
        workflow = await service.create_workflow(
            project_id=project.id,
            title="Auto metric remediation workflow",
            execution_policy={
                "enabled": True,
                "mode": "stale_only",
                "stale_hours": 1,
                "cooldown_minutes": 1,
                "max_auto_runs_per_day": 4,
                "allowed_stages": ["experiment_run"],
            },
        )
        run = await service.log_experiment(
            project_id=project.id,
            workflow_id=workflow.id,
            name="auto-metric-remediation-run",
            status="completed",
            metadata={"experiment_kind": "baseline"},
        )
        await service.configure_experiment_execution(
            experiment_id=run.id,
            patch={
                "mode": "external",
                "working_dir": str(workdir),
                "metadata": {
                    "metrics_file": "metrics.json",
                    "artifact_contract": {
                        "required_metrics": ["accuracy"],
                    },
                },
            },
        )
        workflow = await service.add_workflow_task(
            workflow_id=workflow.id,
            stage="experiment_run",
            title="Record accuracy from metrics file",
            description="Use the existing metrics file to resolve the contract gap.",
            assignee="agent",
            metadata={
                "task_kind": "experiment_contract_remediation",
                "remediation_key": f"{run.id}:metric:accuracy",
                "experiment_id": run.id,
                "action_type": "record_metric",
                "target": "accuracy",
                "suggested_tool": "research_experiment_update",
                "retry_policy": {
                    "max_attempts": 2,
                    "backoff_minutes": 15,
                },
            },
        )

        state = await service.load_state()
        workflow_state = state.workflows[0]
        workflow_state.current_stage = "experiment_run"
        workflow_state.status = "blocked"
        workflow_state.error = "Artifact contract failed."
        workflow_state.last_run_at = "2000-01-01T00:00:00+00:00"
        workflow_state.execution_policy.last_auto_run_at = "2000-01-01T00:00:00+00:00"
        experiment_stage = next(
            stage for stage in workflow_state.stages if stage.name == "experiment_run"
        )
        experiment_stage.status = "blocked"
        if not any(
            task.stage == "experiment_run"
            and task.metadata.get("task_kind") != "experiment_contract_remediation"
            for task in workflow_state.tasks
        ):
            workflow_state.tasks.append(
                WorkflowTask(
                    stage="experiment_run",
                    title="Run or collect experiments",
                    status="pending",
                ),
            )
        await service.save_state(state)

        result = await runtime.run_proactive_cycle(
            project_id=project.id,
            stale_hours=1,
        )
        updated_workflow = await service.get_workflow(workflow.id)
        updated_experiment = await service.get_experiment(run.id)
        validation = await service.get_experiment_artifact_contract_validation(run.id)
        remediation_task = next(
            task
            for task in updated_workflow.tasks
            if task.metadata.get("task_kind") == "experiment_contract_remediation"
        )

        assert result["task_execution_count"] == 1
        assert result["task_execution_results"][0]["executed"] is True
        assert remediation_task.status == "completed"
        assert remediation_task.execution_count == 1
        assert updated_experiment.metrics["accuracy"] == 0.95
        assert validation["passed"] is True
        assert result["auto_execution_count"] == 1
        assert updated_workflow.current_stage == "result_analysis"

    asyncio.run(_run())


def test_research_runtime_auto_executes_metric_remediation_from_json_artifact(
    tmp_path,
) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    async def _run() -> None:
        workdir = tmp_path / "auto-artifact-metric-remediation"
        workdir.mkdir()
        report_path = workdir / "analysis-report.json"
        report_path.write_text(
            '{"analysis": {"accuracy": 0.97}, "items": [{"name": "accuracy", "value": 0.97}]}',
            encoding="utf-8",
        )

        project = await service.create_project(name="Auto Artifact Metric Project")
        workflow = await service.create_workflow(
            project_id=project.id,
            title="Auto artifact metric remediation workflow",
            execution_policy={
                "enabled": True,
                "mode": "stale_only",
                "stale_hours": 1,
                "cooldown_minutes": 1,
                "max_auto_runs_per_day": 4,
                "allowed_stages": ["experiment_run"],
            },
        )
        run = await service.log_experiment(
            project_id=project.id,
            workflow_id=workflow.id,
            name="auto-artifact-metric-run",
            status="completed",
            metadata={"experiment_kind": "baseline"},
        )
        await service.configure_experiment_execution(
            experiment_id=run.id,
            patch={
                "mode": "external",
                "working_dir": str(workdir),
                "metadata": {
                    "artifact_contract": {
                        "required_metrics": ["accuracy"],
                    },
                },
            },
        )
        await service.upsert_artifact(
            project_id=project.id,
            workflow_id=workflow.id,
            experiment_id=run.id,
            artifact_type="analysis",
            title="Auto artifact metric report",
            path=str(report_path),
            source_type="experiment",
            source_id=run.id,
        )
        workflow = await service.add_workflow_task(
            workflow_id=workflow.id,
            stage="experiment_run",
            title="Record accuracy from JSON artifact",
            description="Resolve the missing metric from the analysis report artifact.",
            assignee="agent",
            metadata={
                "task_kind": "experiment_contract_remediation",
                "remediation_key": f"{run.id}:metric:accuracy",
                "experiment_id": run.id,
                "action_type": "record_metric",
                "target": "accuracy",
                "suggested_tool": "research_experiment_update",
                "retry_policy": {
                    "max_attempts": 2,
                    "backoff_minutes": 15,
                },
            },
        )

        state = await service.load_state()
        workflow_state = state.workflows[0]
        workflow_state.current_stage = "experiment_run"
        workflow_state.status = "blocked"
        workflow_state.error = "Artifact contract failed."
        workflow_state.last_run_at = "2000-01-01T00:00:00+00:00"
        workflow_state.execution_policy.last_auto_run_at = "2000-01-01T00:00:00+00:00"
        experiment_stage = next(
            stage for stage in workflow_state.stages if stage.name == "experiment_run"
        )
        experiment_stage.status = "blocked"
        if not any(
            task.stage == "experiment_run"
            and task.metadata.get("task_kind") != "experiment_contract_remediation"
            for task in workflow_state.tasks
        ):
            workflow_state.tasks.append(
                WorkflowTask(
                    stage="experiment_run",
                    title="Run or collect experiments",
                    status="pending",
                ),
            )
        await service.save_state(state)

        result = await runtime.run_proactive_cycle(
            project_id=project.id,
            stale_hours=1,
        )
        updated_workflow = await service.get_workflow(workflow.id)
        updated_experiment = await service.get_experiment(run.id)
        validation = await service.get_experiment_artifact_contract_validation(run.id)

        assert result["task_execution_count"] == 1
        assert result["task_execution_results"][0]["executed"] is True
        assert updated_experiment.metrics["accuracy"] == 0.97
        assert validation["passed"] is True
        assert result["auto_execution_count"] == 1
        assert updated_workflow.current_stage == "result_analysis"

    asyncio.run(_run())


def test_research_runtime_auto_executes_metric_remediation_from_notebook_artifact(
    tmp_path,
) -> None:
    service = ResearchService(
        store=JsonResearchStore(tmp_path / "research-state.json"),
    )
    runtime = ResearchWorkflowRuntime(service=service)

    async def _run() -> None:
        workdir = tmp_path / "auto-notebook-metric-remediation"
        workdir.mkdir()
        notebook_path = workdir / "analysis.ipynb"
        notebook_path.write_text(
            '{"cells":[{"cell_type":"code","execution_count":1,"metadata":{},'
            '"outputs":[{"output_type":"display_data","data":{"application/json":{"accuracy":0.98}},"metadata":{}},'
            '{"output_type":"stream","name":"stdout","text":["{\\"accuracy\\": 0.98}\\n"]}],"source":["print(\'done\')"]}],'
            '"metadata":{},"nbformat":4,"nbformat_minor":5}',
            encoding="utf-8",
        )

        project = await service.create_project(name="Auto Notebook Metric Project")
        workflow = await service.create_workflow(
            project_id=project.id,
            title="Auto notebook metric remediation workflow",
            execution_policy={
                "enabled": True,
                "mode": "stale_only",
                "stale_hours": 1,
                "cooldown_minutes": 1,
                "max_auto_runs_per_day": 4,
                "allowed_stages": ["experiment_run"],
            },
        )
        run = await service.log_experiment(
            project_id=project.id,
            workflow_id=workflow.id,
            name="auto-notebook-metric-run",
            status="completed",
            metadata={"experiment_kind": "baseline"},
        )
        await service.configure_experiment_execution(
            experiment_id=run.id,
            patch={
                "mode": "external",
                "working_dir": str(workdir),
                "metadata": {
                    "artifact_contract": {
                        "required_metrics": ["accuracy"],
                    },
                },
            },
        )
        await service.upsert_artifact(
            project_id=project.id,
            workflow_id=workflow.id,
            experiment_id=run.id,
            artifact_type="analysis",
            title="Auto notebook metric artifact",
            path=str(notebook_path),
            source_type="experiment",
            source_id=run.id,
        )
        workflow = await service.add_workflow_task(
            workflow_id=workflow.id,
            stage="experiment_run",
            title="Record accuracy from notebook artifact",
            description="Resolve the missing metric from the notebook artifact.",
            assignee="agent",
            metadata={
                "task_kind": "experiment_contract_remediation",
                "remediation_key": f"{run.id}:metric:accuracy",
                "experiment_id": run.id,
                "action_type": "record_metric",
                "target": "accuracy",
                "suggested_tool": "research_experiment_update",
                "retry_policy": {
                    "max_attempts": 2,
                    "backoff_minutes": 15,
                },
            },
        )

        state = await service.load_state()
        workflow_state = state.workflows[0]
        workflow_state.current_stage = "experiment_run"
        workflow_state.status = "blocked"
        workflow_state.error = "Artifact contract failed."
        workflow_state.last_run_at = "2000-01-01T00:00:00+00:00"
        workflow_state.execution_policy.last_auto_run_at = "2000-01-01T00:00:00+00:00"
        experiment_stage = next(
            stage for stage in workflow_state.stages if stage.name == "experiment_run"
        )
        experiment_stage.status = "blocked"
        if not any(
            task.stage == "experiment_run"
            and task.metadata.get("task_kind") != "experiment_contract_remediation"
            for task in workflow_state.tasks
        ):
            workflow_state.tasks.append(
                WorkflowTask(
                    stage="experiment_run",
                    title="Run or collect experiments",
                    status="pending",
                ),
            )
        await service.save_state(state)

        result = await runtime.run_proactive_cycle(
            project_id=project.id,
            stale_hours=1,
        )
        updated_workflow = await service.get_workflow(workflow.id)
        updated_experiment = await service.get_experiment(run.id)
        validation = await service.get_experiment_artifact_contract_validation(run.id)

        assert result["task_execution_count"] == 1
        assert result["task_execution_results"][0]["executed"] is True
        assert updated_experiment.metrics["accuracy"] == 0.98
        assert validation["passed"] is True
        assert result["auto_execution_count"] == 1
        assert updated_workflow.current_stage == "result_analysis"

    asyncio.run(_run())
