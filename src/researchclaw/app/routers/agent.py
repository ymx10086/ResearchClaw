"""Agent API routes – chat with ScholarAgent."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from researchclaw.constant import (
    DEFAULT_MAX_INPUT_TOKENS,
    DEFAULT_MAX_ITERS,
    WORKING_DIR,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    """Chat message request body."""

    message: str
    session_id: str | None = None
    agent_id: str | None = None
    stream: bool = False


class ChatResponse(BaseModel):
    """Chat message response."""

    response: str
    session_id: str


class AgentsRunningConfig(BaseModel):
    """Runtime agent limits shown in console settings."""

    max_iters: int = DEFAULT_MAX_ITERS
    max_input_length: int = DEFAULT_MAX_INPUT_TOKENS


def _load_running_config() -> AgentsRunningConfig:
    config_path = Path(WORKING_DIR) / "config.json"
    if not config_path.exists():
        return AgentsRunningConfig()

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return AgentsRunningConfig()

    return AgentsRunningConfig(
        max_iters=int(data.get("max_iters", DEFAULT_MAX_ITERS)),
        max_input_length=int(
            data.get("max_input_length", DEFAULT_MAX_INPUT_TOKENS),
        ),
    )


def _save_running_config(config: AgentsRunningConfig) -> AgentsRunningConfig:
    config_path = Path(WORKING_DIR) / "config.json"
    payload: dict[str, Any] = {}
    if config_path.exists():
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}

    payload.update(config.model_dump())
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return config


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    """Send a message to ScholarAgent and get a response."""
    runner = getattr(req.app.state, "runner", None)
    if not runner:
        return ChatResponse(
            response="Agent is not running. Please check the server logs.",
            session_id=request.session_id or str(uuid.uuid4()),
        )

    session_id = request.session_id or str(uuid.uuid4())

    try:
        response = await runner.chat(
            message=request.message,
            session_id=session_id,
            agent_id=request.agent_id,
        )
        return ChatResponse(response=response, session_id=session_id)
    except Exception as e:
        logger.exception("Chat error")
        return ChatResponse(
            response=f"Error: {e}",
            session_id=session_id,
        )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, req: Request):
    """Stream a response from ScholarAgent via SSE.

    Sends events of these types:
    - ``thinking`` — reasoning/thinking tokens (from thinking models)
    - ``content`` — regular content tokens
    - ``tool_call`` — the agent is calling a tool
    - ``tool_result`` — tool execution result
    - ``done`` — final complete response
    - ``error`` — an error occurred
    """
    runner = getattr(req.app.state, "runner", None)
    session_id = request.session_id or str(uuid.uuid4())

    async def generate():
        if not runner:
            yield f"data: {json.dumps({'type': 'error', 'content': 'Agent not running'})}\n\n"
            return

        try:
            async for event in runner.chat_stream(
                message=request.message,
                session_id=session_id,
                agent_id=request.agent_id,
            ):
                event["session_id"] = session_id
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e), 'session_id': session_id})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/tools")
async def list_tools(req: Request):
    """List available agent tools."""
    runner = getattr(req.app.state, "runner", None)
    if not runner or not runner.agent:
        return {"tools": []}
    return {"tools": runner.agent.tool_names}


@router.get("/status")
async def agent_status(req: Request):
    """Get agent status."""
    runner = getattr(req.app.state, "runner", None)
    agents = []
    if runner and hasattr(runner, "list_agents"):
        try:
            agents = runner.list_agents()
        except Exception:
            agents = []
    return {
        "running": runner is not None and runner.is_running,
        "agent_name": "Scholar",
        "tool_count": len(runner.agent.tool_names)
        if runner and runner.agent
        else 0,
        "agents": agents,
    }


@router.get("/running-config", response_model=AgentsRunningConfig)
async def get_running_config():
    """Get persisted runtime configuration for agent limits."""
    return _load_running_config()


@router.put("/running-config", response_model=AgentsRunningConfig)
async def update_running_config(config: AgentsRunningConfig):
    """Persist runtime configuration for agent limits."""
    return _save_running_config(config)
