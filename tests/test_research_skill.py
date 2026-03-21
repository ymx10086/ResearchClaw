from __future__ import annotations

import asyncio
import sys

from researchclaw.agents.skills.research_workflows import register
from researchclaw.research import JsonResearchStore, ResearchService


def test_research_workflow_skill_uses_shared_state(monkeypatch, tmp_path) -> None:
    state_path = tmp_path / "shared-research-state.json"
    monkeypatch.setenv("RESEARCHCLAW_RESEARCH_STATE_PATH", str(state_path))

    tools = register()

    project = tools["research_project_create"](
        name="Skill Project",
        description="Created through runtime skill tools.",
        execution_catalog=[
            {
                "name": "local-default",
                "template": {
                    "mode": "command",
                    "command": ["python", "scripts/run.py", "--kind", "{experiment_kind}"],
                    "environment": {
                        "RC_EXPERIMENT_KIND": "{experiment_kind}",
                    },
                },
            },
        ],
        result_bundle_schemas=[
            {
                "name": "analysis_summary.v1",
                "required_metrics": ["accuracy"],
                "required_outputs": ["report.json"],
                "required_artifact_types": ["analysis"],
            },
        ],
        default_experiment_runner={
            "enabled": True,
            "default": {
                "catalog_entry": "local-default",
            },
        },
    )
    workflow = tools["research_workflow_create"](
        project_id=project["id"],
        title="Skill-driven workflow",
        goal="Advance the workflow through structured tools.",
    )
    note = tools["research_note_create"](
        project_id=project["id"],
        workflow_id=workflow["id"],
        title="Operator note",
        content="Track the initial reading pass.",
        note_type="idea_note",
        tags=["skill"],
    )

    updated = tools["research_workflow_update_task"](
        workflow_id=workflow["id"],
        task_id=workflow["tasks"][0]["id"],
        status="completed",
        summary="Initial literature search completed through the skill.",
        note_ids=[note["id"]],
    )
    policy = tools["research_workflow_update_execution_policy"](
        workflow_id=workflow["id"],
        enabled=True,
        mode="stale_only",
        stale_hours=2,
        cooldown_minutes=15,
        max_auto_runs_per_day=2,
        allowed_stages=["paper_reading"],
        notify_after_execution=False,
    )
    workflow = tools["research_workflow_update_experiment_runner"](
        workflow_id=workflow["id"],
        kind_overrides={
            "baseline": {
                "metadata": {
                    "profile_name": "baseline-from-skill",
                },
            },
        },
        rules=[
            {
                "name": "ablation-rule",
                "hypothesis_kinds": ["assumption_ablation"],
                "template": {
                    "environment": {
                        "RC_HYPOTHESIS_KIND": "assumption_ablation",
                    },
                },
            },
        ],
    )
    project = tools["research_project_update"](
        project_id=project["id"],
        execution_catalog=[
            *project["execution_catalog"],
            {
                "name": "remote-stress",
                "template": {
                    "mode": "external",
                    "instructions": "Route stress tests to the remote queue.",
                },
            },
        ],
        result_bundle_schemas=[
            *project["result_bundle_schemas"],
            {
                "name": "analysis_summary.v2",
                "required_metrics": ["accuracy", "robust_accuracy"],
                "required_outputs": ["report.json", "metrics.json"],
            },
        ],
        default_experiment_runner={
            "kind_overrides": {
                "stress_test": {
                    "catalog_entry": "remote-stress",
                },
            },
        },
    )
    fetched = tools["research_workflow_get"](workflow["id"])
    fetched_task = tools["research_workflow_task_get"](
        workflow["id"],
        workflow["tasks"][0]["id"],
    )
    notes = tools["research_notes_search"](project_id=project["id"])
    artifacts = tools["research_artifacts_list"](
        project_id=project["id"],
        artifact_type="paper",
    )

    assert state_path.exists()
    assert updated["current_stage"] == "paper_reading"
    assert policy["execution_policy"]["enabled"] is True
    assert fetched["current_stage"] == "paper_reading"
    assert fetched_task["id"] == workflow["tasks"][0]["id"]
    assert fetched_task["status"] == "completed"
    assert tools["research_workflow_remediation"](workflow["id"]) == {}
    assert fetched["execution_policy"]["allowed_stages"] == ["paper_reading"]
    assert fetched["experiment_runner"]["default"]["catalog_entry"] == "local-default"
    assert fetched["experiment_runner"]["kind_overrides"]["baseline"]["metadata"]["profile_name"] == "baseline-from-skill"
    assert fetched["experiment_runner"]["rules"][0]["name"] == "ablation-rule"
    assert project["execution_catalog"][0]["name"] == "local-default"
    assert project["execution_catalog"][1]["name"] == "remote-stress"
    assert project["result_bundle_schemas"][0]["name"] == "analysis_summary.v1"
    assert project["result_bundle_schemas"][1]["name"] == "analysis_summary.v2"
    assert project["default_experiment_runner"]["kind_overrides"]["stress_test"]["catalog_entry"] == "remote-stress"
    assert artifacts == []
    assert notes[0]["id"] == note["id"]


