"""iMessage channel: macOS Messages.app integration via sqlite + imsg CLI.

Key improvements over CoPaw:
- Framework-independent content types.
- Async-safe polling with proper thread shutdown.
- Research-specific: Formatted paper citation delivery via iMessage.
"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import sqlite3
import subprocess
import threading
import time
from typing import Any, Dict, Optional

from ..base import (
    BaseChannel,
    ContentType,
    TextContent,
    OnReplySent,
    ProcessHandler,
)

logger = logging.getLogger(__name__)


class IMessageChannel(BaseChannel):
    """iMessage channel: polls macOS Messages chat.db for new messages,
    sends via ``imsg`` CLI tool.

    Requirements:
    - macOS only
    - ``imsg`` CLI: ``brew install steipete/tap/imsg``
    - Full Disk Access for the process
    """

    channel = "imessage"

    def __init__(
        self,
        process: ProcessHandler,
        enabled: bool,
        db_path: str = "~/Library/Messages/chat.db",
        poll_sec: float = 1.0,
        bot_prefix: str = "[BOT] ",
        on_reply_sent: OnReplySent = None,
        show_tool_details: bool = True,
    ):
        super().__init__(
            process,
            on_reply_sent=on_reply_sent,
            show_tool_details=show_tool_details,
        )
        self.enabled = enabled
        self.db_path = os.path.expanduser(db_path)
        self.poll_sec = poll_sec
        self.bot_prefix = bot_prefix

        self._imsg_path: Optional[str] = None
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_rowid: int = 0
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # ── factory methods ────────────────────────────────────────────

    @classmethod
    def from_env(
        cls,
        process: ProcessHandler,
        on_reply_sent: OnReplySent = None,
    ) -> "IMessageChannel":
        return cls(
            process=process,
            enabled=os.getenv("IMESSAGE_CHANNEL_ENABLED", "0") == "1",
            db_path=os.getenv(
                "IMESSAGE_DB_PATH",
                "~/Library/Messages/chat.db",
            ),
            poll_sec=float(os.getenv("IMESSAGE_POLL_SEC", "1.0")),
            bot_prefix=os.getenv("IMESSAGE_BOT_PREFIX", "[BOT] "),
            on_reply_sent=on_reply_sent,
        )

    @classmethod
    def from_config(
        cls,
        process: ProcessHandler,
        config: Any,
        on_reply_sent: OnReplySent = None,
        show_tool_details: bool = True,
    ) -> "IMessageChannel":
        return cls(
            process=process,
            enabled=getattr(config, "enabled", False),
            db_path=getattr(config, "db_path", "~/Library/Messages/chat.db")
            or "~/Library/Messages/chat.db",
            poll_sec=getattr(config, "poll_sec", 1.0),
            bot_prefix=getattr(config, "bot_prefix", "[BOT] ") or "[BOT] ",
            on_reply_sent=on_reply_sent,
            show_tool_details=show_tool_details,
        )

    # ── helpers ────────────────────────────────────────────────────

    def _ensure_imsg(self) -> str:
        """Locate the imsg CLI tool."""
        path = shutil.which("imsg")
        if not path:
            raise RuntimeError(
                "Cannot find executable: imsg. Install it with:\n"
                "  brew install steipete/tap/imsg\n"
                "Then verify:\n"
                "  which imsg\n",
            )
        return path

    def _get_last_rowid(self) -> int:
        """Get the current max ROWID from the messages table."""
        try:
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            cursor = conn.execute("SELECT MAX(ROWID) FROM message")
            row = cursor.fetchone()
            conn.close()
            return row[0] or 0
        except Exception:
            logger.exception("imessage: failed to get last rowid")
            return 0

    def _poll_new_messages(self) -> list[dict]:
        """Poll for new messages since last_rowid."""
        try:
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            cursor = conn.execute(
                """
                SELECT m.ROWID, m.text, m.is_from_me,
                       h.id as sender_id
                FROM message m
                LEFT JOIN handle h ON m.handle_id = h.ROWID
                WHERE m.ROWID > ? AND m.is_from_me = 0
                ORDER BY m.ROWID ASC
                """,
                (self._last_rowid,),
            )
            rows = cursor.fetchall()
            conn.close()

            messages = []
            for row in rows:
                rowid, text, is_from_me, sender_id = row
                self._last_rowid = max(self._last_rowid, rowid)
                if text and text.strip():
                    messages.append(
                        {
                            "rowid": rowid,
                            "text": text.strip(),
                            "sender_id": sender_id or "",
                        },
                    )
            return messages
        except Exception:
            logger.exception("imessage: poll failed")
            return []

    def _send_sync(self, to_handle: str, text: str) -> None:
        """Send a message via imsg CLI (blocking)."""
        if not self._imsg_path:
            logger.warning("imessage: imsg not available")
            return
        try:
            subprocess.run(
                [self._imsg_path, "send", to_handle, text],
                capture_output=True,
                timeout=30,
                check=False,
            )
        except Exception:
            logger.exception("imessage: send failed to %s", to_handle)

    # ── send ───────────────────────────────────────────────────────

    async def send(
        self,
        to_handle: str,
        text: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.enabled:
            return
        # Run blocking send in executor
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._send_sync, to_handle, text)

    async def _on_consume_error(
        self,
        request: Any,
        to_handle: str,
        err_text: str,
    ) -> None:
        """Send error via imsg (sync, in executor)."""
        await self.send(to_handle, err_text)

    # ── lifecycle ──────────────────────────────────────────────────

    async def start(self) -> None:
        if not self.enabled:
            logger.debug("imessage channel disabled")
            return

        import sys

        if sys.platform != "darwin":
            logger.warning("imessage: only available on macOS")
            self.enabled = False
            return

        self._imsg_path = self._ensure_imsg()
        self._last_rowid = self._get_last_rowid()
        self._loop = asyncio.get_running_loop()
        self._stop_event.clear()

        def _poll_loop() -> None:
            while not self._stop_event.is_set():
                try:
                    messages = self._poll_new_messages()
                    for msg in messages:
                        content_parts = [TextContent(text=msg["text"])]
                        native = {
                            "channel_id": self.channel,
                            "sender_id": msg["sender_id"],
                            "content_parts": content_parts,
                            "meta": {"sender_id": msg["sender_id"]},
                        }
                        if (
                            self._enqueue is not None
                            and self._loop is not None
                        ):
                            self._loop.call_soon_threadsafe(
                                self._enqueue,
                                native,
                            )
                except Exception:
                    logger.exception("imessage: poll loop error")
                self._stop_event.wait(self.poll_sec)

        self._thread = threading.Thread(
            target=_poll_loop,
            daemon=True,
            name="imessage_poll",
        )
        self._thread.start()
        logger.info(
            "iMessage channel started (polling every %.1fs)",
            self.poll_sec,
        )

    async def stop(self) -> None:
        if not self.enabled:
            return
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._thread = None
        logger.info("iMessage channel stopped")
