"""Voice Channel: Twilio ConversationRelay (optional)."""

from __future__ import annotations

import collections
import logging
import secrets
from typing import Any, Dict, Optional

from ..base import BaseChannel, OnReplySent, ProcessHandler
from .session import CallSessionManager
from .twilio_manager import TwilioManager

logger = logging.getLogger(__name__)


class VoiceChannel(BaseChannel):
    """Voice channel backed by Twilio ConversationRelay.

    ``uses_manager_queue = False`` because voice calls are long-lived
    WebSocket sessions.
    """

    channel = "voice"
    uses_manager_queue = False

    def __init__(
        self,
        process: ProcessHandler,
        on_reply_sent: OnReplySent = None,
        show_tool_details: bool = True,
        filter_tool_messages: bool = False,
    ) -> None:
        super().__init__(
            process,
            on_reply_sent,
            show_tool_details,
            filter_tool_messages=filter_tool_messages,
        )
        self.session_mgr = CallSessionManager()
        self.twilio_mgr: Optional[TwilioManager] = None
        self._config: Any = None
        self._enabled = False
        self._public_base_url: str = ""
        self._pending_ws_tokens: collections.OrderedDict[str, None] = (
            collections.OrderedDict()
        )

    @classmethod
    def from_env(
        cls,
        process: ProcessHandler,
        on_reply_sent: OnReplySent = None,
    ) -> "VoiceChannel":
        # Voice is config-first; keep env fallback minimal/disabled.
        instance = cls(process, on_reply_sent)
        instance._enabled = False
        return instance

    @classmethod
    def from_config(
        cls,
        process: ProcessHandler,
        config: Any,
        on_reply_sent: OnReplySent = None,
        show_tool_details: bool = True,
        filter_tool_messages: bool = False,
    ) -> "VoiceChannel":
        instance = cls(
            process,
            on_reply_sent,
            show_tool_details,
            filter_tool_messages=filter_tool_messages,
        )
        instance._config = config
        instance._enabled = bool(getattr(config, "enabled", False))
        instance._public_base_url = (
            str(
                getattr(config, "public_base_url", "")
                or getattr(config, "base_url", "")
                or "",
            )
            .strip()
            .rstrip("/")
        )

        sid = getattr(config, "twilio_account_sid", "") or ""
        token = getattr(config, "twilio_auth_token", "") or ""
        if sid and token:
            instance.twilio_mgr = TwilioManager(sid, token)
        return instance

    async def start(self) -> None:
        """Start the voice channel by configuring Twilio webhooks."""
        if not self._enabled:
            logger.info("Voice channel disabled, skipping start")
            return
        if not self.twilio_mgr:
            logger.warning(
                "Voice enabled but Twilio credentials missing; "
                "voice endpoints stay available but webhook auto-config is skipped",
            )
            return

        phone_number_sid = getattr(self._config, "phone_number_sid", "") or ""
        if not phone_number_sid:
            logger.warning(
                "Voice enabled but phone_number_sid not configured",
            )
            return
        if not self._public_base_url:
            logger.warning(
                "Voice enabled but public_base_url missing; "
                "cannot configure Twilio webhook automatically",
            )
            return

        webhook_url = f"{self._public_base_url}/voice/incoming"
        status_cb_url = f"{self._public_base_url}/voice/status-callback"
        try:
            await self.twilio_mgr.configure_voice_webhook(
                phone_number_sid,
                webhook_url,
                status_callback_url=status_cb_url,
            )
        except Exception:
            logger.exception("Failed to configure Twilio webhook")
            return

        logger.info(
            "Voice channel started: public_base_url=%s phone=%s",
            self._public_base_url,
            getattr(self._config, "phone_number", ""),
        )

    async def stop(self) -> None:
        for session in self.session_mgr.active_sessions():
            try:
                await session.handler.close()
            except Exception:
                logger.exception(
                    "Error closing session handler: call_sid=%s",
                    session.call_sid,
                )
            finally:
                self.session_mgr.end_session(session.call_sid)
        logger.info("Voice channel stopped")

    async def send(
        self,
        to_handle: str,
        text: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        del meta
        session = self.session_mgr.get_session(to_handle)
        if session and session.status == "active":
            await session.handler.send_text(text)

    def build_agent_request_from_native(self, native_payload: Any) -> Any:
        text = (
            native_payload.get("transcript", "")
            if isinstance(native_payload, dict)
            else ""
        )
        session_id = (
            native_payload.get("session_id", "")
            if isinstance(native_payload, dict)
            else ""
        )
        user_id = (
            native_payload.get("from_number", "")
            if isinstance(native_payload, dict)
            else ""
        )
        return {
            "session_id": session_id,
            "user_id": user_id,
            "channel": self.channel,
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": text}],
                },
            ],
        }

    @property
    def config(self) -> Any:
        return self._config

    @property
    def process(self) -> ProcessHandler:
        return self._process

    _MAX_PENDING_TOKENS = 100

    def create_ws_token(self) -> str:
        while len(self._pending_ws_tokens) >= self._MAX_PENDING_TOKENS:
            self._pending_ws_tokens.popitem(last=False)
        token = secrets.token_urlsafe(32)
        self._pending_ws_tokens[token] = None
        return token

    def validate_ws_token(self, token: str) -> bool:
        return self._pending_ws_tokens.pop(token, ...) is not ...

    def get_tunnel_url(self) -> str | None:
        return self._public_base_url or None

    def get_tunnel_wss_url(self) -> str | None:
        if not self._public_base_url:
            return None
        if self._public_base_url.startswith("https://"):
            return "wss://" + self._public_base_url[len("https://") :]
        if self._public_base_url.startswith("http://"):
            return "ws://" + self._public_base_url[len("http://") :]
        return None
