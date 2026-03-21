"""Automation trigger API routes."""

from __future__ import annotations

import asyncio
import os
import re
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ...config import load_config
from ..automation import AutomationRunStore
from ..gateway.auth import extract_header_token
from ..gateway.dispatch import dedupe_dispatch_mappings, normalize_channel_name
from ..gateway.ingress import default_session_id

router = APIRouter()

_TEMPLATE_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")


class TriggerDispatch(BaseModel):
    """A channel dispatch target for automation output."""

    channel: str
    user_id: str = "main"
    session_id: str = "main"


class AgentTriggerRequest(BaseModel):
    """Payload for triggering an automated agent run."""

    message: str = Field(..., min_length=1)
    agent_id: Optional[str] = None
    project_id: Optional[str] = None
    workflow_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: str = "automation"
    deliver: bool = True
    dispatches: List[TriggerDispatch] = Field(default_factory=list)
    fanout_channels: List[str] = Field(default_factory=list)
    run_async: bool = True


class WakeTriggerRequest(BaseModel):
    """Payload for wake triggers."""

    text: str = Field(..., min_length=1)
    mode: str = "now"  # now | next-heartbeat
    agent_id: Optional[str] = None
    project_id: Optional[str] = None
    workflow_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: str = "automation"
    deliver: bool = False
    dispatches: List[TriggerDispatch] = Field(default_factory=list)
    fanout_channels: List[str] = Field(default_factory=list)
    run_async: bool = True


def _get_or_create_store(req: Request) -> AutomationRunStore:
    store = getattr(req.app.state, "automation_store", None)
    if store is None:
        store = AutomationRunStore()
        req.app.state.automation_store = store
    return store


def _resolve_token_from_config() -> str:
    cfg = load_config()
    if not isinstance(cfg, dict):
        return ""
    automation_cfg = cfg.get("automation")
    if isinstance(automation_cfg, dict):
        token = str(automation_cfg.get("token", "") or "").strip()
        if token:
            return token
    hooks_cfg = cfg.get("hooks")
    if isinstance(hooks_cfg, dict):
        token = str(hooks_cfg.get("token", "") or "").strip()
        if token:
            return token
    return ""


def _configured_automation_token() -> str:
    env_token = str(
        os.environ.get("RESEARCHCLAW_AUTOMATION_TOKEN", "") or "",
    ).strip()
    if env_token:
        return env_token
    return _resolve_token_from_config()


def _extract_request_token(req: Request) -> str:
    return extract_header_token(
        req.headers,
        "x-researchclaw-token",
        "x-researchclaw-automation-token",
    )


def _verify_trigger_auth(req: Request) -> None:
    configured = _configured_automation_token()
    if not configured:
        raise HTTPException(
            status_code=503,
            detail=(
                "Automation token is not configured. Set "
                "RESEARCHCLAW_AUTOMATION_TOKEN or config.automation.token."
            ),
        )
    got = _extract_request_token(req)
    if got != configured:
        raise HTTPException(status_code=401, detail="Invalid automation token")


