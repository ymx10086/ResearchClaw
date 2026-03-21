"""Structured research workflow tools for the agent."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from ....constant import RESEARCH_STATE_FILE
from ....research import JsonResearchStore, ResearchService


def _run(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] = {}
    error: dict[str, BaseException] = {}

    def _worker() -> None:
        try:
            result["value"] = asyncio.run(coro)
        except BaseException as exc:  # pragma: no cover - defensive wrapper
            error["value"] = exc

    import threading

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join()

    if "value" in error:
        raise error["value"]
    return result.get("value")


def _resolve_state_path(agent: object | None) -> Path | None:
    env_path = os.environ.get("RESEARCHCLAW_RESEARCH_STATE_PATH", "").strip()
    if env_path:
        return Path(env_path).expanduser()

    working_dir = str(getattr(agent, "working_dir", "") or "").strip()
    if working_dir:
        return Path(working_dir).expanduser() / "research" / RESEARCH_STATE_FILE
    return None


def _service_for_agent(agent: object | None) -> ResearchService:
    return ResearchService(
        store=JsonResearchStore(_resolve_state_path(agent)),
    )


def _jsonify(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _jsonify(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify(item) for item in value]
    return value


def register(agent: object | None = None):
    """Expose structured research graph operations as agent tools."""

    service = _service_for_agent(agent)

    def research_projects_list() -> list[dict[str, Any]]:
        return [
            item.model_dump(mode="json")
            for item in _run(service.list_projects())
        ]

    def research_project_create(
        name: str,
        description: str = "",
        tags: list[str] | None = None,
        execution_catalog: list[dict[str, Any]] | None = None,
        result_bundle_schemas: list[dict[str, Any]] | None = None,
        default_experiment_runner: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        project = _run(
            service.create_project(
                name=name,
                description=description,
                tags=tags,
                execution_catalog=execution_catalog,
                result_bundle_schemas=result_bundle_schemas,
                default_experiment_runner=default_experiment_runner,
                metadata=metadata,
            ),
        )
        return project.model_dump(mode="json")

    def research_project_update(
        project_id: str,
        description: str | None = None,
        status: str | None = None,
        tags: list[str] | None = None,
        default_binding: dict[str, Any] | None = None,
        execution_catalog: list[dict[str, Any]] | None = None,
        result_bundle_schemas: list[dict[str, Any]] | None = None,
        default_experiment_runner: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        project = _run(
            service.update_project(
                project_id=project_id,
                description=description,
                status=status,
                tags=tags,
                default_binding=default_binding,
                execution_catalog=execution_catalog,
                result_bundle_schemas=result_bundle_schemas,
                default_experiment_runner=default_experiment_runner,
                metadata=metadata,
            ),
        )
        return project.model_dump(mode="json")

    def research_project_dashboard(project_id: str) -> dict[str, Any]:
        payload = _run(service.get_project_dashboard(project_id))
        return _jsonify(payload)

    def research_project_blockers_dispatch(
        project_id: str,
        workflow_limit: int = 3,
        task_limit: int = 2,
    ) -> dict[str, Any]:
        from ....research import ResearchWorkflowRuntime

        runtime = ResearchWorkflowRuntime(service=service)
        payload = _run(
            runtime.dispatch_project_blocker_tasks(
                project_id,
                workflow_limit=workflow_limit,
                task_limit=task_limit,
            ),
        )
        return _jsonify(payload)

    def research_project_blockers_execute(
        project_id: str,
        workflow_limit: int = 3,
        task_limit: int = 2,
    ) -> dict[str, Any]:
        from ....research import ResearchWorkflowRuntime

        runtime = ResearchWorkflowRuntime(service=service)
        payload = _run(
            runtime.execute_project_blocker_tasks(
                project_id,
                workflow_limit=workflow_limit,
                task_limit=task_limit,
            ),
        )
        return _jsonify(payload)

    def research_project_blockers_resume(
        project_id: str,
        workflow_limit: int = 3,
    ) -> dict[str, Any]:
        from ....research import ResearchWorkflowRuntime

        runtime = ResearchWorkflowRuntime(service=service)
        payload = _run(
            runtime.resume_project_ready_workflows(
                project_id,
                workflow_limit=workflow_limit,
            ),
        )
        return _jsonify(payload)

    def research_workflows_list(
        project_id: str = "",
        status: str = "",
    ) -> list[dict[str, Any]]:
        return [
            item.model_dump(mode="json")
            for item in _run(
                service.list_workflows(project_id=project_id, status=status),
            )
        ]

    def research_workflow_create(
        project_id: str,
        title: str,
        goal: str = "",
        bindings: dict[str, Any] | None = None,
        execution_policy: dict[str, Any] | None = None,
        experiment_runner: dict[str, Any] | None = None,
        auto_start: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workflow = _run(
            service.create_workflow(
                project_id=project_id,
                title=title,
                goal=goal,
                bindings=bindings,
                execution_policy=execution_policy,
                experiment_runner=experiment_runner,
                auto_start=auto_start,
                metadata=metadata,
            ),
        )
        return workflow.model_dump(mode="json")

    def research_workflow_get(workflow_id: str) -> dict[str, Any]:
        workflow = _run(service.get_workflow(workflow_id))
        return workflow.model_dump(mode="json")

    def research_workflow_remediation(workflow_id: str) -> dict[str, Any]:
        return _run(service.get_workflow_contract_remediation_context(workflow_id))

    def research_workflow_task_get(
        workflow_id: str,
        task_id: str,
    ) -> dict[str, Any]:
        task = _run(
            service.get_workflow_task(
                workflow_id=workflow_id,
                task_id=task_id,
            ),
        )
        return task.model_dump(mode="json")

    def research_workflow_task_execute(
        workflow_id: str,
        task_id: str,
    ) -> dict[str, Any]:
        from ....research import ResearchWorkflowRuntime

        runtime = ResearchWorkflowRuntime(service=service)
        payload = _run(
            runtime.execute_workflow_task(
                workflow_id=workflow_id,
                task_id=task_id,
            ),
        )
        return {
            key: value.model_dump(mode="json")
            if hasattr(value, "model_dump")
            else value
            for key, value in payload.items()
        }

    def research_workflow_add_task(
        workflow_id: str,
        title: str,
        description: str = "",
        stage: str | None = None,
        depends_on: list[str] | None = None,
        due_at: str | None = None,
        assignee: str = "agent",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workflow = _run(
            service.add_workflow_task(
                workflow_id=workflow_id,
                title=title,
                description=description,
                stage=stage,
                depends_on=depends_on,
                due_at=due_at,
                assignee=assignee,
                metadata=metadata,
            ),
        )
        return workflow.model_dump(mode="json")

    def research_workflow_update_task(
        workflow_id: str,
        task_id: str,
        status: str | None = None,
        summary: str | None = None,
        due_at: str | None = None,
        note_ids: list[str] | None = None,
        claim_ids: list[str] | None = None,
        artifact_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        workflow = _run(
            service.update_workflow_task(
                workflow_id=workflow_id,
                task_id=task_id,
                status=status,
                summary=summary,
                due_at=due_at,
                note_ids=note_ids,
                claim_ids=claim_ids,
                artifact_ids=artifact_ids,
            ),
        )
        return workflow.model_dump(mode="json")

    def research_workflow_tick(workflow_id: str) -> dict[str, Any]:
        workflow = _run(service.tick_workflow(workflow_id))
        return workflow.model_dump(mode="json")

    def research_workflow_update_execution_policy(
        workflow_id: str,
        enabled: bool | None = None,
        mode: str | None = None,
        stale_hours: int | None = None,
        cooldown_minutes: int | None = None,
        max_auto_runs_per_day: int | None = None,
        allowed_stages: list[str] | None = None,
        notify_after_execution: bool | None = None,
    ) -> dict[str, Any]:
        workflow = _run(
            service.update_workflow_execution_policy(
                workflow_id=workflow_id,
                patch={
                    "enabled": enabled,
                    "mode": mode,
                    "stale_hours": stale_hours,
                    "cooldown_minutes": cooldown_minutes,
                    "max_auto_runs_per_day": max_auto_runs_per_day,
                    "allowed_stages": allowed_stages,
                    "notify_after_execution": notify_after_execution,
                },
            ),
        )
        return workflow.model_dump(mode="json")

    def research_workflow_update_experiment_runner(
        workflow_id: str,
        enabled: bool | None = None,
        default: dict[str, Any] | None = None,
        kind_overrides: dict[str, dict[str, Any] | None] | None = None,
        rules: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        patch: dict[str, Any] = {}
        if enabled is not None:
            patch["enabled"] = enabled
        if default is not None:
            patch["default"] = default
        if kind_overrides is not None:
            patch["kind_overrides"] = kind_overrides
        if rules is not None:
            patch["rules"] = rules
        workflow = _run(
            service.update_workflow_experiment_runner(
                workflow_id=workflow_id,
                patch=patch,
            ),
        )
        return workflow.model_dump(mode="json")

    def research_note_create(
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
    ) -> dict[str, Any]:
        note = _run(
            service.create_note(
                project_id=project_id,
                title=title,
                content=content,
                note_type=note_type,
                workflow_id=workflow_id,
                experiment_ids=experiment_ids,
                claim_ids=claim_ids,
                artifact_ids=artifact_ids,
                paper_refs=paper_refs,
                tags=tags,
                metadata=metadata,
            ),
        )
        return note.model_dump(mode="json")

    def research_notes_search(
        query: str = "",
        project_id: str = "",
        workflow_id: str = "",
        claim_id: str = "",
        experiment_id: str = "",
        note_type: str = "",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        return [
            item.model_dump(mode="json")
            for item in _run(
                service.list_notes(
                    query=query,
                    project_id=project_id,
                    workflow_id=workflow_id,
                    claim_id=claim_id,
                    experiment_id=experiment_id,
                    note_type=note_type,
                    limit=limit,
                ),
            )
        ]

    def research_artifacts_list(
        project_id: str = "",
        workflow_id: str = "",
        artifact_type: str = "",
        source_type: str = "",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        return [
            item.model_dump(mode="json")
            for item in _run(
                service.list_artifacts(
                    project_id=project_id,
                    workflow_id=workflow_id,
                    artifact_type=artifact_type,
                    source_type=source_type,
                    limit=limit,
                ),
            )
        ]

    def research_artifact_upsert(
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
    ) -> dict[str, Any]:
        artifact = _run(
            service.upsert_artifact(
                project_id=project_id,
                title=title,
                artifact_type=artifact_type,
                workflow_id=workflow_id,
                description=description,
                path=path,
                uri=uri,
                source_type=source_type,
                source_id=source_id,
                experiment_id=experiment_id,
                note_ids=note_ids,
                claim_ids=claim_ids,
                metadata=metadata,
            ),
        )
        return artifact.model_dump(mode="json")

    def research_claim_create(
        project_id: str,
        text: str,
        workflow_id: str = "",
        status: str = "draft",
        confidence: float | None = None,
        note_ids: list[str] | None = None,
        artifact_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        claim = _run(
            service.create_claim(
                project_id=project_id,
                text=text,
                workflow_id=workflow_id,
                status=status,
                confidence=confidence,
                note_ids=note_ids,
                artifact_ids=artifact_ids,
                metadata=metadata,
            ),
        )
        return claim.model_dump(mode="json")

    def research_claim_attach_evidence(
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
    ) -> dict[str, Any]:
        evidence = _run(
            service.attach_evidence(
                project_id=project_id,
                claim_ids=claim_ids,
                evidence_type=evidence_type,
                summary=summary,
                source_type=source_type,
                source_id=source_id,
                title=title,
                locator=locator,
                quote=quote,
                url=url,
                workflow_id=workflow_id,
                artifact_id=artifact_id,
                note_id=note_id,
                experiment_id=experiment_id,
                metadata=metadata,
            ),
        )
        return evidence.model_dump(mode="json")

    def research_claim_update(
        claim_id: str,
        text: str | None = None,
        status: str | None = None,
        confidence: float | None = None,
        note_ids: list[str] | None = None,
        artifact_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        claim = _run(
            service.update_claim(
                claim_id=claim_id,
                text=text,
                status=status,
                confidence=confidence,
                note_ids=note_ids,
                artifact_ids=artifact_ids,
                metadata=metadata,
            ),
        )
        return claim.model_dump(mode="json")

    def research_claim_graph(claim_id: str) -> dict[str, Any]:
        payload = _run(service.get_claim_graph(claim_id))
        return {
            key: value.model_dump(mode="json")
            if hasattr(value, "model_dump")
            else [
                item.model_dump(mode="json")
                if hasattr(item, "model_dump")
                else item
                for item in value
            ]
            if isinstance(value, list)
            else value
            for key, value in payload.items()
        }

    def research_experiment_log(
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
    ) -> dict[str, Any]:
        run = _run(
            service.log_experiment(
                project_id=project_id,
                name=name,
                workflow_id=workflow_id,
                status=status,
                parameters=parameters,
                input_data=input_data,
                metrics=metrics,
                notes=notes,
                output_files=output_files,
                baseline_of=baseline_of,
                ablation_of=ablation_of,
                comparison_group=comparison_group,
                related_run_ids=related_run_ids,
                claim_ids=claim_ids,
                metadata=metadata,
            ),
        )
        return run.model_dump(mode="json")

    def research_experiment_get(experiment_id: str) -> dict[str, Any]:
        run = _run(service.get_experiment(experiment_id))
        return run.model_dump(mode="json")

    def research_experiment_contract(experiment_id: str) -> dict[str, Any]:
        return _run(service.get_experiment_artifact_contract_validation(experiment_id))

    def research_experiment_remediation(experiment_id: str) -> dict[str, Any]:
        return _run(service.get_experiment_contract_remediation(experiment_id))

    def research_experiment_update(
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
    ) -> dict[str, Any]:
        run = _run(
            service.update_experiment(
                experiment_id=experiment_id,
                status=status,
                parameters=parameters,
                input_data=input_data,
                metrics=metrics,
                notes=notes,
                output_files=output_files,
                baseline_of=baseline_of,
                ablation_of=ablation_of,
                comparison_group=comparison_group,
                related_run_ids=related_run_ids,
                claim_ids=claim_ids,
                note_ids=note_ids,
                metadata=metadata,
            ),
        )
        return run.model_dump(mode="json")

    def research_experiment_update_execution(
        experiment_id: str,
        mode: str | None = None,
        command: list[str] | None = None,
        entrypoint: str = "",
        working_dir: str = "",
        notebook_path: str = "",
        result_bundle_file: str = "",
        result_bundle_schema: str = "",
        environment: dict[str, str] | None = None,
        external_run_id: str = "",
        requested_by: str = "",
        instructions: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        patch: dict[str, Any] = {}
        if mode is not None:
            patch["mode"] = mode
        if command is not None:
            patch["command"] = command
        if entrypoint:
            patch["entrypoint"] = entrypoint
        if working_dir:
            patch["working_dir"] = working_dir
        if notebook_path:
            patch["notebook_path"] = notebook_path
        if result_bundle_file:
            patch["result_bundle_file"] = result_bundle_file
        if result_bundle_schema:
            patch["result_bundle_schema"] = result_bundle_schema
        if environment:
            patch["environment"] = environment
        if external_run_id:
            patch["external_run_id"] = external_run_id
        if requested_by:
            patch["requested_by"] = requested_by
        if instructions:
            patch["instructions"] = instructions
        if metadata:
            patch["metadata"] = metadata
        payload = _run(
            service.configure_experiment_execution(
                experiment_id=experiment_id,
                patch=patch,
            ),
        )
        return {
            key: value.model_dump(mode="json")
            if hasattr(value, "model_dump")
            else value
            for key, value in payload.items()
        }

    def research_experiment_events(
        experiment_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        return [
            item.model_dump(mode="json")
            for item in _run(
                service.list_experiment_events(
                    experiment_id=experiment_id,
                    limit=limit,
                ),
            )
        ]

    def research_experiment_heartbeat(
        experiment_id: str,
        summary: str,
        status: str = "running",
        metrics: dict[str, Any] | None = None,
        output_files: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = _run(
            service.record_experiment_heartbeat(
                experiment_id=experiment_id,
                summary=summary,
                status=status,
                metrics=metrics,
                output_files=output_files,
                metadata=metadata,
            ),
        )
        return {
            key: value.model_dump(mode="json")
            if hasattr(value, "model_dump")
            else value
            for key, value in payload.items()
        }

    def research_experiment_result(
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
        payload = _run(
            service.record_experiment_result(
                experiment_id=experiment_id,
                summary=summary,
                status=status,
                metrics=metrics,
                output_files=output_files,
                notes=notes,
                note_ids=note_ids,
                claim_ids=claim_ids,
                metadata=metadata,
            ),
        )
        return {
            key: value.model_dump(mode="json")
            if hasattr(value, "model_dump")
            else value
            for key, value in payload.items()
        }

    def research_experiment_launch(experiment_id: str) -> dict[str, Any]:
        from ....research import ResearchWorkflowRuntime

        runtime = ResearchWorkflowRuntime(service=service)
        payload = _run(runtime.execute_experiment(experiment_id))
        return {
            key: value.model_dump(mode="json")
            if hasattr(value, "model_dump")
            else value
            for key, value in payload.items()
        }

    def research_experiment_compare(
        experiment_ids: list[str],
    ) -> dict[str, Any]:
        return _run(service.compare_experiments(experiment_ids))

    return {
        "research_projects_list": research_projects_list,
        "research_project_create": research_project_create,
        "research_project_update": research_project_update,
        "research_project_dashboard": research_project_dashboard,
        "research_project_blockers_dispatch": research_project_blockers_dispatch,
        "research_project_blockers_execute": research_project_blockers_execute,
        "research_project_blockers_resume": research_project_blockers_resume,
        "research_workflows_list": research_workflows_list,
        "research_workflow_create": research_workflow_create,
        "research_workflow_get": research_workflow_get,
        "research_workflow_remediation": research_workflow_remediation,
        "research_workflow_task_get": research_workflow_task_get,
        "research_workflow_task_execute": research_workflow_task_execute,
        "research_workflow_add_task": research_workflow_add_task,
        "research_workflow_update_task": research_workflow_update_task,
        "research_workflow_tick": research_workflow_tick,
        "research_workflow_update_execution_policy": research_workflow_update_execution_policy,
        "research_workflow_update_experiment_runner": research_workflow_update_experiment_runner,
        "research_note_create": research_note_create,
        "research_notes_search": research_notes_search,
        "research_artifacts_list": research_artifacts_list,
        "research_artifact_upsert": research_artifact_upsert,
        "research_claim_create": research_claim_create,
        "research_claim_attach_evidence": research_claim_attach_evidence,
        "research_claim_update": research_claim_update,
        "research_claim_graph": research_claim_graph,
        "research_experiment_log": research_experiment_log,
        "research_experiment_get": research_experiment_get,
        "research_experiment_contract": research_experiment_contract,
        "research_experiment_remediation": research_experiment_remediation,
        "research_experiment_update": research_experiment_update,
        "research_experiment_update_execution": research_experiment_update_execution,
        "research_experiment_events": research_experiment_events,
        "research_experiment_heartbeat": research_experiment_heartbeat,
        "research_experiment_result": research_experiment_result,
        "research_experiment_launch": research_experiment_launch,
        "research_experiment_compare": research_experiment_compare,
    }
