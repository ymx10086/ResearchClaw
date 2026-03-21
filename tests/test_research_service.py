from __future__ import annotations

import asyncio

from researchclaw.research import JsonResearchStore, ResearchService


def test_research_service_workflow_notes_and_claim_graph(tmp_path) -> None:
    async def _run() -> None:
        service = ResearchService(
            store=JsonResearchStore(tmp_path / "research-state.json"),
        )

        project = await service.create_project(name="Project Alpha")
        workflow = await service.create_workflow(
            project_id=project.id,
            title="Robustness study",
            goal="Validate the main robustness hypothesis.",
        )

        assert workflow.status == "running"
        assert workflow.current_stage == "literature_search"
        assert len(workflow.tasks) == 1

        workflow = await service.update_workflow_task(
            workflow_id=workflow.id,
            task_id=workflow.tasks[0].id,
            status="completed",
            summary="Core papers shortlisted.",
        )

        assert workflow.current_stage == "paper_reading"
        assert workflow.status == "running"
        assert len(workflow.tasks) == 2

        note = await service.create_note(
            project_id=project.id,
            title="Reading note",
            content="The method reports stronger robustness under shift.",
            workflow_id=workflow.id,
            note_type="paper_note",
            paper_refs=["ArXiv:2501.00001"],
            tags=["reading", "robustness"],
        )

        claim = await service.create_claim(
            project_id=project.id,
            workflow_id=workflow.id,
            text="The method improves robustness under distribution shift.",
            note_ids=[note.id],
        )

        evidence = await service.attach_evidence(
            project_id=project.id,
            claim_ids=[claim.id],
            evidence_type="note",
            summary="Reading note captures the robustness result.",
            source_type="note",
            source_id=note.id,
            title=note.title,
            locator="summary",
            note_id=note.id,
            workflow_id=workflow.id,
        )

        graph = await service.get_claim_graph(claim.id)
        dashboard = await service.get_project_dashboard(project.id)

        assert graph["claim"].id == claim.id
        assert [item.id for item in graph["notes"]] == [note.id]
        assert [item.id for item in graph["evidences"]] == [evidence.id]
        assert dashboard["counts"]["workflows"] == 1
        assert dashboard["counts"]["notes"] == 1
        assert dashboard["counts"]["claims"] == 1
        assert dashboard["health"]["workflows"]["running"] == 1
        assert dashboard["health"]["experiments"]["contract_passed"] == 0
        assert dashboard["health"]["remediation"]["open_tasks"] == 0

    asyncio.run(_run())