def test_research_workflow_skill_updates_claims_and_experiments(
    monkeypatch,
    tmp_path,
) -> None:
    state_path = tmp_path / "shared-research-state.json"
    monkeypatch.setenv("RESEARCHCLAW_RESEARCH_STATE_PATH", str(state_path))

    tools = register()

    project = tools["research_project_create"](name="Skill Update Project")
    workflow = tools["research_workflow_create"](
        project_id=project["id"],
        title="Experiment workflow",
    )
    note = tools["research_note_create"](
        project_id=project["id"],
        workflow_id=workflow["id"],
        title="Experiment note",
        content="The experiment update should link metrics and artifacts back.",
        note_type="experiment_note",
    )
    claim = tools["research_claim_create"](
        project_id=project["id"],
        workflow_id=workflow["id"],
        text="The structured run supports the hypothesis.",
    )
    run = tools["research_experiment_log"](
        project_id=project["id"],
        workflow_id=workflow["id"],
        name="planned-run",
        status="planned",
        claim_ids=[claim["id"]],
    )

    updated_run = tools["research_experiment_update"](
        experiment_id=run["id"],
        status="completed",
        metrics={"accuracy": 0.91, "robust_accuracy": 0.86},
        notes="Completed through the skill update tool.",
        output_files=["outputs/run-metrics.json"],
        note_ids=[note["id"]],
        metadata={"stage": "experiment_run"},
    )
    updated_claim = tools["research_claim_update"](
        claim_id=claim["id"],
        status="supported",
        confidence=0.88,
        note_ids=[note["id"]],
        artifact_ids=updated_run["artifact_ids"],
        metadata={"stage": "result_analysis"},
    )
    graph = tools["research_claim_graph"](claim["id"])

    assert updated_run["status"] == "completed"
    assert note["id"] in updated_run["note_ids"]
    assert updated_run["artifact_ids"]
    assert updated_claim["status"] == "supported"
    assert updated_claim["confidence"] == 0.88
    assert any(item["experiment_id"] == run["id"] for item in graph["evidences"])

    configured = tools["research_experiment_update_execution"](
        experiment_id=run["id"],
        mode="external",
        result_bundle_file="analysis-summary.json",
        result_bundle_schema="analysis_summary.v1",
        environment={"RC_QUEUE": "external"},
        external_run_id="skill-job-1",
        requested_by="skill-test",
        metadata={
            "artifact_contract": {
                "required_metrics": ["accuracy"],
                "required_outputs": ["skill-metrics.json"],
            },
        },
    )
    heartbeat = tools["research_experiment_heartbeat"](
        experiment_id=run["id"],
        summary="External execution heartbeat.",
        metrics={"step": 3},
    )
    result = tools["research_experiment_result"](
        experiment_id=run["id"],
        summary="External execution completed.",
        status="completed",
        metrics={"accuracy": 0.95},
        output_files=["outputs/skill-metrics.json"],
    )
    events = tools["research_experiment_events"](run["id"], limit=10)
    contract = tools["research_experiment_contract"](run["id"])

    assert configured["experiment"]["execution"]["mode"] == "external"
    assert configured["experiment"]["execution"]["result_bundle_file"] == "analysis-summary.json"
    assert configured["experiment"]["execution"]["result_bundle_schema"] == "analysis_summary.v1"
    assert configured["experiment"]["execution"]["environment"]["RC_QUEUE"] == "external"
    assert heartbeat["event"]["event_type"] == "heartbeat"
    assert result["event"]["event_type"] == "completion"
    assert events[0]["event_type"] == "completion"
    assert contract["passed"] is True
    assert tools["research_experiment_remediation"](run["id"])["action_count"] == 0

    workdir = tmp_path / "skill-command-run"
    workdir.mkdir()
    command_run = tools["research_experiment_log"](
        project_id=project["id"],
        workflow_id=workflow["id"],
        name="command-run",
        status="planned",
        claim_ids=[claim["id"]],
        metadata={"experiment_kind": "baseline"},
    )
    tools["research_experiment_update_execution"](
        experiment_id=command_run["id"],
        mode="command",
        command=[
            sys.executable,
            "-c",
            (
                "import json, pathlib; "
                "pathlib.Path('metrics.json').write_text("
                "json.dumps({'accuracy': 0.96, 'robust_accuracy': 0.9}), "
                "encoding='utf-8')"
            ),
        ],
        working_dir=str(workdir),
        metadata={
            "metrics_file": "metrics.json",
            "output_files": ["metrics.json"],
        },
    )
    launched = tools["research_experiment_launch"](command_run["id"])

    assert launched["executed"] is True
    assert launched["experiment"]["status"] == "completed"
    assert launched["experiment"]["metrics"]["accuracy"] == 0.96

    remediation_run = tools["research_experiment_log"](
        project_id=project["id"],
        workflow_id=workflow["id"],
        name="remediation-run",
        status="planned",
    )
    tools["research_experiment_update_execution"](
        experiment_id=remediation_run["id"],
        mode="external",
        metadata={
            "artifact_contract": {
                "required_metrics": ["accuracy"],
                "required_outputs": ["report.json"],
                "required_artifact_types": ["analysis"],
            },
        },
    )
    tools["research_experiment_update"](
        experiment_id=remediation_run["id"],
        status="completed",
        metrics={},
        output_files=[],
        notes="Deliberately missing contract outputs.",
    )
    remediation = tools["research_experiment_remediation"](remediation_run["id"])
    artifact = tools["research_artifact_upsert"](
        project_id=project["id"],
        workflow_id=workflow["id"],
        experiment_id=remediation_run["id"],
        artifact_type="analysis",
        title="Remediation analysis",
        path="outputs/remediation-analysis.md",
        source_type="experiment",
        source_id=remediation_run["id"],
    )

    assert remediation["required"] is True
    assert remediation["action_count"] == 3
    assert remediation["actions"][2]["suggested_tool"] == "research_artifact_upsert"
    assert artifact["artifact_type"] == "analysis"

    executable_artifact = tmp_path / "skill-auto-analysis.md"
    executable_artifact.write_text("skill generated analysis", encoding="utf-8")
    execute_run = tools["research_experiment_log"](
        project_id=project["id"],
        workflow_id=workflow["id"],
        name="execute-task-run",
        status="completed",
    )
    tools["research_experiment_update_execution"](
        experiment_id=execute_run["id"],
        mode="external",
        metadata={
            "artifact_contract": {
                "required_artifact_types": ["analysis"],
            },
        },
    )
    task_workflow = tools["research_workflow_add_task"](
        workflow_id=workflow["id"],
        stage="experiment_run",
        title="Publish analysis artifact from skill",
        assignee="agent",
        metadata={
            "task_kind": "experiment_contract_remediation",
            "remediation_key": f"{execute_run['id']}:artifact:analysis",
            "experiment_id": execute_run["id"],
            "action_type": "publish_artifact",
            "target": "analysis",
            "payload_hint": {
                "project_id": project["id"],
                "workflow_id": workflow["id"],
                "experiment_id": execute_run["id"],
                "artifact_type": "analysis",
                "title": "execute-task-run analysis",
                "path": str(executable_artifact),
                "source_type": "experiment",
                "source_id": execute_run["id"],
            },
            "retry_policy": {
                "max_attempts": 2,
                "backoff_minutes": 15,
            },
        },
    )
    task_id = task_workflow["tasks"][-1]["id"]
    executed_task = tools["research_workflow_task_execute"](
        workflow["id"],
        task_id,
    )
    fetched_task = tools["research_workflow_task_get"](
        workflow["id"],
        task_id,
    )
    execute_contract = tools["research_experiment_contract"](execute_run["id"])

    assert executed_task["executed"] is True
    assert fetched_task["status"] == "completed"
    assert fetched_task["execution_count"] == 1
    assert execute_contract["passed"] is True

    bundle_workdir = tmp_path / "skill-bundle-artifact-remediation"
    bundle_workdir.mkdir()
    (bundle_workdir / "analysis.md").write_text(
        "bundle generated analysis",
        encoding="utf-8",
    )
    (bundle_workdir / "analysis-summary.json").write_text(
        '{"result_bundle":{"artifacts":[{"artifact_type":"analysis","path":"analysis.md","title":"Bundle analysis"}]}}',
        encoding="utf-8",
    )
    bundle_run = tools["research_experiment_log"](
        project_id=project["id"],
        workflow_id=workflow["id"],
        name="bundle-artifact-execute-task-run",
        status="completed",
        output_files=[str(bundle_workdir / "analysis-summary.json")],
    )
    tools["research_experiment_update_execution"](
        experiment_id=bundle_run["id"],
        mode="external",
        working_dir=str(bundle_workdir),
        metadata={
            "artifact_contract": {
                "required_artifact_types": ["analysis"],
            },
        },
    )
    bundle_task_workflow = tools["research_workflow_add_task"](
        workflow_id=workflow["id"],
        stage="experiment_run",
        title="Publish analysis artifact from bundle",
        assignee="agent",
        metadata={
            "task_kind": "experiment_contract_remediation",
            "remediation_key": f"{bundle_run['id']}:artifact:analysis",
            "experiment_id": bundle_run["id"],
            "action_type": "publish_artifact",
            "target": "analysis",
            "payload_hint": {
                "artifact_type": "analysis",
            },
            "retry_policy": {
                "max_attempts": 2,
                "backoff_minutes": 15,
            },
        },
    )
    bundle_task_id = bundle_task_workflow["tasks"][-1]["id"]
    executed_bundle_task = tools["research_workflow_task_execute"](
        workflow["id"],
        bundle_task_id,
    )
    bundle_contract = tools["research_experiment_contract"](bundle_run["id"])
    bundle_artifacts = tools["research_artifacts_list"](
        project_id=project["id"],
        artifact_type="analysis",
    )

    assert executed_bundle_task["executed"] is True
    assert bundle_contract["passed"] is True
    assert any(
        item["path"].endswith("analysis.md")
        and item["title"] == "Bundle analysis"
        for item in bundle_artifacts
    )

    metric_workdir = tmp_path / "skill-metric-remediation"
    metric_workdir.mkdir()
    (metric_workdir / "metrics.json").write_text('{"accuracy": 0.92}', encoding="utf-8")
    metric_run = tools["research_experiment_log"](
        project_id=project["id"],
        workflow_id=workflow["id"],
        name="metric-execute-task-run",
        status="completed",
    )
    tools["research_experiment_update_execution"](
        experiment_id=metric_run["id"],
        mode="external",
        working_dir=str(metric_workdir),
        metadata={
            "metrics_file": "metrics.json",
            "artifact_contract": {
                "required_metrics": ["accuracy"],
            },
        },
    )
    metric_task_workflow = tools["research_workflow_add_task"](
        workflow_id=workflow["id"],
        stage="experiment_run",
        title="Record accuracy metric",
        description="Resolve the missing accuracy value from metrics.json.",
        assignee="agent",
        metadata={
            "task_kind": "experiment_contract_remediation",
            "remediation_key": f"{metric_run['id']}:metric:accuracy",
            "experiment_id": metric_run["id"],
            "action_type": "record_metric",
            "target": "accuracy",
            "retry_policy": {
                "max_attempts": 2,
                "backoff_minutes": 15,
            },
        },
    )
    metric_task_id = metric_task_workflow["tasks"][-1]["id"]
    executed_metric_task = tools["research_workflow_task_execute"](
        workflow["id"],
        metric_task_id,
    )
    fetched_metric_task = tools["research_workflow_task_get"](
        workflow["id"],
        metric_task_id,
    )
    metric_contract = tools["research_experiment_contract"](metric_run["id"])
    metric_run_after = tools["research_experiment_get"](metric_run["id"])

    assert executed_metric_task["executed"] is True
    assert fetched_metric_task["status"] == "completed"
    assert fetched_metric_task["execution_count"] == 1
    assert metric_run_after["metrics"]["accuracy"] == 0.92
    assert metric_contract["passed"] is True

    report_workdir = tmp_path / "skill-report-metric-remediation"
    report_workdir.mkdir()
    (report_workdir / "report.json").write_text(
        '{"summary": {"accuracy": 0.94}, "items": [{"metric": "accuracy", "value": 0.94}]}',
        encoding="utf-8",
    )
    report_run = tools["research_experiment_log"](
        project_id=project["id"],
        workflow_id=workflow["id"],
        name="report-metric-execute-task-run",
        status="completed",
        output_files=[str(report_workdir / "report.json")],
    )
    tools["research_experiment_update_execution"](
        experiment_id=report_run["id"],
        mode="external",
        working_dir=str(report_workdir),
        metadata={
            "artifact_contract": {
                "required_metrics": ["accuracy"],
            },
        },
    )
    report_task_workflow = tools["research_workflow_add_task"](
        workflow_id=workflow["id"],
        stage="experiment_run",
        title="Record accuracy from report artifact",
        description="Resolve the missing accuracy value from report.json.",
        assignee="agent",
        metadata={
            "task_kind": "experiment_contract_remediation",
            "remediation_key": f"{report_run['id']}:metric:accuracy",
            "experiment_id": report_run["id"],
            "action_type": "record_metric",
            "target": "accuracy",
            "retry_policy": {
                "max_attempts": 2,
                "backoff_minutes": 15,
            },
        },
    )
    report_task_id = report_task_workflow["tasks"][-1]["id"]
    executed_report_task = tools["research_workflow_task_execute"](
        workflow["id"],
        report_task_id,
    )
    report_contract = tools["research_experiment_contract"](report_run["id"])
    report_run_after = tools["research_experiment_get"](report_run["id"])

    assert executed_report_task["executed"] is True
    assert report_run_after["metrics"]["accuracy"] == 0.94
    assert report_contract["passed"] is True

    notebook_workdir = tmp_path / "skill-notebook-metric-remediation"
    notebook_workdir.mkdir()
    (notebook_workdir / "analysis.ipynb").write_text(
        '{"cells":[{"cell_type":"code","execution_count":1,"metadata":{},'
        '"outputs":[{"output_type":"display_data","data":{"application/json":{"metrics":{"accuracy":0.97}}},"metadata":{}}],'
        '"source":["print(\'done\')"]}],"metadata":{},"nbformat":4,"nbformat_minor":5}',
        encoding="utf-8",
    )
    notebook_run = tools["research_experiment_log"](
        project_id=project["id"],
        workflow_id=workflow["id"],
        name="notebook-metric-execute-task-run",
        status="completed",
        output_files=[str(notebook_workdir / "analysis.ipynb")],
    )
    tools["research_experiment_update_execution"](
        experiment_id=notebook_run["id"],
        mode="external",
        working_dir=str(notebook_workdir),
        metadata={
            "artifact_contract": {
                "required_metrics": ["accuracy"],
            },
        },
    )
    notebook_task_workflow = tools["research_workflow_add_task"](
        workflow_id=workflow["id"],
        stage="experiment_run",
        title="Record accuracy from notebook output",
        description="Resolve the missing accuracy value from analysis.ipynb.",
        assignee="agent",
        metadata={
            "task_kind": "experiment_contract_remediation",
            "remediation_key": f"{notebook_run['id']}:metric:accuracy",
            "experiment_id": notebook_run["id"],
            "action_type": "record_metric",
            "target": "accuracy",
            "retry_policy": {
                "max_attempts": 2,
                "backoff_minutes": 15,
            },
        },
    )
    notebook_task_id = notebook_task_workflow["tasks"][-1]["id"]
    executed_notebook_task = tools["research_workflow_task_execute"](
        workflow["id"],
        notebook_task_id,
    )
    notebook_contract = tools["research_experiment_contract"](notebook_run["id"])
    notebook_run_after = tools["research_experiment_get"](notebook_run["id"])

    assert executed_notebook_task["executed"] is True
    assert notebook_run_after["metrics"]["accuracy"] == 0.97
    assert notebook_contract["passed"] is True


