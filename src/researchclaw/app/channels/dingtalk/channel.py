# pylint: disable=too-many-branches,too-many-statements
"""DingTalk channel: DingTalk Stream for incoming, webhook/API for replies.

Key improvements over CoPaw:
- Framework-independent content types.
- Simplified session_webhook store with async lock.
- Better error handling for expired webhooks.
- Research-specific: paper search result cards via DingTalk markdown.
"""
from __future__ import annotations

import asyncio
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base import (
    BaseChannel,
    ContentType,
    TextContent,
    ImageContent,
    FileContent,
    OnReplySent,
    OutgoingContentPart,
    ProcessHandler,
    RunStatus,
)
from ..utils import split_long_message

logger = logging.getLogger(__name__)

DINGTALK_TOKEN_TTL_SECONDS = 7000
SENT_VIA_WEBHOOK = "__sent_via_webhook__"


def _short_session_id(conversation_id: str) -> str:
    """Short suffix of conversation_id for session lookup."""
    if not conversation_id:
        return ""
    return (
        conversation_id[-16:] if len(conversation_id) > 16 else conversation_id
    )


class DingTalkChannel(BaseChannel):
    """DingTalk channel via DingTalk Stream SDK.

    Incoming: DingTalk Stream callback → enqueue to manager.
    Outgoing: session webhook (for reply) or Open API (for proactive).
    """

    channel = "dingtalk"

    def __init__(
        self,
        process: ProcessHandler,
        enabled: bool,
        client_id: str,
        client_secret: str,
        bot_prefix: str = "[BOT] ",
        media_dir: str = "~/.researchclaw/media",
        on_reply_sent: OnReplySent = None,
        show_tool_details: bool = True,
    ):
        super().__init__(
            process,
            on_reply_sent=on_reply_sent,
            show_tool_details=show_tool_details,
        )
        self.enabled = enabled
        self.client_id = client_id
        self.client_secret = client_secret
        self.bot_prefix = bot_prefix
        self._media_dir = Path(media_dir).expanduser()

        self._client: Optional[Any] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stream_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._http: Optional[Any] = None

        # Session webhook store (in-memory)
        self._session_webhook_store: Dict[str, str] = {}
        self._session_webhook_lock = asyncio.Lock()

        # Token cache
        self._token_lock = asyncio.Lock()
        self._token_value: Optional[str] = None
        self._token_expires_at: float = 0.0

        self._debounce_seconds = 0.0

    # ── factory methods ────────────────────────────────────────────

    @classmethod
    def from_env(
        cls,
        process: ProcessHandler,
        on_reply_sent: OnReplySent = None,
    ) -> "DingTalkChannel":
        return cls(
            process=process,
            enabled=os.getenv("DINGTALK_CHANNEL_ENABLED", "0") == "1",
            client_id=os.getenv("DINGTALK_CLIENT_ID", ""),
            client_secret=os.getenv("DINGTALK_CLIENT_SECRET", ""),
            bot_prefix=os.getenv("DINGTALK_BOT_PREFIX", "[BOT] "),
            media_dir=os.getenv("DINGTALK_MEDIA_DIR", "~/.researchclaw/media"),
            on_reply_sent=on_reply_sent,
        )

    @classmethod
    def from_config(
        cls,
        process: ProcessHandler,
        config: Any,
        on_reply_sent: OnReplySent = None,
        show_tool_details: bool = True,
    ) -> "DingTalkChannel":
        return cls(
            process=process,
            enabled=getattr(config, "enabled", False),
            client_id=getattr(config, "client_id", "") or "",
            client_secret=getattr(config, "client_secret", "") or "",
            bot_prefix=getattr(config, "bot_prefix", "[BOT] ") or "[BOT] ",
            media_dir=getattr(config, "media_dir", "~/.researchclaw/media")
            or "~/.researchclaw/media",
            on_reply_sent=on_reply_sent,
            show_tool_details=show_tool_details,
        )

    # ── session ID / webhook ───────────────────────────────────────

    def resolve_session_id(
        self,
        sender_id: str,
        channel_meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        meta = channel_meta or {}
        cid = meta.get("conversation_id")
        if cid:
            return _short_session_id(cid)
        return f"{self.channel}:{sender_id}"

    def to_handle_from_target(self, *, user_id: str, session_id: str) -> str:
        return f"dingtalk:sw:{session_id}"

    def build_agent_request_from_native(self, native_payload: Any) -> Any:
        payload = native_payload if isinstance(native_payload, dict) else {}
        channel_id = payload.get("channel_id") or self.channel
        sender_id = payload.get("sender_id") or ""
        content_parts = payload.get("content_parts") or []
        meta = dict(payload.get("meta") or {})
        if payload.get("session_webhook"):
            meta["session_webhook"] = payload["session_webhook"]
        session_id = self.resolve_session_id(sender_id, meta)
        request = self.build_agent_request_from_user_content(
            channel_id=channel_id,
            sender_id=sender_id,
            session_id=session_id,
            content_parts=content_parts,
            channel_meta=meta,
        )
        if hasattr(request, "channel_meta"):
            request.channel_meta = meta
        elif isinstance(request, dict):
            request["channel_meta"] = meta
        return request

    # ── webhook store ──────────────────────────────────────────────

    async def _store_session_webhook(self, key: str, webhook: str) -> None:
        async with self._session_webhook_lock:
            self._session_webhook_store[key] = webhook

    async def _get_session_webhook(self, key: str) -> Optional[str]:
        async with self._session_webhook_lock:
            return self._session_webhook_store.get(key)

    # ── send ───────────────────────────────────────────────────────

    async def send(
        self,
        to_handle: str,
        text: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.enabled:
            return

        # Try session webhook first
        webhook = (meta or {}).get("session_webhook")
        if not webhook:
            webhook = await self._get_session_webhook(to_handle)

        if webhook:
            await self._send_via_webhook(webhook, text)
        else:
            logger.warning(
                "dingtalk: no webhook for to_handle=%s, message dropped",
                to_handle,
            )

    async def _send_via_webhook(self, webhook: str, text: str) -> None:
        """Send text via DingTalk session webhook."""
        try:
            import aiohttp
        except ImportError:
            logger.warning("aiohttp not installed")
            return

        if self._http is None:
            self._http = aiohttp.ClientSession()

        # DingTalk markdown supports basic formatting
        payload = {
            "msgtype": "text",
            "text": {"content": text},
        }
        try:
            async with self._http.post(
                webhook,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning(
                        "dingtalk webhook send failed: HTTP %s: %s",
                        resp.status,
                        body[:200],
                    )
        except Exception:
            logger.exception("dingtalk: webhook send failed")

    # ── lifecycle ──────────────────────────────────────────────────

    async def start(self) -> None:
        if not self.enabled:
            logger.debug("dingtalk channel disabled")
            return
        if not self.client_id or not self.client_secret:
            logger.warning(
                "dingtalk: client_id or client_secret not configured",
            )
            return

        try:
            import dingtalk_stream
        except ImportError:
            logger.warning(
                "dingtalk-stream not installed. "
                "Install with: pip install dingtalk-stream",
            )
            return

        self._loop = asyncio.get_running_loop()
        credential = dingtalk_stream.Credential(
            self.client_id,
            self.client_secret,
        )
        self._client = dingtalk_stream.DingTalkStreamClient(credential)

        # Register chatbot handler
        async def _on_message(headers: dict, incoming: Any) -> Any:
            text = (
                (getattr(incoming, "text", None) or {})
                .get("content", "")
                .strip()
            )
            sender_id = getattr(incoming, "sender_staff_id", "") or getattr(
                incoming,
                "sender_id",
                "",
            )
            conversation_id = getattr(incoming, "conversation_id", "")
            session_webhook = getattr(incoming, "session_webhook", "")

            content_parts = (
                [TextContent(text=text)] if text else [TextContent(text="")]
            )

            meta = {
                "conversation_id": conversation_id,
                "sender_id": sender_id,
            }

            native = {
                "channel_id": self.channel,
                "sender_id": sender_id,
                "content_parts": content_parts,
                "meta": meta,
                "session_webhook": session_webhook,
            }

            # Store webhook for proactive sends
            if session_webhook:
                key = self.to_handle_from_target(
                    user_id=sender_id,
                    session_id=self.resolve_session_id(sender_id, meta),
                )
                asyncio.run_coroutine_threadsafe(
                    self._store_session_webhook(key, session_webhook),
                    self._loop,
                )

            if self._enqueue is not None:
                self._enqueue(native)
            else:
                logger.warning("dingtalk: _enqueue not set")

            return dingtalk_stream.AckMessage.STATUS_OK, "OK"

        self._client.register_callback_handler(
            dingtalk_stream.ChatbotMessage.TOPIC,
            dingtalk_stream.AsyncChatbotHandler(_on_message),
        )

        # Run stream in background thread
        self._stop_event.clear()

        def _run_stream() -> None:
            try:
                self._client.start_forever()
            except Exception:
                logger.exception("dingtalk stream thread crashed")

        self._stream_thread = threading.Thread(
            target=_run_stream,
            daemon=True,
            name="dingtalk_stream",
        )
        self._stream_thread.start()
        logger.info("DingTalk channel started")

    async def stop(self) -> None:
        if not self.enabled:
            return
        self._stop_event.set()
        if self._http:
            await self._http.close()
            self._http = None
        # dingtalk_stream doesn't have a clean shutdown API
        self._client = None
        logger.info("DingTalk channel stopped")