def test_research_service_dashboard_surfaces_execution_health(tmp_path) -> None:
    async def _run() -> None:
        service = ResearchService(
            store=JsonResearchStore(tmp_path / "research-state.json"),
        )

        project = await service.create_project(
            name="Dashboard Health Project",
            result_bundle_schemas=[
                {
                    "name": "analysis_summary.v1",
                    "required_metrics": ["accuracy"],
                    "required_outputs": ["report.json"],
                    "required_artifact_types": ["analysis"],
                },
            ],
        )
        workflow = await service.create_workflow(
            project_id=project.id,
            title="Dashboard health workflow",
        )
        for _ in range(5):
            current_task = workflow.tasks[-1]
            workflow = await service.update_workflow_task(
                workflow_id=workflow.id,
                task_id=current_task.id,
                status="completed",
                summary="Advance to experiment_run for dashboard health coverage.",
            )
        assert workflow.current_stage == "experiment_run"

        run = await service.log_experiment(
            project_id=project.id,
            workflow_id=workflow.id,
            name="health-run",
            status="planned",
        )
        await service.configure_experiment_execution(
            experiment_id=run.id,
            patch={
                "mode": "command",
                "result_bundle_schema": "analysis_summary.v1",
            },
        )
        run = await service.update_experiment(
            experiment_id=run.id,
            status="completed",
            metrics={"accuracy": 0.91},
            output_files=["outputs/report.json"],
            metadata={
                "result_bundle_validation": {
                    "enabled": True,
                    "schema_name": "analysis_summary.v1",
                    "schema_found": True,
                    "passed": False,
                    "missing_sections": ["artifacts"],
                    "missing_metrics": [],
                    "missing_outputs": [],
                    "missing_artifact_types": ["analysis"],
                },
            },
        )
        workflow = await service.add_workflow_task(
            workflow_id=workflow.id,
            title="Resolve experiment contract blockers",
            description="Follow up on missing bundle artifacts.",
            stage="experiment_run",
            assignee="agent",
            metadata={
                "task_kind": "experiment_contract_followup",
                "contract_failure_run_ids": [run.id],
            },
        )
        followup_task = workflow.tasks[-1]
        workflow = await service.update_workflow_task(
            workflow_id=workflow.id,
            task_id=followup_task.id,
            status="blocked",
            summary="Blocked until the missing analysis artifact is published.",
        )
        workflow = await service.add_workflow_task(
            workflow_id=workflow.id,
            title="Publish missing analysis artifact",
            description="Attach the missing analysis artifact back to the experiment.",
            stage="experiment_run",
            due_at="2000-01-01T00:00:00+00:00",
            assignee="agent",
            metadata={
                "task_kind": "experiment_contract_remediation",
                "remediation_key": f"{run.id}:artifact:analysis",
                "retry_policy": {"max_attempts": 2, "backoff_minutes": 30},
            },
        )
        remediation_task = workflow.tasks[-1]
        await service.record_workflow_task_dispatch(
            workflow_id=workflow.id,
            task_id=remediation_task.id,
            summary="Remediation dispatched to the agent.",
        )
        await service.record_workflow_task_execution(
            workflow_id=workflow.id,
            task_id=remediation_task.id,
            summary="Remediation execution attempted once.",
            error="Artifact not yet available.",
        )

        dashboard = await service.get_project_dashboard(project.id)

        assert dashboard["health"]["workflows"]["blocked"] == 1
        assert dashboard["health"]["experiments"]["completed"] == 1
        assert dashboard["health"]["experiments"]["contract_failed"] == 1
        assert dashboard["health"]["experiments"]["bundle_failed"] == 1
        assert dashboard["health"]["remediation"]["open_tasks"] == 1
        assert dashboard["health"]["remediation"]["due_tasks"] == 1
        assert dashboard["health"]["remediation"]["dispatch_attempts"] == 1
        assert dashboard["health"]["remediation"]["execution_attempts"] == 1
        assert dashboard["recent_blockers"][0]["workflow_id"] == workflow.id
        assert dashboard["recent_blockers"][0]["open_remediation_tasks"] == 1
        assert dashboard["recent_blockers"][0]["actionable_tasks"][0]["task_id"] == remediation_task.id
        assert dashboard["recent_blockers"][0]["actionable_tasks"][0]["action_type"] == ""
        assert dashboard["recent_blockers"][0]["actionable_tasks"][0]["can_dispatch"] is False
        assert dashboard["recent_blockers"][0]["actionable_tasks"][0]["can_execute"] is True

    asyncio.run(_run())


def test_research_service_experiments_and_proactive_reminders(
    tmp_path,
    monkeypatch,
) -> None:
    async def _run() -> None:
        service = ResearchService(
            store=JsonResearchStore(tmp_path / "research-state.json"),
        )

        project = await service.create_project(name="Project Beta")
        await service.add_project_paper_watch(
            project_id=project.id,
            query="distribution shift robustness",
            max_results=5,
            check_every_hours=1,
        )
        workflow = await service.create_workflow(
            project_id=project.id,
            title="Long-running workflow",
        )
        claim = await service.create_claim(
            project_id=project.id,
            workflow_id=workflow.id,
            text="Ablation confirms the contribution of the regularizer.",
        )

        run = await service.log_experiment(
            project_id=project.id,
            workflow_id=workflow.id,
            name="ablation-1",
            status="completed",
            parameters={"lr": 0.001},
            metrics={"accuracy": 0.91, "f1": 0.88},
            output_files=["results.csv", "figure.png"],
            claim_ids=[claim.id],
        )

        compare = await service.compare_experiments([run.id])
        graph = await service.get_claim_graph(claim.id)

        assert compare["runs"][0]["metrics"]["accuracy"] == 0.91
        assert len(run.artifact_ids) == 2
        assert any(item.experiment_id == run.id for item in graph["evidences"])
        assert any(item.id == run.id for item in graph["experiments"])

        state = await service.load_state()
        state.workflows[0].last_run_at = "2000-01-01T00:00:00+00:00"
        await service.save_state(state)

        monkeypatch.setattr(
            service,
            "_search_papers",
            lambda **_: [
                {"title": "Paper A", "arxiv_id": "2501.00001"},
                {"title": "Paper B", "arxiv_id": "2501.00002"},
            ],
        )

        reminders = await service.generate_proactive_reminders(stale_hours=1)
        reminder_types = {item.reminder_type for item in reminders}

        assert "workflow_timeout" in reminder_types
        assert "experiment_complete" in reminder_types
        assert "new_paper_tracking" in reminder_types

    asyncio.run(_run())


