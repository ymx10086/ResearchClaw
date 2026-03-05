"""MCP client management routes."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()
logger = logging.getLogger(__name__)


class MCPClient(BaseModel):
    key: str
    name: str
    transport: str = "stdio"
    enabled: bool = True
    description: str = ""
    command: str = ""
    args: List[str] = Field(default_factory=list)
    url: str = ""
    env: Dict[str, str] = Field(default_factory=dict)


class MCPClientCreate(BaseModel):
    name: str
    transport: str = "stdio"
    enabled: bool = True
    description: str = ""
    command: str = ""
    args: List[str] = Field(default_factory=list)
    url: str = ""
    env: Dict[str, str] = Field(default_factory=dict)


async def _reload_runtime(req: Request, mcp: Any) -> None:
    """Apply current in-memory MCP config to runtime clients immediately."""
    try:
        await mcp.reload()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"MCP runtime reload failed: {exc}",
        ) from exc

    runner = getattr(req.app.state, "runner", None)
    if runner is None:
        return
    try:
        await runner.refresh_mcp_clients(force=True)
    except Exception:
        logger.debug("Runner MCP refresh failed", exc_info=True)


@router.get("")
async def list_clients(req: Request) -> List[dict[str, Any]]:
    mcp = getattr(req.app.state, "mcp_manager", None)
    if not mcp:
        return []
    return mcp.list_clients()


@router.post("", status_code=201)
async def create_client(
    client_key: str,
    body: MCPClientCreate,
    req: Request,
) -> dict[str, Any]:
    mcp = getattr(req.app.state, "mcp_manager", None)
    if not mcp:
        raise HTTPException(
            status_code=500,
            detail="MCP manager not available",
        )

    existing = {item.get("key") for item in mcp.list_clients()}
    if client_key in existing:
        raise HTTPException(
            status_code=400,
            detail=f"MCP client '{client_key}' already exists",
        )

    mcp.register(client_key, body.model_dump())
    await mcp.save()
    await _reload_runtime(req, mcp)
    return {"created": True, "key": client_key}


@router.put("/{client_key}")
async def update_client(
    client_key: str,
    body: MCPClientCreate,
    req: Request,
) -> dict[str, Any]:
    mcp = getattr(req.app.state, "mcp_manager", None)
    if not mcp:
        raise HTTPException(
            status_code=500,
            detail="MCP manager not available",
        )

    mcp.register(client_key, body.model_dump())
    await mcp.save()
    await _reload_runtime(req, mcp)
    return {"updated": True, "key": client_key}


@router.patch("/{client_key}/toggle")
async def toggle_client(client_key: str, req: Request) -> dict[str, Any]:
    mcp = getattr(req.app.state, "mcp_manager", None)
    if not mcp:
        raise HTTPException(
            status_code=500,
            detail="MCP manager not available",
        )

    clients = {item.get("key"): item for item in mcp.list_clients()}
    item = clients.get(client_key)
    if not item:
        raise HTTPException(
            status_code=404,
            detail=f"MCP client '{client_key}' not found",
        )

    item["enabled"] = not bool(item.get("enabled", True))
    mcp.register(client_key, item)
    await mcp.save()
    await _reload_runtime(req, mcp)
    return {"key": client_key, "enabled": item["enabled"]}


@router.delete("/{client_key}")
async def delete_client(client_key: str, req: Request) -> dict[str, Any]:
    mcp = getattr(req.app.state, "mcp_manager", None)
    if not mcp:
        raise HTTPException(
            status_code=500,
            detail="MCP manager not available",
        )

    mcp.remove(client_key)
    await mcp.save()
    await _reload_runtime(req, mcp)
    return {"deleted": True, "key": client_key}
