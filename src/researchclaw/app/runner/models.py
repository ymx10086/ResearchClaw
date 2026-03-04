"""Chat models for runner with UUID management.

Provides Pydantic models for chat specifications, history, and persistence.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from pydantic import BaseModel, Field

from ..channels.schema import DEFAULT_CHANNEL


class ChatSpec(BaseModel):
    """Chat specification with UUID identifier.

    Stored in JSON and can be used for session tracking.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Chat UUID identifier",
    )
    name: str = Field(default="New Chat", description="Chat display name")
    session_id: str = Field(
        ...,
        description="Session identifier (channel:user_id format)",
    )
    user_id: str = Field(..., description="User identifier")
    channel: str = Field(default=DEFAULT_CHANNEL, description="Channel name")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Chat creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Chat last update timestamp",
    )
    meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (e.g. research context)",
    )


class ChatMessage(BaseModel):
    """A single chat message for history display."""

    role: str = "user"
    content: Any = ""
    timestamp: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatHistory(BaseModel):
    """Complete chat view with messages."""

    messages: List[ChatMessage] = Field(default_factory=list)


class ChatsFile(BaseModel):
    """Chat registry file for JSON repository.

    Stores chat_id (UUID) -> session_id mappings for persistence.
    """

    version: int = 1
    chats: List[ChatSpec] = Field(default_factory=list)