def test_research_service_execution_policy_updates(tmp_path) -> None:
    async def _run() -> None:
        service = ResearchService(
            store=JsonResearchStore(tmp_path / "research-state.json"),
        )

        project = await service.create_project(name="Policy Project")
        workflow = await service.create_workflow(
            project_id=project.id,
            title="Policy workflow",
        )

        workflow = await service.update_workflow_execution_policy(
            workflow_id=workflow.id,
            patch={
                "enabled": True,
                "mode": "stale_or_blocked",
                "stale_hours": 6,
                "cooldown_minutes": 30,
                "max_auto_runs_per_day": 3,
                "allowed_stages": ["literature_search", "paper_reading"],
                "notify_after_execution": False,
            },
        )

        assert workflow.execution_policy.enabled is True
        assert workflow.execution_policy.mode == "stale_or_blocked"
        assert workflow.execution_policy.stale_hours == 6
        assert workflow.execution_policy.cooldown_minutes == 30
        assert workflow.execution_policy.max_auto_runs_per_day == 3
        assert workflow.execution_policy.allowed_stages == [
            "literature_search",
            "paper_reading",
        ]
        assert workflow.execution_policy.notify_after_execution is False

    asyncio.run(_run())


def test_research_service_note_artifact_linking(tmp_path) -> None:
    async def _run() -> None:
        service = ResearchService(
            store=JsonResearchStore(tmp_path / "research-state.json"),
        )

        project = await service.create_project(name="Artifact Project")
        workflow = await service.create_workflow(
            project_id=project.id,
            title="Artifact workflow",
        )
        artifact = await service.upsert_artifact(
            project_id=project.id,
            workflow_id=workflow.id,
            title="Sample paper",
            artifact_type="paper",
            source_type="semantic_scholar",
            source_id="paper-1",
            metadata={"abstract": "A useful paper."},
        )
        note = await service.create_note(
            project_id=project.id,
            workflow_id=workflow.id,
            title="Paper note",
            content="This note is linked to the paper artifact.",
            note_type="paper_note",
            artifact_ids=[artifact.id],
            paper_refs=["SemanticScholar:paper-1"],
        )

        artifacts = await service.list_artifacts(
            project_id=project.id,
            workflow_id=workflow.id,
            artifact_type="paper",
        )

        assert artifacts[0].id == artifact.id
        assert note.id in artifacts[0].note_ids
        assert artifact.id in note.artifact_ids

    asyncio.run(_run())


def test_research_service_updates_claims_and_experiments(tmp_path) -> None:
    async def _run() -> None:
        service = ResearchService(
            store=JsonResearchStore(tmp_path / "research-state.json"),
        )

        project = await service.create_project(name="Mutable Research Project")
        workflow = await service.create_workflow(
            project_id=project.id,
            title="Mutable workflow",
        )
        claim = await service.create_claim(
            project_id=project.id,
            workflow_id=workflow.id,
            text="The ablation should weaken robustness under shift.",
        )
        note = await service.create_note(
            project_id=project.id,
            workflow_id=workflow.id,
            title="Experiment observation",
            content="The completed run weakens robust accuracy.",
            note_type="experiment_note",
        )
        run = await service.log_experiment(
            project_id=project.id,
            workflow_id=workflow.id,
            name="ablation-plan",
            status="planned",
            claim_ids=[claim.id],
            metadata={"experiment_kind": "ablation"},
        )

        run = await service.update_experiment(
            experiment_id=run.id,
            status="completed",
            metrics={"accuracy": 0.77, "robust_accuracy": 0.68},
            notes="Completed by the structured worker.",
            output_files=["runs/ablation-metrics.json", "runs/ablation-curve.png"],
            note_ids=[note.id],
            metadata={"stage": "experiment_run"},
        )
        claim = await service.update_claim(
            claim_id=claim.id,
            status="supported",
            confidence=0.83,
            note_ids=[note.id],
            artifact_ids=run.artifact_ids,
            metadata={"stage": "result_analysis"},
        )
        graph = await service.get_claim_graph(claim.id)

        assert run.status == "completed"
        assert note.id in run.note_ids
        assert len(run.artifact_ids) == 2
        assert claim.status == "supported"
        assert claim.confidence == 0.83
        assert note.id in claim.note_ids
        assert any(item.experiment_id == run.id for item in graph["evidences"])
        assert any(item.id == run.id for item in graph["experiments"])
        assert any(item.id in run.artifact_ids for item in graph["artifacts"])

    asyncio.run(_run())