def _dedupe_dispatches(
    dispatches: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    return dedupe_dispatch_mappings(dispatches)


def _expand_dispatches(
    *,
    payload: AgentTriggerRequest,
    req: Request,
    default_session_id: str,
) -> List[Dict[str, str]]:
    dispatches = [
        {
            "channel": d.channel,
            "user_id": d.user_id,
            "session_id": d.session_id,
        }
        for d in payload.dispatches
    ]

    if payload.deliver and payload.fanout_channels:
        channels = [normalize_channel_name(v) for v in payload.fanout_channels]
        channels = [v for v in channels if v]
        if "*" in channels:
            mgr = getattr(req.app.state, "channel_manager", None)
            available = []
            if mgr is not None and hasattr(mgr, "list_channels"):
                available = [
                    str(item.get("name", "")).strip().lower()
                    for item in mgr.list_channels()
                    if isinstance(item, dict)
                ]
            channels = sorted({v for v in available if v})

        for channel in channels:
            dispatches.append(
                {
                    "channel": channel,
                    "user_id": payload.user_id or "main",
                    "session_id": default_session_id,
                },
            )

    if payload.deliver and not dispatches:
        last = {}
        cfg = load_config()
        if isinstance(cfg, dict):
            last = cfg.get("last_dispatch") or {}
        channel = normalize_channel_name(str(last.get("channel", "")))
        user_id = str(last.get("user_id", "") or "").strip()
        session_id = str(last.get("session_id", "") or "").strip()
        dispatches.append(
            {
                "channel": channel or "console",
                "user_id": user_id or "main",
                "session_id": session_id or default_session_id,
            },
        )

    return _dedupe_dispatches(dispatches)


def _value_by_path(payload: Any, path: str) -> Any:
    current = payload
    for part in [p for p in path.split(".") if p]:
        if isinstance(current, dict):
            current = current.get(part)
            continue
        if isinstance(current, list):
            try:
                idx = int(part)
            except ValueError:
                return None
            if idx < 0 or idx >= len(current):
                return None
            current = current[idx]
            continue
        return None
    return current


def _render_template(template: str, payload: Any) -> str:
    def _replace(match: re.Match[str]) -> str:
        expr = match.group(1).strip()
        value = _value_by_path(payload, expr)
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return str(value)
        return str(value)

    return _TEMPLATE_RE.sub(_replace, template)


def _extract_message_from_mapping(mapping: dict[str, Any], body: Any) -> str:
    message_template = str(mapping.get("message_template", "") or "").strip()
    if message_template:
        return _render_template(message_template, body).strip()

    message_field = str(mapping.get("message_field", "") or "").strip()
    if message_field:
        value = _value_by_path(body, message_field)
        if value is not None:
            return str(value).strip()

    fallback = body.get("message") if isinstance(body, dict) else None
    if fallback:
        return str(fallback).strip()
    return ""


def _resolve_hook_mapping(hook_name: str) -> dict[str, Any] | None:
    cfg = load_config()
    if not isinstance(cfg, dict):
        return None

    options: list[dict[str, Any]] = []
    automation_cfg = cfg.get("automation")
    if isinstance(automation_cfg, dict):
        mappings = automation_cfg.get("mappings")
        if isinstance(mappings, list):
            options.extend([m for m in mappings if isinstance(m, dict)])
    hooks_cfg = cfg.get("hooks")
    if isinstance(hooks_cfg, dict):
        mappings = hooks_cfg.get("mappings")
        if isinstance(mappings, list):
            options.extend([m for m in mappings if isinstance(m, dict)])

    for item in options:
        name = str(item.get("name") or item.get("path") or "").strip().lower()
        if name == hook_name.strip().lower():
            return item
    return None


async def _run_agent_trigger(
    *,
    req: Request,
    run_id: str,
    payload: AgentTriggerRequest,
    session_id: str,
    dispatches: List[Dict[str, str]],
) -> Dict[str, Any]:
    store = _get_or_create_store(req)
    await store.mark_running(run_id)

    runner = getattr(req.app.state, "runner", None)
    if runner is None:
        await store.mark_failed(
            run_id,
            error="Agent runner is not initialized",
        )
        raise RuntimeError("Agent runner is not initialized")

    if payload.agent_id:
        response_text = await runner.chat(
            payload.message,
            session_id=session_id,
            agent_id=payload.agent_id,
        )
    else:
        response_text = await runner.chat(
            payload.message,
            session_id=session_id,
        )

    delivery_results: List[Dict[str, Any]] = []
    if payload.deliver:
        channel_manager = getattr(req.app.state, "channel_manager", None)
        if channel_manager is None:
            delivery_results.append(
                {
                    "ok": False,
                    "error": "Channel manager is not initialized",
                },
            )
        else:
            for target in dispatches:
                result = dict(target)
                try:
                    await channel_manager.send_text(
                        channel=target["channel"],
                        user_id=target["user_id"],
                        session_id=target["session_id"],
                        text=response_text,
                        meta={
                            "source": "automation",
                            "agent_id": payload.agent_id or "main",
                        },
                    )
                    result["ok"] = True
                except (
                    Exception
                ) as e:  # channel errors should not abort the run
                    result["ok"] = False
                    result["error"] = str(e)
                delivery_results.append(result)

    research_runtime = getattr(req.app.state, "research_runtime", None)
    if (
        research_runtime is not None
        and payload.workflow_id
        and hasattr(research_runtime, "note_automation_run")
    ):
        try:
            await research_runtime.note_automation_run(
                workflow_id=payload.workflow_id,
                run_id=run_id,
                summary=response_text[:400],
                session_id=session_id,
                dispatches=dispatches,
            )
        except Exception:
            pass

    return (
        await store.mark_success(
            run_id,
            response=response_text,
            delivery_results=delivery_results,
        )
        or {}
    )


async def _queue_or_run_trigger(
    *,
    req: Request,
    payload: AgentTriggerRequest,
    source: str,
    session_prefix: str = "automation",
) -> Dict[str, Any]:
    store = _get_or_create_store(req)
    run_id = str(uuid.uuid4())
    session_id = default_session_id(
        prefix=session_prefix,
        provided=payload.session_id or f"{session_prefix}:{run_id}",
    )
    dispatches = _expand_dispatches(
        payload=payload,
        req=req,
        default_session_id=session_id,
    )

    await store.create(
        run_id=run_id,
        message=payload.message,
        session_id=session_id,
        deliver=payload.deliver,
        dispatches=dispatches,
        source=source,
        agent_id=str(payload.agent_id or "").strip(),
    )

    async def _task() -> None:
        try:
            await _run_agent_trigger(
                req=req,
                run_id=run_id,
                payload=payload,
                session_id=session_id,
                dispatches=dispatches,
            )
        except Exception as e:
            await store.mark_failed(run_id, error=str(e))

    if payload.run_async:
        asyncio.create_task(_task())
        return {
            "id": run_id,
            "status": "queued",
            "session_id": session_id,
            "dispatches": dispatches,
            "agent_id": payload.agent_id or "main",
            "source": source,
        }

    try:
        run = await _run_agent_trigger(
            req=req,
            run_id=run_id,
            payload=payload,
            session_id=session_id,
            dispatches=dispatches,
        )
        run["source"] = source
        return run
    except Exception as e:
        await store.mark_failed(run_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


def _wake_to_agent_trigger(payload: WakeTriggerRequest) -> AgentTriggerRequest:
    mode = str(payload.mode or "now").strip().lower()
    text = payload.text.strip()
    wake_message = (
        f"[Wake trigger:{mode}] {text}"
        if mode == "now"
        else f"[Wake trigger:deferred] {text}"
    )
    return AgentTriggerRequest(
        message=wake_message,
        agent_id=payload.agent_id,
        project_id=payload.project_id,
        workflow_id=payload.workflow_id,
        session_id=payload.session_id,
        user_id=payload.user_id,
        deliver=payload.deliver,
        dispatches=payload.dispatches,
        fanout_channels=payload.fanout_channels,
        run_async=payload.run_async,
    )


@router.post("/triggers/agent")
async def trigger_agent(payload: AgentTriggerRequest, req: Request):
    """Trigger an agent run from external automation systems."""
    _verify_trigger_auth(req)
    return await _queue_or_run_trigger(
        req=req,
        payload=payload,
        source="agent",
    )


@router.post("/triggers/wake")
async def trigger_wake(payload: WakeTriggerRequest, req: Request):
    """Trigger a wake event (immediate or deferred)."""
    _verify_trigger_auth(req)
    mode = str(payload.mode or "now").strip().lower()
    if mode not in {"now", "next-heartbeat"}:
        raise HTTPException(
            status_code=400,
            detail="mode must be one of: now, next-heartbeat",
        )

    if mode == "next-heartbeat":
        store = _get_or_create_store(req)
        run_id = str(uuid.uuid4())
        session_id = default_session_id(
            prefix="wake",
            provided=payload.session_id or f"wake:{run_id}",
        )
        await store.create(
            run_id=run_id,
            message=payload.text,
            session_id=session_id,
            deliver=False,
            dispatches=[],
            source="wake-deferred",
            agent_id=str(payload.agent_id or "").strip(),
        )
        await store.mark_success(
            run_id,
            response="Wake accepted and deferred to next heartbeat window.",
            delivery_results=[],
        )
        return {
            "id": run_id,
            "status": "succeeded",
            "session_id": session_id,
            "source": "wake-deferred",
            "agent_id": payload.agent_id or "main",
        }

    agent_payload = _wake_to_agent_trigger(payload)
    return await _queue_or_run_trigger(
        req=req,
        payload=agent_payload,
        source="wake-now",
        session_prefix="wake",
    )


@router.post("/hooks/{hook_name}")
async def trigger_hook(hook_name: str, req: Request):
    """Mapped automation ingress endpoint for external event hooks."""
    _verify_trigger_auth(req)
    mapping = _resolve_hook_mapping(hook_name)
    if mapping is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown hook: {hook_name}",
        )

    body = await req.json()
    action = str(mapping.get("action", "agent") or "agent").strip().lower()
    run_async = bool(mapping.get("run_async", True))
    deliver = bool(mapping.get("deliver", True))
    agent_id = (
        str(mapping.get("agent_id") or mapping.get("agentId") or "").strip()
        or None
    )
    session_id = (
        str(
            mapping.get("session_id") or mapping.get("sessionId") or "",
        ).strip()
        or None
    )
    fanout = mapping.get("fanout_channels")
    if not isinstance(fanout, list):
        fanout = []
    dispatches = mapping.get("dispatches")
    dispatch_models: list[TriggerDispatch] = []
    if isinstance(dispatches, list):
        for item in dispatches:
            if not isinstance(item, dict):
                continue
            channel = str(item.get("channel", "")).strip()
            if not channel:
                continue
            dispatch_models.append(
                TriggerDispatch(
                    channel=channel,
                    user_id=str(item.get("user_id", "main") or "main"),
                    session_id=str(item.get("session_id", "main") or "main"),
                ),
            )

    message = _extract_message_from_mapping(mapping, body)
    if not message:
        raise HTTPException(
            status_code=400,
            detail="Hook mapping produced empty message. Set message_template or message_field.",
        )

    if action == "wake":
        wake_payload = WakeTriggerRequest(
            text=message,
            mode=str(mapping.get("mode") or mapping.get("wake_mode") or "now"),
            agent_id=agent_id,
            session_id=session_id,
            user_id=str(mapping.get("user_id") or "automation"),
            deliver=deliver,
            dispatches=dispatch_models,
            fanout_channels=[str(v) for v in fanout],
            run_async=run_async,
        )
        return await trigger_wake(wake_payload, req)

    payload = AgentTriggerRequest(
        message=message,
        agent_id=agent_id,
        session_id=session_id,
        user_id=str(mapping.get("user_id") or "automation"),
        deliver=deliver,
        dispatches=dispatch_models,
        fanout_channels=[str(v) for v in fanout],
        run_async=run_async,
    )
    return await _queue_or_run_trigger(
        req=req,
        payload=payload,
        source=f"hook:{hook_name}",
    )


@router.get("/triggers/runs")
async def list_trigger_runs(req: Request, limit: int = 50):
    """List recent automation trigger runs."""
    store = _get_or_create_store(req)
    return {"runs": await store.list(limit=limit)}


@router.get("/triggers/runs/{run_id}")
async def get_trigger_run(req: Request, run_id: str):
    """Get one automation trigger run by id."""
    store = _get_or_create_store(req)
    run = await store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run
