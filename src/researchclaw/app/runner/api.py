"""Chat management API — CRUD for chat sessions.

Provides REST endpoints for listing, creating, updating, and deleting
chat sessions. Chat history is retrieved from session files.
"""
from __future__ import annotations

import json
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .chat_manager import ChatManager
from .models import ChatSpec, ChatHistory, ChatMessage

router = APIRouter(prefix="/chats", tags=["chats"])


def get_chat_manager(request: Request) -> ChatManager:
    """Get the chat manager from app state."""
    mgr = getattr(request.app.state, "chat_manager", None)
    if mgr is None:
        raise HTTPException(
            status_code=503,
            detail="Chat manager not initialized",
        )
    return mgr


@router.get("", response_model=list[ChatSpec])
async def list_chats(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    channel: Optional[str] = Query(None, description="Filter by channel"),
    mgr: ChatManager = Depends(get_chat_manager),
):
    """List all chats with optional filters."""
    return await mgr.list_chats(user_id=user_id, channel=channel)


@router.post("", response_model=ChatSpec)
async def create_chat(
    request: ChatSpec,
    mgr: ChatManager = Depends(get_chat_manager),
):
    """Create a new chat. Server generates chat_id (UUID) automatically."""
    chat_id = str(uuid4())
    spec = ChatSpec(
        id=chat_id,
        name=request.name,
        session_id=request.session_id,
        user_id=request.user_id,
        channel=request.channel,
        meta=request.meta,
    )
    return await mgr.create_chat(spec)


@router.post("/batch-delete", response_model=dict)
async def batch_delete_chats(
    chat_ids: list[str],
    mgr: ChatManager = Depends(get_chat_manager),
):
    """Delete chats by chat IDs."""
    deleted = await mgr.delete_chats(chat_ids=chat_ids)
    return {"deleted": deleted}


@router.get("/{chat_id}", response_model=ChatHistory)
async def get_chat(
    chat_id: str,
    mgr: ChatManager = Depends(get_chat_manager),
):
    """Get detailed information about a specific chat by UUID."""
    chat_spec = await mgr.get_chat(chat_id)
    if not chat_spec:
        raise HTTPException(
            status_code=404,
            detail=f"Chat not found: {chat_id}",
        )

    # Try to load messages from session file
    try:
        from pathlib import Path
        from ...constant import WORKING_DIR

        sessions_dir = Path(WORKING_DIR) / "sessions"
        session_file = sessions_dir / f"{chat_spec.session_id}.json"

        if session_file.exists():
            data = json.loads(session_file.read_text(encoding="utf-8"))
            messages = [
                ChatMessage(
                    role=m.get("role", "user"),
                    content=m.get("content", ""),
                    timestamp=m.get("timestamp", 0.0),
                    metadata=m.get("metadata", {}),
                )
                for m in data.get("messages", [])
            ]
            return ChatHistory(messages=messages)
    except Exception:
        pass

    return ChatHistory(messages=[])


@router.put("/{chat_id}", response_model=ChatSpec)
async def update_chat(
    chat_id: str,
    spec: ChatSpec,
    mgr: ChatManager = Depends(get_chat_manager),
):
    """Update an existing chat."""
    if spec.id != chat_id:
        raise HTTPException(status_code=400, detail="chat_id mismatch")

    existing = await mgr.get_chat(chat_id)
    if not existing:
        raise HTTPException(
            status_code=404,
            detail=f"Chat not found: {chat_id}",
        )

    return await mgr.update_chat(spec)


@router.delete("/{chat_id}", response_model=dict)
async def delete_chat(
    chat_id: str,
    mgr: ChatManager = Depends(get_chat_manager),
):
    """Delete a chat by UUID."""
    deleted = await mgr.delete_chats(chat_ids=[chat_id])
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Chat not found: {chat_id}",
        )
    return {"deleted": True}