def test_research_service_external_experiment_execution_timeline(tmp_path) -> None:
    async def _run() -> None:
        service = ResearchService(
            store=JsonResearchStore(tmp_path / "research-state.json"),
        )

        project = await service.create_project(name="External Execution Project")
        workflow = await service.create_workflow(
            project_id=project.id,
            title="External execution workflow",
        )
        claim = await service.create_claim(
            project_id=project.id,
            workflow_id=workflow.id,
            text="The external run should write results back into the graph.",
        )
        run = await service.log_experiment(
            project_id=project.id,
            workflow_id=workflow.id,
            name="external-run",
            status="planned",
            claim_ids=[claim.id],
        )

        configured = await service.configure_experiment_execution(
            experiment_id=run.id,
            patch={
                "mode": "external",
                "external_run_id": "job-123",
                "requested_by": "ci",
                "instructions": "Report heartbeats every few minutes.",
            },
        )
        heartbeat = await service.record_experiment_heartbeat(
            experiment_id=run.id,
            summary="The external run has started.",
            metrics={"step": 10},
        )
        result = await service.record_experiment_result(
            experiment_id=run.id,
            summary="The external run completed successfully.",
            status="completed",
            metrics={"accuracy": 0.92, "robust_accuracy": 0.88},
            output_files=["outputs/external-metrics.json"],
            notes="External executor uploaded the final metrics.",
        )
        events = await service.list_experiment_events(
            experiment_id=run.id,
            limit=10,
        )

        assert configured["experiment"].execution.mode == "external"
        assert configured["event"].event_type == "binding"
        assert heartbeat["experiment"].status == "running"
        assert heartbeat["event"].event_type == "heartbeat"
        assert result["experiment"].status == "completed"
        assert result["event"].event_type == "completion"
        assert result["experiment"].execution.last_heartbeat_at is not None
        assert result["experiment"].artifact_ids
        assert [item.event_type for item in events[:3]] == [
            "completion",
            "heartbeat",
            "binding",
        ]

    asyncio.run(_run())


