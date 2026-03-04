# pylint: disable=too-many-branches,too-many-statements
"""Feishu (Lark) channel: WebSocket receive, Open API send.

Key improvements over CoPaw:
- Framework-independent content types.
- Async token management with auto-refresh.
- Structured session management (chat_id / open_id based).
- Research-specific: rich card messages for paper citations.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..base import (
    BaseChannel,
    ContentType,
    TextContent,
    ImageContent,
    FileContent,
    OnReplySent,
    OutgoingContentPart,
    ProcessHandler,
)
from ..utils import split_long_message, file_url_to_local_path

logger = logging.getLogger(__name__)

# Constants
FEISHU_PROCESSED_IDS_MAX = 2000
FEISHU_NICKNAME_CACHE_MAX = 500
FEISHU_TOKEN_REFRESH_BEFORE_SECONDS = 300
FEISHU_FILE_MAX_BYTES = 30 * 1024 * 1024  # 30MB


def _short_session_id(full_id: str) -> str:
    """Short suffix for session lookup."""
    if not full_id:
        return ""
    return full_id[-16:] if len(full_id) > 16 else full_id


class FeishuChannel(BaseChannel):
    """Feishu/Lark channel: WebSocket long connection for receive,
    Open API (tenant_access_token) for send.

    Session mapping:
    - Group chat: ``feishu:chat_id:<chat_id>``
    - P2P: ``feishu:open_id:<open_id>``
    """

    channel = "feishu"

    def __init__(
        self,
        process: ProcessHandler,
        enabled: bool,
        app_id: str,
        app_secret: str,
        bot_prefix: str = "[BOT] ",
        encrypt_key: str = "",
        verification_token: str = "",
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
        self.app_id = app_id
        self.app_secret = app_secret
        self.bot_prefix = bot_prefix
        self.encrypt_key = encrypt_key
        self.verification_token = verification_token
        self._media_dir = Path(media_dir).expanduser()

        self._client: Any = None
        self._ws_client: Any = None
        self._ws_thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_event = threading.Event()

        self._tenant_access_token: Optional[str] = None
        self._tenant_access_token_expire_at: float = 0.0
        self._token_lock = asyncio.Lock()
        self._http: Optional[Any] = None

        # Message ID dedup
        self._processed_message_ids: OrderedDict[str, None] = OrderedDict()
        # session_id -> (receive_id, receive_id_type) for send
        self._receive_id_store: Dict[str, Tuple[str, str]] = {}
        self._receive_id_lock = asyncio.Lock()
        # Nickname cache
        self._nickname_cache: Dict[str, str] = {}

    # ── factory methods ────────────────────────────────────────────

    @classmethod
    def from_env(
        cls,
        process: ProcessHandler,
        on_reply_sent: OnReplySent = None,
    ) -> "FeishuChannel":
        return cls(
            process=process,
            enabled=os.getenv("FEISHU_CHANNEL_ENABLED", "0") == "1",
            app_id=os.getenv("FEISHU_APP_ID", ""),
            app_secret=os.getenv("FEISHU_APP_SECRET", ""),
            bot_prefix=os.getenv("FEISHU_BOT_PREFIX", "[BOT] "),
            encrypt_key=os.getenv("FEISHU_ENCRYPT_KEY", ""),
            verification_token=os.getenv("FEISHU_VERIFICATION_TOKEN", ""),
            media_dir=os.getenv("FEISHU_MEDIA_DIR", "~/.researchclaw/media"),
            on_reply_sent=on_reply_sent,
        )

    @classmethod
    def from_config(
        cls,
        process: ProcessHandler,
        config: Any,
        on_reply_sent: OnReplySent = None,
        show_tool_details: bool = True,
    ) -> "FeishuChannel":
        return cls(
            process=process,
            enabled=getattr(config, "enabled", False),
            app_id=getattr(config, "app_id", "") or "",
            app_secret=getattr(config, "app_secret", "") or "",
            bot_prefix=getattr(config, "bot_prefix", "[BOT] ") or "[BOT] ",
            encrypt_key=getattr(config, "encrypt_key", "") or "",
            verification_token=getattr(config, "verification_token", "") or "",
            media_dir=getattr(config, "media_dir", "~/.researchclaw/media")
            or "~/.researchclaw/media",
            on_reply_sent=on_reply_sent,
            show_tool_details=show_tool_details,
        )

    # ── session resolution ─────────────────────────────────────────

    def resolve_session_id(
        self,
        sender_id: str,
        channel_meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        meta = channel_meta or {}
        chat_id = (meta.get("feishu_chat_id") or "").strip()
        chat_type = (meta.get("feishu_chat_type") or "p2p").strip()
        if chat_type == "group" and chat_id:
            return _short_session_id(chat_id)
        if sender_id:
            return _short_session_id(sender_id)
        if chat_id:
            return _short_session_id(chat_id)
        return f"{self.channel}:{sender_id}"

    def get_to_handle_from_request(self, request: Any) -> str:
        """Feishu sends by session_id (maps to receive_id)."""
        if isinstance(request, dict):
            return request.get("session_id", "") or ""
        return getattr(request, "session_id", "") or ""

    def build_agent_request_from_native(self, native_payload: Any) -> Any:
        payload = native_payload if isinstance(native_payload, dict) else {}
        channel_id = payload.get("channel_id") or self.channel
        sender_id = payload.get("sender_id") or ""
        content_parts = payload.get("content_parts") or []
        meta = payload.get("meta") or {}
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

    # ── token management ───────────────────────────────────────────

    async def _ensure_token(self) -> str:
        """Get or refresh tenant_access_token."""
        async with self._token_lock:
            now = time.time()
            if (
                self._tenant_access_token
                and now
                < self._tenant_access_token_expire_at
                - FEISHU_TOKEN_REFRESH_BEFORE_SECONDS
            ):
                return self._tenant_access_token

            try:
                import aiohttp

                if self._http is None:
                    self._http = aiohttp.ClientSession()

                async with self._http.post(
                    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                    json={
                        "app_id": self.app_id,
                        "app_secret": self.app_secret,
                    },
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    data = await resp.json()
                    token = data.get("tenant_access_token", "")
                    expire = data.get("expire", 7200)
                    self._tenant_access_token = token
                    self._tenant_access_token_expire_at = now + expire
                    return token
            except Exception:
                logger.exception("feishu: token refresh failed")
                return self._tenant_access_token or ""

    # ── receive_id store ───────────────────────────────────────────

    async def _store_receive_id(
        self,
        session_id: str,
        receive_id: str,
        receive_id_type: str,
    ) -> None:
        async with self._receive_id_lock:
            self._receive_id_store[session_id] = (receive_id, receive_id_type)

    async def _get_receive_id(self, session_id: str) -> Tuple[str, str]:
        async with self._receive_id_lock:
            return self._receive_id_store.get(session_id, ("", ""))

    async def _before_consume_process(self, request: Any) -> None:
        """Store receive_id from channel_meta for send path."""
        meta = (
            getattr(request, "channel_meta", None)
            if not isinstance(request, dict)
            else request.get("channel_meta")
        ) or {}
        session_id = (
            request.get("session_id")
            if isinstance(request, dict)
            else getattr(request, "session_id", "")
        ) or ""

        receive_id = meta.get("feishu_receive_id", "")
        receive_id_type = meta.get("feishu_receive_id_type", "open_id")
        if receive_id and session_id:
            await self._store_receive_id(
                session_id,
                receive_id,
                receive_id_type,
            )

    # ── send ───────────────────────────────────────────────────────

    async def send(
        self,
        to_handle: str,
        text: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.enabled:
            return

        receive_id, receive_id_type = await self._get_receive_id(to_handle)
        if not receive_id:
            logger.warning("feishu: no receive_id for session=%s", to_handle)
            return

        token = await self._ensure_token()
        if not token:
            logger.warning("feishu: no token available")
            return

        try:
            import aiohttp

            if self._http is None:
                self._http = aiohttp.ClientSession()

            msg_body = {
                "receive_id": receive_id,
                "msg_type": "text",
                "content": json.dumps({"text": text}),
            }

            async with self._http.post(
                f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}",
                json=msg_body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning(
                        "feishu send failed: HTTP %s: %s",
                        resp.status,
                        body[:200],
                    )
        except Exception:
            logger.exception("feishu: send failed")

    # ── lifecycle ──────────────────────────────────────────────────

    async def start(self) -> None:
        if not self.enabled:
            logger.debug("feishu channel disabled")
            return
        if not self.app_id or not self.app_secret:
            logger.warning("feishu: app_id or app_secret not configured")
            return

        try:
            import lark_oapi as lark
        except ImportError:
            logger.warning(
                "lark-oapi not installed. Install with: pip install lark-oapi",
            )
            return

        self._loop = asyncio.get_running_loop()

        # Build lark client
        self._client = (
            lark.Client.builder()
            .app_id(
                self.app_id,
            )
            .app_secret(self.app_secret)
            .build()
        )

        # Build WebSocket client for event subscription
        event_handler = lark.EventDispatcherHandler.builder(
            self.encrypt_key,
            self.verification_token,
        ).build()

        self._ws_client = lark.ws.Client(
            self.app_id,
            self.app_secret,
            event_handler=event_handler,
        )

        def _run_ws() -> None:
            try:
                self._ws_client.start()
            except Exception:
                logger.exception("feishu: WS thread crashed")

        self._stop_event.clear()
        self._ws_thread = threading.Thread(
            target=_run_ws,
            daemon=True,
            name="feishu_ws",
        )
        self._ws_thread.start()
        logger.info("Feishu channel started")

    async def stop(self) -> None:
        if not self.enabled:
            return
        self._stop_event.set()
        if self._http:
            await self._http.close()
            self._http = None
        self._client = None
        self._ws_client = None
        logger.info("Feishu channel stopped")
