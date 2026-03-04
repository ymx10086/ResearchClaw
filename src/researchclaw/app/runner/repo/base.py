"""Chat repository for storing chat/session specs."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ..models import ChatSpec, ChatsFile
from ...channels.schema import DEFAULT_CHANNEL


class BaseChatRepository(ABC):
    """Abstract repository for chat specs persistence.

    Subclasses implement load/save; convenience CRUD methods
    are provided here for consistency.
    """

    @abstractmethod
    async def load(self) -> ChatsFile:
        """Load all chat specs from storage."""
        raise NotImplementedError

    @abstractmethod
    async def save(self, chats_file: ChatsFile) -> None:
        """Persist all chat specs to storage (should be atomic if possible)."""
        raise NotImplementedError

    # ---- Convenience operations ----

    async def list_chats(self) -> list[ChatSpec]:
        """List all chat specifications."""
        cf = await self.load()
        return cf.chats

    async def get_chat(self, chat_id: str) -> Optional[ChatSpec]:
        """Get chat spec by chat_id (UUID)."""
        cf = await self.load()
        for chat in cf.chats:
            if chat.id == chat_id:
                return chat
        return None

    async def get_chat_by_id(
        self,
        session_id: str,
        user_id: str,
        channel: str = DEFAULT_CHANNEL,
    ) -> Optional[ChatSpec]:
        """Get chat spec by session_id, user_id, and channel."""
        cf = await self.load()
        for chat in cf.chats:
            if (
                chat.session_id == session_id
                and chat.user_id == user_id
                and chat.channel == channel
            ):
                return chat
        return None

    async def upsert_chat(self, spec: ChatSpec) -> None:
        """Insert or update a chat spec."""
        cf = await self.load()
        for i, c in enumerate(cf.chats):
            if c.id == spec.id:
                cf.chats[i] = spec
                break
        else:
            cf.chats.append(spec)
        await self.save(cf)

    async def delete_chats(self, chat_ids: list[str]) -> bool:
        """Delete chat specs by IDs.

        Returns True if any were deleted.
        """
        if not chat_ids:
            return False
        cf = await self.load()
        before = len(cf.chats)
        cf.chats = [c for c in cf.chats if c.id not in chat_ids]
        if len(cf.chats) == before:
            return False
        await self.save(cf)
        return True

    async def filter_chats(
        self,
        user_id: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> list[ChatSpec]:
        """Filter chats by user_id and/or channel."""
        cf = await self.load()
        results = cf.chats
        if user_id is not None:
            results = [c for c in results if c.user_id == user_id]
        if channel is not None:
            results = [c for c in results if c.channel == channel]
        return results