def test_research_service_runner_profiles_seed_workflow_defaults(tmp_path) -> None:
    async def _run() -> None:
        service = ResearchService(
            store=JsonResearchStore(tmp_path / "research-state.json"),
        )

        project = await service.create_project(
            name="Runner Profile Project",
            execution_catalog=[
                {
                    "name": "local-benchmark",
                    "template": {
                        "mode": "command",
                        "command": ["python", "scripts/run.py", "--kind", "{experiment_kind}"],
                        "working_dir": "{output_dir}",
                        "environment": {
                            "RC_EXPERIMENT_KIND": "{experiment_kind}",
                        },
                        "parameter_overrides": {
                            "dataset": "{experiment_kind}_suite",
                        },
                        "input_data_overrides": {
                            "planned_stage": "{current_stage}",
                        },
                        "metadata": {
                            "metrics_file": "metrics.json",
                            "output_files": ["metrics.json"],
                        },
                    },
                    "artifact_contract": {
                        "required_metrics": ["accuracy", "robust_accuracy"],
                    },
                },
            ],
            default_experiment_runner={
                "enabled": True,
                "default": {
                    "catalog_entry": "local-benchmark",
                },
                "kind_overrides": {
                    "ablation": {
                        "instructions": "Use the ablation-specific command profile.",
                    },
                },
            },
        )
        project = await service.update_project(
            project_id=project.id,
            execution_catalog=[
                *[item.model_dump(mode="json") for item in project.execution_catalog],
                {
                    "name": "remote-stress",
                    "template": {
                        "mode": "external",
                        "instructions": "Dispatch stress tests to the remote queue.",
                    },
                    "artifact_contract": {
                        "required_outputs": ["stress-report.json"],
                    },
                },
            ],
            default_experiment_runner={
                "kind_overrides": {
                    "stress_test": {
                        "catalog_entry": "remote-stress",
                    },
                },
                "rules": [
                    {
                        "name": "failure-mode-remote",
                        "stages": ["experiment_plan"],
                        "hypothesis_kinds": ["failure_mode_probe"],
                        "template": {
                            "environment": {
                                "RC_QUEUE": "remote-shift",
                            },
                        },
                    },
                ],
            },
        )
        workflow = await service.create_workflow(
            project_id=project.id,
            title="Runner profile workflow",
        )
        workflow = await service.update_workflow_experiment_runner(
            workflow_id=workflow.id,
            patch={
                "kind_overrides": {
                    "baseline": {
                        "metadata": {
                            "profile_name": "baseline-default",
                        },
                    },
                },
            },
        )

        assert project.default_experiment_runner.enabled is True
        assert project.execution_catalog[0].name == "local-benchmark"
        assert (
            project.execution_catalog[0].artifact_contract["required_metrics"]
            == ["accuracy", "robust_accuracy"]
        )
        assert project.default_experiment_runner.default.catalog_entry == "local-benchmark"
        assert (
            project.default_experiment_runner.kind_overrides["stress_test"]["catalog_entry"]
            == "remote-stress"
        )
        assert workflow.experiment_runner.enabled is True
        assert workflow.experiment_runner.default.catalog_entry == "local-benchmark"
        assert (
            project.execution_catalog[1].artifact_contract["required_outputs"]
            == ["stress-report.json"]
        )
        assert (
            workflow.experiment_runner.kind_overrides["ablation"]["instructions"]
            == "Use the ablation-specific command profile."
        )
        assert (
            workflow.experiment_runner.kind_overrides["baseline"]["metadata"]["profile_name"]
            == "baseline-default"
        )
        assert workflow.experiment_runner.rules[0].name == "failure-mode-remote"
        assert workflow.experiment_runner.rules[0].hypothesis_kinds == [
            "failure_mode_probe",
        ]

    asyncio.run(_run())


def test_research_service_validates_experiment_artifact_contract(tmp_path) -> None:
    async def _run() -> None:
        service = ResearchService(
            store=JsonResearchStore(tmp_path / "research-state.json"),
        )

        project = await service.create_project(name="Contract Validation Project")
        workflow = await service.create_workflow(
            project_id=project.id,
            title="Contract validation workflow",
        )
        claim = await service.create_claim(
            project_id=project.id,
            workflow_id=workflow.id,
            text="The contract validator should report missing metrics and outputs.",
        )
        run = await service.log_experiment(
            project_id=project.id,
            workflow_id=workflow.id,
            name="contract-run",
            status="planned",
            claim_ids=[claim.id],
        )
        await service.configure_experiment_execution(
            experiment_id=run.id,
            patch={
                "mode": "command",
                "metadata": {
                    "artifact_contract": {
                        "required_metrics": ["accuracy", "calibration_error"],
                        "required_outputs": ["metrics.json", "report.json"],
                        "required_artifact_types": [
                            "generated_table",
                            "generated_figure",
                        ],
                    },
                },
            },
        )
        run = await service.update_experiment(
            experiment_id=run.id,
            status="completed",
            metrics={"accuracy": 0.91},
            output_files=["outputs/metrics.json"],
            notes="Only partial outputs were recorded.",
        )
        validation = await service.get_experiment_artifact_contract_validation(run.id)
        remediation = await service.get_experiment_contract_remediation(run.id)
        persisted = await service.get_experiment(run.id)

        assert validation["enabled"] is True
        assert validation["passed"] is False
        assert validation["missing_metrics"] == ["calibration_error"]
        assert validation["missing_outputs"] == ["report.json"]
        assert validation["missing_artifact_types"] == ["generated_figure"]
        assert remediation["required"] is True
        assert remediation["action_count"] == 3
        assert [item["action_type"] for item in remediation["actions"]] == [
            "record_metric",
            "archive_output",
            "publish_artifact",
        ]
        assert remediation["actions"][0]["action_key"].endswith(":metric:calibration_error")
        assert remediation["actions"][0]["assignee"] == "analyst"
        assert remediation["actions"][2]["assignee"] == "agent"
        assert remediation["actions"][2]["retry_policy"]["max_attempts"] == 2
        assert remediation["actions"][2]["suggested_tool"] == "research_artifact_upsert"
        assert persisted.metadata["contract_validation"]["passed"] is False
        assert persisted.metadata["contract_validation"]["remediation"]["action_count"] == 3

    asyncio.run(_run())