def test_research_project_blocker_skill_actions(monkeypatch, tmp_path) -> None:
    state_path = tmp_path / "shared-research-state.json"
    monkeypatch.setenv("RESEARCHCLAW_RESEARCH_STATE_PATH", str(state_path))

    tools = register()
    service = ResearchService(store=JsonResearchStore(state_path))

    project = tools["research_project_create"](name="Skill Project Blockers")
    workflow = tools["research_workflow_create"](
        project_id=project["id"],
        title="Skill blocker workflow",
    )

    artifact_path = tmp_path / "skill-project-analysis.md"
    artifact_path.write_text("analysis output", encoding="utf-8")

    run = tools["research_experiment_log"](
        project_id=project["id"],
        workflow_id=workflow["id"],
        name="skill-project-gap-run",
        status="completed",
        metadata={"experiment_kind": "baseline"},
    )
    tools["research_experiment_update_execution"](
        experiment_id=run["id"],
        mode="external",
        metadata={
            "artifact_contract": {
                "required_artifact_types": ["analysis"],
            },
        },
    )
    tools["research_workflow_add_task"](
        workflow_id=workflow["id"],
        stage="experiment_run",
        title="Publish missing analysis artifact",
        description="Attach the analysis artifact back to the experiment.",
        assignee="agent",
        metadata={
            "task_kind": "experiment_contract_remediation",
            "remediation_key": f"{run['id']}:artifact:analysis",
            "experiment_id": run["id"],
            "action_type": "publish_artifact",
            "target": "analysis",
            "suggested_tool": "research_artifact_upsert",
            "payload_hint": {
                "artifact_type": "analysis",
                "title": "Recovered analysis artifact",
                "path": str(artifact_path),
            },
        },
    )
    state = asyncio.run(service.load_state())
    state.workflows[0].current_stage = "experiment_run"
    state.workflows[0].status = "blocked"
    state.workflows[0].error = "Ready for project blocker handling."
    asyncio.run(service.save_state(state))

    execute_result = tools["research_project_blockers_execute"](
        project["id"],
        workflow_limit=3,
        task_limit=2,
    )
    contract = tools["research_experiment_contract"](run["id"])
    workflow_after_execute = tools["research_workflow_get"](workflow["id"])

    assert execute_result["executed_count"] == 1
    assert contract["passed"] is True
    assert workflow_after_execute["current_stage"] == "result_analysis"

    resumed = tools["research_project_blockers_resume"](
        project["id"],
        workflow_limit=3,
    )
    workflow_after = tools["research_workflow_get"](workflow["id"])

    assert resumed["resumed_count"] == 0
    assert resumed["skipped"] is True
    assert workflow_after["current_stage"] == "result_analysis"
