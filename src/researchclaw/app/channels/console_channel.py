# pylint: disable=too-many-branches
"""Console Channel: pretty-prints agent responses to stdout.

Key improvements over CoPaw:
- Framework-independent content types (no agentscope_runtime dependency).
- Rich ANSI output with emoji indicators per content type.
- Push-store integration for web console SSE streaming.
- Research-specific: paper citation formatting in terminal output.
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import (
    BaseChannel,
    ContentType,
    OnReplySent,
    OutgoingContentPart,
    ProcessHandler,
)

logger = logging.getLogger(__name__)

# ── ANSI colour helpers (degrade gracefully on non-tty) ────────────
_USE_COLOR = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

_GREEN = "\033[32m" if _USE_COLOR else ""
_YELLOW = "\033[33m" if _USE_COLOR else ""
_CYAN = "\033[36m" if _USE_COLOR else ""
_RED = "\033[31m" if _USE_COLOR else ""
_BOLD = "\033[1m" if _USE_COLOR else ""
_DIM = "\033[2m" if _USE_COLOR else ""
_RESET = "\033[0m" if _USE_COLOR else ""


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


class ConsoleChannel(BaseChannel):
    """Console Channel: prints agent responses to stdout.

    Input is handled by AgentApp's ``/agent/process`` endpoint; this
    channel only takes care of output (printing to the terminal and
    pushing to the web console via push_store).
    """

    channel = "console"

    def __init__(
        self,
        process: ProcessHandler,
        enabled: bool = True,
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
        self.bot_prefix = bot_prefix

    # ── factory methods ────────────────────────────────────────────

    @classmethod
    def from_env(
        cls,
        process: ProcessHandler,
        on_reply_sent: OnReplySent = None,
    ) -> "ConsoleChannel":
        return cls(
            process=process,
            enabled=os.getenv("CONSOLE_CHANNEL_ENABLED", "1") == "1",
            bot_prefix=os.getenv("CONSOLE_BOT_PREFIX", "[BOT] "),
            on_reply_sent=on_reply_sent,
        )

    @classmethod
    def from_config(
        cls,
        process: ProcessHandler,
        config: Any,
        on_reply_sent: OnReplySent = None,
        show_tool_details: bool = True,
    ) -> "ConsoleChannel":
        return cls(
            process=process,
            enabled=getattr(config, "enabled", True),
            bot_prefix=getattr(config, "bot_prefix", "[BOT] ") or "[BOT] ",
            on_reply_sent=on_reply_sent,
            show_tool_details=show_tool_details,
        )

    # ── consume ────────────────────────────────────────────────────

    async def consume_one(self, payload: Any) -> None:
        """Process one payload: stream events and print to stdout."""
        # Build request from native dict or use as-is
        if isinstance(payload, dict) and "content_parts" in payload:
            session_id = self.resolve_session_id(
                payload.get("sender_id") or "",
                payload.get("meta"),
            )
            content_parts = payload.get("content_parts") or []
            should_process, merged = self._apply_no_text_debounce(
                session_id,
                content_parts,
            )
            if not should_process:
                return
            payload = {**payload, "content_parts": merged}
            request = self.build_agent_request_from_native(payload)
        else:
            request = payload
            if getattr(request, "input", None):
                session_id = getattr(request, "session_id", "") or ""
                contents = list(
                    getattr(request.input[0], "content", None) or [],
                )
                should_process, merged = self._apply_no_text_debounce(
                    session_id,
                    contents,
                )
                if not should_process:
                    return
                if merged and hasattr(request.input[0], "content"):
                    request.input[0].content = merged

        try:
            send_meta = getattr(request, "channel_meta", None) or {}
            send_meta.setdefault("bot_prefix", self.bot_prefix)
            last_response = None
            event_count = 0

            async for event in self._process(request):
                event_count += 1
                obj = getattr(event, "object", None)
                status = getattr(event, "status", None)
                ev_type = getattr(event, "type", None)

                logger.debug(
                    "console event #%s: obj=%s status=%s type=%s",
                    event_count,
                    obj,
                    status,
                    ev_type,
                )

                # Completed message → print parts
                completed = False
                if hasattr(status, "value"):
                    completed = status.value == "completed"
                elif isinstance(status, str):
                    completed = status == "completed"

                if obj == "message" and completed:
                    parts = self._message_to_content_parts(event)
                    self._print_parts(parts, ev_type)

                elif obj == "response":
                    last_response = event

            logger.info(
                "console stream done: events=%s response=%s",
                event_count,
                last_response is not None,
            )

            if last_response and getattr(last_response, "error", None):
                err = getattr(
                    last_response.error,
                    "message",
                    str(last_response.error),
                )
                self._print_error(err)

            to_handle = getattr(request, "user_id", "") or ""
            if self._on_reply_sent:
                self._on_reply_sent(
                    self.channel,
                    to_handle,
                    getattr(request, "session_id", None)
                    or f"{self.channel}:{to_handle}",
                )

        except Exception:
            logger.exception("console process/reply failed")
            self._print_error(
                "An error occurred while processing your request.",
            )

    # ── pretty-print helpers ───────────────────────────────────────

    def _print_parts(
        self,
        parts: List[OutgoingContentPart],
        ev_type: Optional[str] = None,
    ) -> None:
        """Print outgoing content parts to stdout with ANSI styling."""
        ts = _ts()
        label = f" ({ev_type})" if ev_type else ""
        print(f"\n{_GREEN}{_BOLD}🤖 [{ts}] Bot{label}{_RESET}")

        for p in parts:
            t = getattr(p, "type", None)
            t_val = (
                t.value if isinstance(t, ContentType) else str(t) if t else ""
            )

            if t_val == ContentType.TEXT.value:
                text = getattr(p, "text", None) or ""
                if text:
                    print(f"{self.bot_prefix}{text}")
            elif t_val == ContentType.REFUSAL.value:
                refusal = getattr(p, "refusal", None) or ""
                if refusal:
                    print(f"{_RED}⚠ Refusal: {refusal}{_RESET}")
            elif t_val == ContentType.IMAGE.value:
                url = getattr(p, "image_url", None) or ""
                print(f"{_YELLOW}🖼  [Image: {url}]{_RESET}")
            elif t_val == ContentType.VIDEO.value:
                url = getattr(p, "video_url", None) or ""
                print(f"{_YELLOW}🎬 [Video: {url}]{_RESET}")
            elif t_val == ContentType.AUDIO.value:
                print(f"{_YELLOW}🔊 [Audio]{_RESET}")
            elif t_val == ContentType.FILE.value:
                url = (
                    getattr(p, "file_url", None)
                    or getattr(p, "file_id", None)
                    or ""
                )
                print(f"{_YELLOW}📎 [File: {url}]{_RESET}")
        print()

    def _print_error(self, err: str) -> None:
        ts = _ts()
        print(
            f"\n{_RED}{_BOLD}❌ [{ts}] Error{_RESET}\n"
            f"{_RED}{err}{_RESET}\n",
        )

    def _parts_to_text(
        self,
        parts: List[OutgoingContentPart],
        meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Merge content parts to a single text string."""
        text_parts: List[str] = []
        for p in parts:
            t = getattr(p, "type", None)
            t_val = (
                t.value if isinstance(t, ContentType) else str(t) if t else ""
            )
            if t_val == ContentType.TEXT.value:
                text_parts.append(getattr(p, "text", "") or "")
            elif t_val == ContentType.REFUSAL.value:
                text_parts.append(getattr(p, "refusal", "") or "")
        body = "\n".join(text_parts) if text_parts else ""
        prefix = (meta or {}).get("bot_prefix", self.bot_prefix) or ""
        if prefix and body:
            body = prefix + body
        return body

    # ── send (proactive sends / cron) ──────────────────────────────

    async def send(
        self,
        to_handle: str,
        text: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Print to stdout and push to web console store."""
        if not self.enabled:
            return
        ts = _ts()
        prefix = (meta or {}).get("bot_prefix", self.bot_prefix) or ""
        print(
            f"\n{_GREEN}{_BOLD}🤖 [{ts}] Bot → {to_handle}{_RESET}\n"
            f"{prefix}{text}\n",
        )
        # Push to console store for web frontend
        sid = (meta or {}).get("session_id")
        if sid and text.strip():
            try:
                from ..console_push_store import append as push_store_append

                await push_store_append(sid, text.strip())
            except Exception:
                logger.debug("push_store_append not available")

    async def send_content_parts(
        self,
        to_handle: str,
        parts: List[OutgoingContentPart],
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Print parts to stdout and push text to web console store."""
        self._print_parts(parts)
        sid = (meta or {}).get("session_id")
        if sid:
            body = self._parts_to_text(parts, meta)
            if body.strip():
                try:
                    from ..console_push_store import (
                        append as push_store_append,
                    )

                    await push_store_append(sid, body.strip())
                except Exception:
                    logger.debug("push_store_append not available")

    # ── lifecycle ──────────────────────────────────────────────────

    async def start(self) -> None:
        if not self.enabled:
            logger.debug("console channel disabled")
            return
        logger.info("Console channel started")

    async def stop(self) -> None:
        if not self.enabled:
            return
        logger.info("Console channel stopped")