def test_research_service_derives_contract_from_result_bundle_schema(tmp_path) -> None:
    async def _run() -> None:
        service = ResearchService(
            store=JsonResearchStore(tmp_path / "research-state.json"),
        )

        project = await service.create_project(
            name="Schema Contract Project",
            result_bundle_schemas=[
                {
                    "name": "analysis_summary.v1",
                    "description": "Baseline analysis summary bundle",
                    "required_sections": ["metrics", "outputs", "artifacts"],
                    "required_metrics": ["accuracy", "calibration_error"],
                    "required_outputs": ["report.json"],
                    "required_artifact_types": ["analysis"],
                },
            ],
        )
        workflow = await service.create_workflow(
            project_id=project.id,
            title="Schema-derived contract workflow",
        )
        run = await service.log_experiment(
            project_id=project.id,
            workflow_id=workflow.id,
            name="schema-derived-run",
            status="planned",
        )
        configured = await service.configure_experiment_execution(
            experiment_id=run.id,
            patch={
                "mode": "command",
                "result_bundle_schema": "analysis_summary.v1",
            },
        )
        run = await service.update_experiment(
            experiment_id=run.id,
            status="completed",
            metrics={"accuracy": 0.93},
            output_files=["outputs/raw-metrics.json"],
            notes="Schema contract should drive remediation.",
        )
        validation = await service.get_experiment_artifact_contract_validation(run.id)

        assert (
            configured["experiment"].execution.metadata["artifact_contract"]["required_metrics"]
            == ["accuracy", "calibration_error"]
        )
        assert validation["enabled"] is True
        assert validation["passed"] is False
        assert validation["missing_metrics"] == ["calibration_error"]
        assert validation["missing_outputs"] == ["report.json"]
        assert validation["missing_artifact_types"] == ["analysis"]

    asyncio.run(_run())


