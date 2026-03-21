"""Runtime snapshot helpers for gateway health and observability surfaces."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from ...config import get_heartbeat_config
from ...constant import WORKING_DIR
from .schemas import GatewayRuntimeSnapshot
from .runtime import get_gateway_runtime


def empty_cron_stats() -> dict[str, Any]:
    return {
        "started": False,
        "scheduler_active": False,
        "registered_jobs_total": 0,
        "registered_jobs_enabled": 0,
        "persistent_jobs_total": 0,
        "persistent_jobs_enabled": 0,
        "states_tracked": 0,
        "running_jobs": 0,
        "errored_jobs": 0,
    }


def empty_channel_stats() -> dict[str, Any]:
    return {
        "registered_channels": 0,
        "queued_messages": 0,
        "pending_messages": 0,
        "in_progress_keys": 0,
        "consumer_workers": {"total": 0, "alive": 0},
        "channels": [],
    }


def empty_automation_stats() -> dict[str, Any]:
    return {
        "total": 0,
        "queued": 0,
        "running": 0,
        "succeeded": 0,
        "failed": 0,
    }


def empty_usage_stats() -> dict[str, Any]:
    return {
        "requests": 0,
        "succeeded": 0,
        "failed": 0,
        "fallbacks": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "providers": [],
        "agents": [],
    }


def _heartbeat_config_defaults(
    *,
    enabled: bool,
    healthy: bool,
    last_heartbeat: float | None = None,
    age_seconds: int | None = None,
) -> dict[str, Any]:
    hb = get_heartbeat_config()
    return {
        "enabled": enabled,
        "configured": enabled,
        "last_heartbeat": last_heartbeat,
        "age_seconds": age_seconds,
        "healthy": healthy,
        "every": str(getattr(hb, "every", "30m") or "30m"),
        "target": str(getattr(hb, "target", "last") or "last"),
    }


def runtime_component_flags(
    snapshot: GatewayRuntimeSnapshot,
) -> dict[str, bool]:
    """Return simple component-presence flags for gateway health surfaces."""
    return {
        "runner": snapshot.runner is not None,
        "chat_manager": snapshot.chat_manager is not None,
        "channel_manager": snapshot.channel_manager is not None,
        "mcp_manager": snapshot.mcp_manager is not None,
        "mcp_watcher": snapshot.mcp_watcher is not None,
        "cron_manager": snapshot.cron_manager is not None,
        "config_watcher": snapshot.config_watcher is not None,
        "automation_store": snapshot.automation_store is not None,
        "research_service": snapshot.research_service is not None,
        "research_runtime": snapshot.research_runtime is not None,
    }


async def get_control_cron_jobs(cron: Any) -> list[Any]:
    """Return cron jobs for control page (prefer registered/simple jobs)."""
    if cron is None:
        return []
    if hasattr(cron, "list_jobs"):
        try:
            return await cron.list_jobs()
        except Exception:
            pass
    if hasattr(cron, "list_registered_jobs"):
        try:
            return cron.list_registered_jobs()
        except Exception:
            pass
    return []


async def get_cron_runtime_stats(cron: Any) -> dict[str, Any]:
    """Best-effort cron runtime stats for observability."""
    if cron is None:
        return empty_cron_stats()
    if hasattr(cron, "get_runtime_stats"):
        try:
            stats = await cron.get_runtime_stats()
            if isinstance(stats, dict):
                return stats
        except Exception:
            pass
    jobs = await get_control_cron_jobs(cron)
    total = len(jobs)
    enabled = sum(
        1 for job in jobs if isinstance(job, dict) and job.get("enabled", True)
    )
    return {
        "started": True,
        "scheduler_active": False,
        "registered_jobs_total": total,
        "registered_jobs_enabled": enabled,
        "persistent_jobs_total": total,
        "persistent_jobs_enabled": enabled,
        "states_tracked": 0,
        "running_jobs": 0,
        "errored_jobs": 0,
    }


def get_runner_runtime_stats(runner: Any) -> dict[str, Any]:
    """Best-effort runner/session observability snapshot."""
    if runner is None:
        return {
            "running": False,
            "agent_id": "",
            "agent_name": "",
            "tool_count": 0,
            "default_agent_id": "",
            "session_count": 0,
            "model_provider": "",
            "model_name": "",
            "agents": [],
            "usage": empty_usage_stats(),
        }
    session_count = 0
    try:
        if hasattr(runner, "list_sessions"):
            session_count = len(runner.list_sessions())
        elif hasattr(runner, "session_manager"):
            session_count = len(runner.session_manager.list_sessions())
    except Exception:
        session_count = 0

    model_cfg = {}
    runner_for_status = getattr(runner, "runner", None)
    snapshot: dict[str, Any] = {}
    if hasattr(runner, "get_status_snapshot"):
        try:
            snapshot = runner.get_status_snapshot()
        except Exception:
            snapshot = {}
    if hasattr(runner, "get_status_manager"):
        try:
            _, manager = runner.get_status_manager()
            if manager is not None:
                runner_for_status = getattr(
                    manager,
                    "runner",
                    runner_for_status,
                )
        except Exception:
            runner_for_status = getattr(runner, "runner", None)
    try:
        if runner_for_status is not None:
            model_cfg = (
                getattr(runner_for_status, "_last_model_config", {}) or {}
            )
    except Exception:
        model_cfg = {}

    usage: dict[str, Any] = empty_usage_stats()
    try:
        if hasattr(runner, "list_usage_stats"):
            stats = runner.list_usage_stats()
            if isinstance(stats, dict):
                usage = stats
        elif hasattr(runner, "get_usage_stats"):
            stats = runner.get_usage_stats()
            if isinstance(stats, dict):
                usage = stats
    except Exception:
        pass

    return {
        "running": bool(
            snapshot.get("running", getattr(runner, "is_running", False)),
        ),
        "agent_id": str(snapshot.get("agent_id", "") or ""),
        "agent_name": str(snapshot.get("agent_name", "") or ""),
        "tool_count": int(snapshot.get("tool_count", 0) or 0),
        "default_agent_id": str(snapshot.get("default_agent_id", "") or ""),
        "session_count": session_count,
        "model_provider": str(model_cfg.get("provider", "") or ""),
        "model_name": str(model_cfg.get("model_name", "") or ""),
        "agents": (
            snapshot.get("agents")
            if isinstance(snapshot.get("agents"), list)
            else runner.list_agents()
            if hasattr(runner, "list_agents")
            else []
        ),
        "usage": usage,
    }


def get_skills_runtime_stats() -> dict[str, Any]:
    try:
        from researchclaw.agents.skills_manager import SkillsManager

        active_skills = SkillsManager().list_active_skills()
    except Exception:
        active_skills = []
    return {
        "active_count": len(active_skills),
        "active_skills": active_skills,
    }


def get_heartbeat_runtime_stats() -> dict[str, Any]:
    enabled = bool(getattr(get_heartbeat_config(), "enabled", False))
    hb_file = Path(WORKING_DIR) / "heartbeat.json"
    if not hb_file.exists():
        return _heartbeat_config_defaults(enabled=enabled, healthy=False)
    try:
        data = json.loads(hb_file.read_text(encoding="utf-8"))
    except Exception:
        return _heartbeat_config_defaults(enabled=enabled, healthy=False)

    ts = float(data.get("timestamp", 0))
    age = int(time.time() - ts) if ts else None
    return _heartbeat_config_defaults(
        enabled=enabled,
        healthy=enabled and age is not None and age <= 2 * 3600,
        last_heartbeat=ts,
        age_seconds=age,
    )


def get_channel_runtime_stats(channels: Any) -> dict[str, Any]:
    """Best-effort channel runtime stats."""
    if channels is None:
        return empty_channel_stats()
    if hasattr(channels, "get_runtime_stats"):
        try:
            stats = channels.get_runtime_stats()
            if isinstance(stats, dict):
                return stats
        except Exception:
            pass
    listed = []
    try:
        listed = channels.list_channels()
    except Exception:
        listed = []
    stats = empty_channel_stats()
    stats["registered_channels"] = len(listed)
    stats["channels"] = listed
    return stats


async def get_automation_runtime_stats(store: Any) -> dict[str, Any]:
    if store is None or not hasattr(store, "stats"):
        return empty_automation_stats()
    try:
        stats = await store.stats()
        if isinstance(stats, dict):
            return stats
    except Exception:
        pass
    return empty_automation_stats()


async def get_research_runtime_stats(service: Any, runtime: Any) -> dict[str, Any]:
    if runtime is not None and hasattr(runtime, "get_runtime_stats"):
        try:
            stats = await runtime.get_runtime_stats()
            if isinstance(stats, dict):
                return stats
        except Exception:
            pass
    if service is not None and hasattr(service, "get_runtime_stats"):
        try:
            stats = await service.get_runtime_stats()
            if isinstance(stats, dict):
                return stats
        except Exception:
            pass
    return {
        "projects": 0,
        "workflows": 0,
        "active_workflows": 0,
        "notes": 0,
        "claims": 0,
        "evidences": 0,
        "experiments": 0,
        "artifacts": 0,
        "due_reminders": 0,
        "state_path": "",
    }


async def build_control_status_payload(app: FastAPI) -> dict[str, Any]:
    """Build the control-plane status payload from the gateway runtime."""
    runtime = get_gateway_runtime(app)
    snapshot = runtime.snapshot()
    uptime_seconds = (
        int(time.time() - snapshot.started_at) if snapshot.started_at else 0
    )
    cron_jobs = await get_control_cron_jobs(snapshot.cron_manager)
    cron_stats = await get_cron_runtime_stats(snapshot.cron_manager)
    channel_stats = get_channel_runtime_stats(snapshot.channel_manager)
    runner_stats = get_runner_runtime_stats(snapshot.runner)
    automation_stats = await get_automation_runtime_stats(
        snapshot.automation_store,
    )
    research_stats = await get_research_runtime_stats(
        snapshot.research_service,
        snapshot.research_runtime,
    )
    skills_stats = get_skills_runtime_stats()
    heartbeat_stats = get_heartbeat_runtime_stats()
    mcp_clients = (
        snapshot.mcp_manager.list_clients() if snapshot.mcp_manager else []
    )
    return {
        "service": "ResearchClaw",
        "mode": "24x7-standby",
        "uptime_seconds": uptime_seconds,
        "runner_running": runner_stats["running"],
        "cron_jobs": cron_jobs,
        "channels": channel_stats.get("channels", []),
        "mcp_clients": mcp_clients,
        "runtime": {
            "runner": runner_stats,
            "channels": channel_stats,
            "cron": cron_stats,
            "automation": automation_stats,
            "research": research_stats,
            "skills": skills_stats,
            "heartbeat": heartbeat_stats,
            "components": runtime_component_flags(snapshot),
        },
    }
