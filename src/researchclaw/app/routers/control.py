"""Control-plane routes for 24x7 standby status and runtime management."""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from researchclaw.constant import WORKING_DIR

router = APIRouter()


@router.get("/status")
async def runtime_status(req: Request):
    started_at = getattr(req.app.state, "started_at", None)
    uptime_seconds = int(time.time() - started_at) if started_at else 0

    runner = getattr(req.app.state, "runner", None)
    cron = getattr(req.app.state, "cron", None)
    channels = getattr(req.app.state, "channel_manager", None)
    mcp = getattr(req.app.state, "mcp_manager", None)

    return {
        "service": "ResearchClaw",
        "mode": "24x7-standby",
        "uptime_seconds": uptime_seconds,
        "runner_running": bool(runner and runner.is_running),
        "cron_jobs": cron.list_jobs() if cron else [],
        "channels": channels.list_channels() if channels else [],
        "mcp_clients": mcp.list_clients() if mcp else [],
    }


@router.get("/cron-jobs")
async def list_cron_jobs(req: Request):
    cron = getattr(req.app.state, "cron", None)
    if not cron:
        return []
    return cron.list_jobs()


@router.get("/channels")
async def list_channels(req: Request):
    channels = getattr(req.app.state, "channel_manager", None)
    if not channels:
        return []
    return channels.list_channels()


@router.get("/sessions")
async def list_sessions(req: Request):
    runner = getattr(req.app.state, "runner", None)
    if not runner or not hasattr(runner, "session_manager"):
        return []
    return runner.session_manager.list_sessions()


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, req: Request):
    runner = getattr(req.app.state, "runner", None)
    if not runner or not hasattr(runner, "session_manager"):
        raise HTTPException(
            status_code=404,
            detail="Session manager not available",
        )

    session = runner.session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found",
        )
    return session.to_dict()


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, req: Request):
    runner = getattr(req.app.state, "runner", None)
    if not runner or not hasattr(runner, "session_manager"):
        raise HTTPException(
            status_code=404,
            detail="Session manager not available",
        )

    session = runner.session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found",
        )

    runner.session_manager.delete_session(session_id)
    return {"deleted": True, "session_id": session_id}


@router.post("/cron-jobs/{job_name}/enable")
async def enable_cron_job(job_name: str, req: Request):
    cron = getattr(req.app.state, "cron", None)
    if not cron:
        raise HTTPException(
            status_code=500,
            detail="Cron manager not available",
        )
    cron.enable_job(job_name)
    return {"enabled": True, "job": job_name}


@router.post("/cron-jobs/{job_name}/disable")
async def disable_cron_job(job_name: str, req: Request):
    cron = getattr(req.app.state, "cron", None)
    if not cron:
        raise HTTPException(
            status_code=500,
            detail="Cron manager not available",
        )
    cron.disable_job(job_name)
    return {"enabled": False, "job": job_name}


@router.get("/heartbeat")
async def heartbeat_status():
    hb_file = Path(WORKING_DIR) / "heartbeat.json"
    if not hb_file.exists():
        return {"enabled": True, "last_heartbeat": None, "healthy": False}

    try:
        data = json.loads(hb_file.read_text(encoding="utf-8"))
    except Exception:
        return {"enabled": True, "last_heartbeat": None, "healthy": False}

    ts = float(data.get("timestamp", 0))
    age = int(time.time() - ts) if ts else None
    return {
        "enabled": True,
        "last_heartbeat": ts,
        "age_seconds": age,
        "healthy": age is not None and age <= 2 * 3600,
    }