def test_research_service_blocked_workflow_reminder_includes_remediation(tmp_path) -> None:
    async def _run() -> None:
        service = ResearchService(
            store=JsonResearchStore(tmp_path / "research-state.json"),
        )

        project = await service.create_project(name="Reminder Contract Project")
        workflow = await service.create_workflow(
            project_id=project.id,
            title="Reminder remediation workflow",
        )
        run = await service.log_experiment(
            project_id=project.id,
            workflow_id=workflow.id,
            name="blocked-contract-run",
            status="planned",
            metadata={"experiment_kind": "baseline"},
        )
        await service.configure_experiment_execution(
            experiment_id=run.id,
            patch={
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
        await service.update_experiment(
            experiment_id=run.id,
            status="completed",
            metrics={},
            output_files=[],
            notes="The experiment completed without the required contract outputs.",
        )

        state = await service.load_state()
        workflow_state = state.workflows[0]
        workflow_state.current_stage = "experiment_run"
        workflow_state.status = "blocked"
        workflow_state.error = "Artifact contract failed."
        experiment_stage = next(
            stage for stage in workflow_state.stages if stage.name == "experiment_run"
        )
        experiment_stage.status = "blocked"
        experiment_stage.blocked_reason = workflow_state.error
        await service.save_state(state)

        workflow = await service.add_workflow_task(
            workflow_id=workflow.id,
            stage="experiment_run",
            title="Resolve experiment contract gaps",
            description="Backfill missing metrics, outputs, or artifact types.",
            metadata={
                "task_kind": "experiment_contract_followup",
                "contract_failure_run_ids": [run.id],
            },
        )
        reminders = await service.preview_due_reminders(project_id=project.id, stale_hours=1)

        assert reminders
        reminder = reminders[0]
        assert reminder.reminder_type == "stage_stuck_followup"
        assert "1 run(s) need remediation" in reminder.summary
        assert reminder.context["blocked_task_title"] == "Resolve experiment contract gaps"
        assert len(reminder.context["contract_failures"]) == 1
        assert len(reminder.context["remediation_actions"]) == 3
        assert reminder.context["remediation_actions"][2]["suggested_tool"] == (
            "research_artifact_upsert"
        )
        assert workflow.tasks[-1].metadata["task_kind"] == "experiment_contract_followup"

    asyncio.run(_run())


def test_research_service_generates_task_level_remediation_reminders(tmp_path) -> None:
    async def _run() -> None:
        service = ResearchService(
            store=JsonResearchStore(tmp_path / "research-state.json"),
        )

        project = await service.create_project(name="Task Reminder Project")
        workflow = await service.create_workflow(
            project_id=project.id,
            title="Task reminder workflow",
        )
        workflow = await service.add_workflow_task(
            workflow_id=workflow.id,
            stage="experiment_run",
            title="Backfill robustness metric",
            description="Record the missing robustness metric before analysis.",
            assignee="analyst",
            metadata={
                "task_kind": "experiment_contract_remediation",
                "remediation_key": "run-1:metric:robust_accuracy",
                "suggested_tool": "research_experiment_update",
                "retry_policy": {
                    "max_attempts": 2,
                    "backoff_minutes": 30,
                },
            },
        )

        state = await service.load_state()
        workflow_state = state.workflows[0]
        workflow_state.current_stage = "experiment_run"
        workflow_state.status = "blocked"
        workflow_state.error = "Artifact contract failed."
        workflow_state.tasks[0].status = "blocked"
        await service.save_state(state)

        reminders = await service.generate_proactive_reminders(
            project_id=project.id,
            stale_hours=1,
        )
        state = await service.load_state()
        task = next(
            item
            for item in state.workflows[0].tasks
            if item.metadata.get("task_kind") == "experiment_contract_remediation"
        )
        task_reminders = [
            item for item in reminders if item.reminder_type == "remediation_task_followup"
        ]

        assert task_reminders
        assert task_reminders[0].task_id == task.id
        assert task_reminders[0].context["task_assignee"] == "analyst"
        assert task.dispatch_count == 1
        assert task.last_dispatch_at is not None

        second = await service.preview_due_reminders(
            project_id=project.id,
            stale_hours=1,
        )
        assert not any(item.reminder_type == "remediation_task_followup" for item in second)

        state = await service.load_state()
        task = next(
            item
            for item in state.workflows[0].tasks
            if item.metadata.get("task_kind") == "experiment_contract_remediation"
        )
        task.dispatch_count = 2
        task.last_dispatch_at = "2000-01-01T00:00:00+00:00"
        await service.save_state(state)

        third = await service.preview_due_reminders(
            project_id=project.id,
            stale_hours=1,
        )
        blocked = next(
            item for item in third if item.reminder_type == "stage_stuck_followup"
        )
        assert blocked.context["retry_exhausted_count"] == 1
        assert "exhausted retry budget" in blocked.summary

    asyncio.run(_run())


def test_research_service_records_manual_task_dispatch(tmp_path) -> None:
    async def _run() -> None:
        service = ResearchService(
            store=JsonResearchStore(tmp_path / "research-state.json"),
        )

        project = await service.create_project(name="Manual Dispatch Project")
        workflow = await service.create_workflow(
            project_id=project.id,
            title="Manual dispatch workflow",
        )
        workflow = await service.add_workflow_task(
            workflow_id=workflow.id,
            title="Follow up with the analyst",
            description="Send a direct reminder about the missing artifact.",
            assignee="analyst",
            metadata={
                "task_kind": "experiment_contract_remediation",
                "suggested_tool": "research_artifact_upsert",
            },
        )
        task_id = workflow.tasks[-1].id

        task = await service.get_workflow_task(
            workflow_id=workflow.id,
            task_id=task_id,
        )
        updated = await service.record_workflow_task_dispatch(
            workflow_id=workflow.id,
            task_id=task_id,
            summary="Manual follow-up dispatched.",
        )
        executed = await service.record_workflow_task_execution(
            workflow_id=workflow.id,
            task_id=task_id,
            summary="Manual remediation execution attempted.",
        )

        assert task.id == task_id
        assert updated.dispatch_count == 1
        assert updated.last_dispatch_at is not None
        assert updated.last_dispatch_summary == "Manual follow-up dispatched."
        assert updated.last_dispatch_error == ""
        assert executed.execution_count == 1
        assert executed.last_execution_at is not None
        assert executed.last_execution_summary == "Manual remediation execution attempted."
        assert executed.last_execution_error == ""

    asyncio.run(_run())
