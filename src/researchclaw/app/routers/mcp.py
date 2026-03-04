"""MCP client management routes."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()


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
    return {"deleted": True, "key": client_key}
