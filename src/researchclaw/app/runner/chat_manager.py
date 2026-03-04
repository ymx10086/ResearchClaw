"""Chat manager for managing chat specifications (CRUD operations)."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from .models import ChatSpec
from .repo import BaseChatRepository
from ..channels.schema import DEFAULT_CHANNEL

logger = logging.getLogger(__name__)


class ChatManager:
    """Manages chat specifications in repository.

    Only handles ChatSpec CRUD operations.
    Does NOT manage session state — that's handled by runner/session.
    """

    def __init__(self, *, repo: BaseChatRepository):
        self._repo = repo
        self._lock = asyncio.Lock()

    # ----- Read Operations -----

    async def list_chats(
        self,
        user_id: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> list[ChatSpec]:
        """List chat specs with optional filters."""
        async with self._lock:
            return await self._repo.filter_chats(
                user_id=user_id,
                channel=channel,
            )

    async def get_chat(self, chat_id: str) -> Optional[ChatSpec]:
        """Get chat spec by chat_id (UUID)."""
        async with self._lock:
            return await self._repo.get_chat(chat_id)

    async def get_or_create_chat(
        self,
        session_id: str,
        user_id: str,
        channel: str = DEFAULT_CHANNEL,
        name: str = "New Chat",
    ) -> ChatSpec:
        """Get existing chat or create a new one.

        Useful for auto-registration when chats come from channels.
        """
        async with self._lock:
            existing = await self._repo.get_chat_by_id(
                session_id,
                user_id,
                channel,
            )
            if existing:
                return existing

            spec = ChatSpec(
                session_id=session_id,
                user_id=user_id,
                channel=channel,
                name=name,
            )
            await self._repo.upsert_chat(spec)
            logger.debug(
                "Auto-registered new chat: %s -> %s",
                spec.id,
                session_id,
            )
            return spec

    async def create_chat(self, spec: ChatSpec) -> ChatSpec:
        """Create a new chat."""
        async with self._lock:
            await self._repo.upsert_chat(spec)
            return spec

    async def update_chat(self, spec: ChatSpec) -> ChatSpec:
        """Update an existing chat spec."""
        async with self._lock:
            spec.updated_at = datetime.now(timezone.utc)
            await self._repo.upsert_chat(spec)
            return spec

    async def delete_chats(self, chat_ids: list[str]) -> bool:
        """Delete chat specs. Returns True if any were deleted."""
        async with self._lock:
            deleted = await self._repo.delete_chats(chat_ids)
            if deleted:
                logger.debug("Deleted chats: %s", chat_ids)
            return deleted

    async def count_chats(
        self,
        user_id: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> int:
        """Count chats matching filters."""
        async with self._lock:
            chats = await self._repo.filter_chats(
                user_id=user_id,
                channel=channel,
            )
            return len(chats)
