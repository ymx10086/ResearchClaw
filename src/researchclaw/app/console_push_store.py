"""Console push store for SSE-based real-time updates.

Supports two complementary push mechanisms:

1. **SSE queues** (ConsolePushStore): Each connected frontend client gets its
   own asyncio queue for real-time event streaming. Events are pushed to all
   connected clients simultaneously.

2. **Session messages** (module-level functions): Bounded in-memory message
   store keyed by session_id. Used for async push from background tasks
   (e.g. cron job errors). Messages are consumed (taken) by the frontend
   polling endpoint and auto-expire after _MAX_AGE_SECONDS.

Both mechanisms coexist: SSE for live streaming, session messages for
deferred/async notifications.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# =====================================================================
# Part 1: SSE Queue-based push (for real-time frontend streaming)
# =====================================================================


class ConsolePushStore:
    """Store for pushing messages to connected console clients via SSE.

    Each connected client gets its own asyncio queue for receiving events.
    """

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}

    def subscribe(self, client_id: str) -> asyncio.Queue:
        """Create a queue for a new client subscription."""
        queue: asyncio.Queue = asyncio.Queue()
        self._queues[client_id] = queue
        return queue

    def add_client(
        self,
        client_id: str,
        queue: asyncio.Queue | None = None,
    ) -> asyncio.Queue:
        """Backward-compatible alias for subscribe()."""
        if queue is None:
            return self.subscribe(client_id)
        self._queues[client_id] = queue
        return queue

    def unsubscribe(self, client_id: str) -> None:
        """Remove a client subscription."""
        self._queues.pop(client_id, None)

    def remove_client(self, client_id: str) -> None:
        """Backward-compatible alias for unsubscribe()."""
        self.unsubscribe(client_id)

    async def push(self, event: str, data: Any) -> None:
        """Push an event to all connected clients."""
        message = {"event": event, "data": data}
        for queue in self._queues.values():
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.debug("Queue full for a client, dropping message")

    async def broadcast(self, event: dict[str, Any]) -> None:
        """Backward-compatible broadcast API for router usage."""
        for queue in self._queues.values():
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.debug("Queue full for a client, dropping message")

    @property
    def client_count(self) -> int:
        """Number of connected clients."""
        return len(self._queues)


# Global SSE push store instance
push_store = ConsolePushStore()


# =====================================================================
# Part 2: Session-based message store (for async/deferred notifications)
# =====================================================================

_list: List[Dict[str, Any]] = []
_lock = asyncio.Lock()
_MAX_AGE_SECONDS = 60
_MAX_MESSAGES = 500


async def append(session_id: str, text: str) -> None:
    """Append a message (bounded: oldest dropped if over _MAX_MESSAGES).

    Args:
        session_id: Target session to receive the message
        text: Message text content
    """
    if not session_id or not text:
        return
    async with _lock:
        _list.append(
            {
                "id": str(uuid.uuid4()),
                "text": text,
                "ts": time.time(),
                "session_id": session_id,
            },
        )
        if len(_list) > _MAX_MESSAGES:
            _list.sort(key=lambda m: m["ts"])
            del _list[: len(_list) - _MAX_MESSAGES]


async def take(session_id: str) -> List[Dict[str, Any]]:
    """Return and remove all messages for the session.

    Args:
        session_id: Session to drain messages from

    Returns:
        List of message dicts with 'id' and 'text' keys
    """
    if not session_id:
        return []
    async with _lock:
        out = [m for m in _list if m.get("session_id") == session_id]
        _list[:] = [m for m in _list if m.get("session_id") != session_id]
        return _strip_ts(out)


async def take_all() -> List[Dict[str, Any]]:
    """Return and remove all messages."""
    async with _lock:
        out = list(_list)
        _list.clear()
        return _strip_ts(out)


def _strip_ts(msgs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Strip internal timestamp from messages for API response."""
    return [{"id": m["id"], "text": m["text"]} for m in msgs]


async def get_recent(
    max_age_seconds: int = _MAX_AGE_SECONDS,
) -> List[Dict[str, Any]]:
    """Return recent messages (not consumed). Drop older than max_age_seconds.

    Args:
        max_age_seconds: Maximum age of messages to retain

    Returns:
        List of recent message dicts
    """
    now = time.time()
    cutoff = now - max_age_seconds
    async with _lock:
        out = [m for m in _list if m["ts"] >= cutoff]
        _list[:] = out
        return _strip_ts(out)
