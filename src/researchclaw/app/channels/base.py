"""Base Channel – unified async channel abstraction.

All channels inherit from :class:`BaseChannel`. A channel converts between
*native* platform payloads and internal agent requests, manages debouncing,
content rendering, and lifecycle (start/stop).

Key improvements over CoPaw:
- **Framework-independent**: no hard dependency on ``agentscope_runtime``
  types – lightweight dataclasses used as content parts.
- **Enhanced debouncing**: both *no-text* debounce (buffer images until text
  arrives) and configurable *time* debounce (merge rapid-fire messages).
- **Pluggable renderer**: ``MessageRenderer`` can be swapped per channel.
- **Hook-based extensibility**: ``_before_consume_process``,
  ``on_event_message_completed``, ``on_event_response``, ``_on_consume_error``
  allow subclasses to customise without overriding the full consume loop.
"""
from __future__ import annotations

import asyncio
import logging
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    List,
    Optional,
    Union,
    TYPE_CHECKING,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lightweight content-part types (framework-independent)
# ---------------------------------------------------------------------------


class ContentType(str, Enum):
    """Unified content type identifiers."""

    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"
    REFUSAL = "refusal"


@dataclass
class TextContent:
    type: ContentType = ContentType.TEXT
    text: str = ""


@dataclass
class ImageContent:
    type: ContentType = ContentType.IMAGE
    image_url: str = ""


@dataclass
class VideoContent:
    type: ContentType = ContentType.VIDEO
    video_url: str = ""


@dataclass
class AudioContent:
    type: ContentType = ContentType.AUDIO
    data: str = ""


@dataclass
class FileContent:
    type: ContentType = ContentType.FILE
    file_url: str = ""
    file_id: str = ""


@dataclass
class RefusalContent:
    type: ContentType = ContentType.REFUSAL
    refusal: str = ""


OutgoingContentPart = Union[
    TextContent,
    ImageContent,
    VideoContent,
    AudioContent,
    FileContent,
    RefusalContent,
]

# ---------------------------------------------------------------------------
# Callback type aliases
# ---------------------------------------------------------------------------

# Optional callback to enqueue payload (set by ChannelManager)
EnqueueCallback = Optional[Callable[[Any], None]]

# Called when a user-originated reply was sent (channel_name, user_id, session_id)
OnReplySent = Optional[Callable[[str, str, str], None]]

# process: accepts a request, yields events (SSE-style streaming)
ProcessHandler = Callable[[Any], AsyncIterator[Any]]


class RunStatus:
    """Lightweight run-status sentinel (avoids agentscope dependency)."""

    Completed = "completed"
    InProgress = "in_progress"
    Failed = "failed"


# Try to import agentscope_runtime types for compatibility; fall back silently.
try:
    from agentscope_runtime.engine.schemas.agent_schemas import (
        ContentType as _ASContentType,
        TextContent as _ASTextContent,
        ImageContent as _ASImageContent,
        VideoContent as _ASVideoContent,
        AudioContent as _ASAudioContent,
        FileContent as _ASFileContent,
        RefusalContent as _ASRefusalContent,
        RunStatus as _ASRunStatus,
        MessageType as _ASMessageType,
    )

    _HAS_AGENTSCOPE = True
except ImportError:
    _HAS_AGENTSCOPE = False

# ---------------------------------------------------------------------------
# RenderStyle & MessageRenderer (inline; avoids early import of renderer.py)
# ---------------------------------------------------------------------------

if TYPE_CHECKING:
    from .renderer import MessageRenderer, RenderStyle


@dataclass
class _DefaultRenderStyle:
    show_tool_details: bool = True
    filter_tool_messages: bool = False
    show_emoji: bool = True
    max_tool_output_len: int = 300


# ---------------------------------------------------------------------------
# BaseChannel
# ---------------------------------------------------------------------------


class BaseChannel(ABC):
    """Base for all channels.

    The queue and consumer loop live in :class:`ChannelManager`; the channel
    defines how to consume via :meth:`consume_one`.
    """

    channel: str = ""

    # If True, manager creates a queue and consumer loop for this channel.
    uses_manager_queue: bool = True

    def __init__(
        self,
        process: ProcessHandler,
        on_reply_sent: OnReplySent = None,
        show_tool_details: bool = True,
        filter_tool_messages: bool = False,
    ):
        self._process = process
        self._on_reply_sent = on_reply_sent
        self._show_tool_details = show_tool_details
        self._filter_tool_messages = filter_tool_messages

        # Enqueue callback – set by ChannelManager.start_all()
        self._enqueue: EnqueueCallback = None

        # Pluggable renderer (lazy-initialised)
        self._renderer: Optional[Any] = None
        self._render_style = _DefaultRenderStyle(
            show_tool_details=show_tool_details,
            filter_tool_messages=filter_tool_messages,
        )

        # Optional shared aiohttp.ClientSession
        self._http: Optional[Any] = None

        # No-text debounce buffer: session_id -> list of content parts
        self._pending_content_by_session: Dict[str, List[Any]] = {}

        # Time debounce (> 0 to enable; key = get_debounce_key(payload))
        self._debounce_seconds: float = 0.0
        self._debounce_pending: Dict[str, List[Any]] = {}
        self._debounce_timers: Dict[str, asyncio.Task] = {}

    # ── renderer (lazy) ────────────────────────────────────────────

    def _get_renderer(self) -> Any:
        """Return (and cache) the MessageRenderer instance."""
        if self._renderer is None:
            from .renderer import MessageRenderer  # noqa: F811
            from .renderer import RenderStyle  # noqa: F811

            style = RenderStyle(
                show_tool_details=self._show_tool_details,
                filter_tool_messages=self._filter_tool_messages,
                show_emoji=getattr(self._render_style, "show_emoji", True),
                max_tool_output_len=getattr(
                    self._render_style,
                    "max_tool_output_len",
                    300,
                ),
            )
            self._renderer = MessageRenderer(style)
        return self._renderer

    # ── native payload detection ───────────────────────────────────

    def _is_native_payload(self, payload: Any) -> bool:
        """True if payload is a native dict that can be time-debounced."""
        return isinstance(payload, dict) and "content_parts" in payload

    # ── debounce key ───────────────────────────────────────────────

    def get_debounce_key(self, payload: Any) -> str:
        """Key for time debounce (same key = same conversation).

        Override for channel-specific keys (e.g. short conversation_id).
        """
        if isinstance(payload, dict):
            meta = payload.get("meta") or {}
            return (
                payload.get("session_id")
                or meta.get("conversation_id")
                or payload.get("sender_id")
                or ""
            )
        return getattr(payload, "session_id", "") or ""

    # ── merge helpers ──────────────────────────────────────────────

    def merge_native_items(self, items: List[Any]) -> Any:
        """Merge multiple native payloads into one.

        Default: concat content_parts, merge meta keys. Override for
        channel-specific merge logic.
        """
        if not items:
            return None
        first = items[0] if isinstance(items[0], dict) else {}
        merged_parts: List[Any] = []
        merged_meta: Dict[str, Any] = dict(first.get("meta") or {})
        for it in items:
            p = it if isinstance(it, dict) else {}
            merged_parts.extend(p.get("content_parts") or [])
            m = p.get("meta") or {}
            for k in (
                "reply_future",
                "reply_loop",
                "incoming_message",
                "conversation_id",
            ):
                if k in m:
                    merged_meta[k] = m[k]
        return {
            "channel_id": first.get("channel_id") or self.channel,
            "sender_id": first.get("sender_id") or "",
            "content_parts": merged_parts,
            "meta": merged_meta,
        }

    def merge_requests(self, requests: List[Any]) -> Any:
        """Merge multiple requests (same session) into one.

        Concatenates content from all, keeps first request's meta/session.
        """
        if not requests:
            return None
        first = requests[0]
        if len(requests) == 1:
            return first
        all_contents: List[Any] = []
        for req in requests:
            inp = getattr(req, "input", None) or []
            if inp and hasattr(inp[0], "content"):
                all_contents.extend(getattr(inp[0], "content") or [])
        if not all_contents:
            return first
        msg = first.input[0]
        if hasattr(msg, "model_copy"):
            new_msg = msg.model_copy(update={"content": all_contents})
        else:
            new_msg = msg
            setattr(new_msg, "content", all_contents)
        if hasattr(first, "model_copy"):
            return first.model_copy(update={"input": [new_msg]})
        first.input[0] = new_msg
        return first

    # ── debounce hook ──────────────────────────────────────────────

    def _on_debounce_buffer_append(
        self,
        key: str,
        payload: Any,
        existing_items: List[Any],
    ) -> None:
        """Hook when appending to time-debounce buffer. Override e.g. to
        unblock previous reply_future."""

    # ── content inspection ─────────────────────────────────────────

    def _content_has_text(self, contents: List[Any]) -> bool:
        """True if contents has actionable text/media payload."""
        if not contents:
            return False
        for c in contents:
            t = getattr(c, "type", None)
            # Accept both our ContentType enum and string values
            t_val = (
                t.value if isinstance(t, ContentType) else str(t) if t else ""
            )
            if t_val == ContentType.TEXT.value:
                if (getattr(c, "text", None) or "").strip():
                    return True
            if t_val == ContentType.REFUSAL.value:
                if (getattr(c, "refusal", None) or "").strip():
                    return True
            if t_val in (
                ContentType.IMAGE.value,
                ContentType.VIDEO.value,
                ContentType.AUDIO.value,
                ContentType.FILE.value,
            ):
                return True
        return False

    def _apply_no_text_debounce(
        self,
        session_id: str,
        content_parts: List[Any],
    ) -> tuple:
        """Debounce: if no text, buffer and return ``(False, [])``.

        When text arrives, prepend buffered content and return
        ``(True, merged)``.
        """
        if not self._content_has_text(content_parts):
            self._pending_content_by_session.setdefault(
                session_id,
                [],
            ).extend(content_parts)
            logger.debug(
                "channel debounce: no text, buffered session_id=%s",
                session_id[:24] if session_id else "",
            )
            return (False, [])
        pending = self._pending_content_by_session.pop(session_id, [])
        merged = pending + list(content_parts)
        return (True, merged)

    # ── enqueue callback ───────────────────────────────────────────

    def set_enqueue(self, cb: EnqueueCallback) -> None:
        """Set enqueue callback (called by ChannelManager)."""
        self._enqueue = cb

    # ── factory methods (subclasses override) ──────────────────────

    @classmethod
    def from_env(
        cls,
        process: ProcessHandler,
        on_reply_sent: OnReplySent = None,
    ) -> "BaseChannel":
        raise NotImplementedError

    @classmethod
    def from_config(
        cls,
        process: ProcessHandler,
        config: Any,
        on_reply_sent: OnReplySent = None,
        show_tool_details: bool = True,
        filter_tool_messages: bool = False,
    ) -> "BaseChannel":
        raise NotImplementedError

    # ── session resolution ─────────────────────────────────────────

    def resolve_session_id(
        self,
        sender_id: str,
        channel_meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Map sender and optional channel meta to session_id.

        Override for channel-specific keys (e.g. short suffix of
        conversation_id).
        """
        return f"{self.channel}:{sender_id}"

    # ── request building ───────────────────────────────────────────

    def build_agent_request_from_user_content(
        self,
        channel_id: str,
        sender_id: str,
        session_id: str,
        content_parts: List[Any],
        channel_meta: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Build an agent request from content parts.

        If ``agentscope_runtime`` is available, creates a proper
        ``AgentRequest``; otherwise returns a plain dict.
        """
        if not content_parts:
            content_parts = [TextContent(text="")]

        if _HAS_AGENTSCOPE:
            from agentscope_runtime.engine.schemas.agent_schemas import (
                AgentRequest,
                Message,
                Role,
            )

            msg = Message(
                type=_ASMessageType.MESSAGE,
                role=Role.USER,
                content=content_parts,
            )
            return AgentRequest(
                session_id=session_id,
                user_id=sender_id,
                input=[msg],
                channel=channel_id,
            )

        # Framework-independent fallback
        return {
            "session_id": session_id,
            "user_id": sender_id,
            "channel": channel_id,
            "input": [{"role": "user", "content": content_parts}],
        }

    def build_agent_request_from_native(self, native_payload: Any) -> Any:
        """Convert channel-native payload to an agent request.

        Subclasses must implement: parse native -> content_parts, then call
        :meth:`build_agent_request_from_user_content`.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement "
            "build_agent_request_from_native(native_payload)",
        )

    # ── request helpers ────────────────────────────────────────────

    def _payload_to_request(self, payload: Any) -> Any:
        """Convert queue payload to a request.

        If payload looks like a request (has ``session_id`` and ``input``),
        return as-is; otherwise delegate to
        :meth:`build_agent_request_from_native`.
        """
        if payload is None:
            raise ValueError("payload is None")
        if hasattr(payload, "session_id") and hasattr(payload, "input"):
            return payload
        if (
            isinstance(payload, dict)
            and "session_id" in payload
            and "input" in payload
        ):
            return payload
        return self.build_agent_request_from_native(payload)

    def get_to_handle_from_request(self, request: Any) -> str:
        """Resolve send target (to_handle) from request. Default: user_id."""
        if isinstance(request, dict):
            return request.get("user_id", "") or ""
        return getattr(request, "user_id", "") or ""

    def get_on_reply_sent_args(self, request: Any, to_handle: str) -> tuple:
        """Args for ``_on_reply_sent(channel, *args)``.

        Default: ``(to_handle, session_id)``.
        """
        if isinstance(request, dict):
            session_id = (
                request.get("session_id", "") or f"{self.channel}:{to_handle}"
            )
        else:
            session_id = (
                getattr(request, "session_id", "")
                or f"{self.channel}:{to_handle}"
            )
        return (to_handle, session_id)

    # ── webhook / token refresh ────────────────────────────────────

    async def refresh_webhook_or_token(self) -> None:
        """Optional: refresh webhook URL or API token. Default no-op."""

    # ── consume pipeline ───────────────────────────────────────────

    async def consume_one(self, payload: Any) -> None:
        """Process one payload from the manager-owned queue.

        If ``_debounce_seconds > 0`` and payload is native, buffer and
        flush after delay; otherwise call :meth:`_consume_one_request`.
        """
        if self._debounce_seconds > 0 and self._is_native_payload(payload):
            key = self.get_debounce_key(payload)
            if key in self._debounce_pending and self._debounce_pending[key]:
                self._on_debounce_buffer_append(
                    key,
                    payload,
                    self._debounce_pending[key],
                )
            self._debounce_pending.setdefault(key, []).append(payload)
            old = self._debounce_timers.pop(key, None)
            if old and not old.done():
                old.cancel()

            async def flush(k: str) -> None:
                await asyncio.sleep(self._debounce_seconds)
                items = self._debounce_pending.pop(k, [])
                self._debounce_timers.pop(k, None)
                if not items:
                    return
                merged = self.merge_native_items(items)
                if merged:
                    await self._consume_one_request(merged)

            self._debounce_timers[key] = asyncio.create_task(flush(key))
            return
        await self._consume_one_request(payload)

    async def _consume_one_request(self, payload: Any) -> None:
        """Convert payload to request, apply no-text debounce, run process,
        send messages, handle errors and on_reply_sent.
        """
        request = self._payload_to_request(payload)

        # Merge meta from dict payload (preserves session_webhook etc.)
        if isinstance(payload, dict):
            meta_from_payload = dict(payload.get("meta") or {})
            if payload.get("session_webhook"):
                meta_from_payload["session_webhook"] = payload[
                    "session_webhook"
                ]
            if hasattr(request, "channel_meta"):
                request.channel_meta = meta_from_payload
            elif isinstance(request, dict):
                request.setdefault("channel_meta", meta_from_payload)

        # No-text debounce
        session_id = (
            request.get("session_id", "")
            if isinstance(request, dict)
            else getattr(request, "session_id", "")
        ) or ""

        inp = (
            request.get("input")
            if isinstance(request, dict)
            else getattr(request, "input", None)
        )
        if inp:
            first_msg = inp[0] if isinstance(inp, list) else inp
            contents = (
                first_msg.get("content")
                if isinstance(first_msg, dict)
                else getattr(first_msg, "content", None)
            ) or []
            contents = list(contents)
            should_process, merged = self._apply_no_text_debounce(
                session_id,
                contents,
            )
            if not should_process:
                return
            if merged:
                if isinstance(first_msg, dict):
                    first_msg["content"] = merged
                elif hasattr(first_msg, "model_copy"):
                    new_msg = first_msg.model_copy(update={"content": merged})
                    if isinstance(request, dict):
                        request["input"][0] = new_msg
                    else:
                        request.input[0] = new_msg
                elif hasattr(first_msg, "content"):
                    first_msg.content = merged

        to_handle = self.get_to_handle_from_request(request)
        await self._before_consume_process(request)

        # Build send_meta
        if isinstance(payload, dict):
            send_meta = dict(payload.get("meta") or {})
            if payload.get("session_webhook"):
                send_meta["session_webhook"] = payload["session_webhook"]
        else:
            send_meta = (
                getattr(request, "channel_meta", None)
                or (
                    request.get("channel_meta")
                    if isinstance(request, dict)
                    else None
                )
                or {}
            )
        bot_prefix = getattr(self, "bot_prefix", None) or getattr(
            self,
            "_bot_prefix",
            "",
        )
        if bot_prefix and "bot_prefix" not in send_meta:
            send_meta = {**send_meta, "bot_prefix": bot_prefix}

        await self._run_process_loop(request, to_handle, send_meta)

    # ── hooks ──────────────────────────────────────────────────────

    async def _before_consume_process(self, request: Any) -> None:
        """Hook before running _process. Override e.g. to save receive_id."""

    async def on_event_message_completed(
        self,
        request: Any,
        to_handle: str,
        event: Any,
        send_meta: Dict[str, Any],
    ) -> None:
        """Hook: one message event completed. Default: send_message_content."""
        await self.send_message_content(to_handle, event, send_meta)

    async def on_event_response(self, request: Any, event: Any) -> None:
        """Hook: response event received. Default: no-op."""

    async def _on_consume_error(
        self,
        request: Any,
        to_handle: str,
        err_text: str,
    ) -> None:
        """Called on consume error. Default: send err_text as text content."""
        await self.send_content_parts(
            to_handle,
            [TextContent(text=err_text)],
            (
                getattr(request, "channel_meta", None)
                if not isinstance(request, dict)
                else request.get("channel_meta")
            )
            or {},
        )

    # ── process loop ───────────────────────────────────────────────

    async def _run_process_loop(
        self,
        request: Any,
        to_handle: str,
        send_meta: Dict[str, Any],
    ) -> None:
        """Run _process and send events.

        Override for channel-specific loops (e.g. DingTalk webhook sends).
        """
        bot_prefix = send_meta.get("bot_prefix", "") or getattr(
            self,
            "bot_prefix",
            "",
        )
        last_response = None
        try:
            async for event in self._process(request):
                obj = getattr(event, "object", None)
                status = getattr(event, "status", None)
                # Support both RunStatus objects and string values
                status_val = (
                    (status.value if hasattr(status, "value") else str(status))
                    if status
                    else ""
                )
                completed = status_val in (
                    RunStatus.Completed,
                    "completed",
                )
                if obj == "message" and completed:
                    await self.on_event_message_completed(
                        request,
                        to_handle,
                        event,
                        send_meta,
                    )
                elif obj == "response":
                    last_response = event
                    await self.on_event_response(request, event)

            if last_response and getattr(last_response, "error", None):
                err = getattr(
                    last_response.error,
                    "message",
                    str(last_response.error),
                )
                err_text = (bot_prefix or "") + f"Error: {err}"
                await self._on_consume_error(request, to_handle, err_text)

            if self._on_reply_sent:
                args = self.get_on_reply_sent_args(request, to_handle)
                self._on_reply_sent(self.channel, *args)
        except Exception:
            logger.exception("channel consume_one failed")
            await self._on_consume_error(
                request,
                to_handle,
                "An error occurred while processing your request.",
            )

    # ── message rendering ──────────────────────────────────────────

    def _message_to_content_parts(
        self,
        message: Any,
    ) -> List[OutgoingContentPart]:
        """Convert a message event into sendable content parts.

        Delegates to the pluggable renderer.
        """
        renderer = self._get_renderer()
        return renderer.message_to_parts(message)

    async def send_message_content(
        self,
        to_handle: str,
        message: Any,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send all content of a message (text, image, video, etc.)."""
        parts = self._message_to_content_parts(message)
        if not parts:
            logger.debug(
                "send_message_content: no parts for to_handle=%s, skip",
                to_handle,
            )
            return
        logger.debug(
            "send_message_content: to_handle=%s parts=%d types=%s",
            to_handle,
            len(parts),
            [getattr(p, "type", None) for p in parts],
        )
        await self.send_content_parts(to_handle, parts, meta)

    # ── send methods ───────────────────────────────────────────────

    async def send_content_parts(
        self,
        to_handle: str,
        parts: List[OutgoingContentPart],
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send a list of content parts.

        Default: merge text/refusal into one text body, append media URLs
        as fallback, send one message; call :meth:`send_media` for each
        media part.
        """
        text_parts: List[str] = []
        media_parts: List[OutgoingContentPart] = []
        for p in parts:
            t = getattr(p, "type", None)
            t_val = (
                t.value if isinstance(t, ContentType) else str(t) if t else ""
            )
            if t_val == ContentType.TEXT.value and getattr(p, "text", None):
                text_parts.append(p.text)
            elif t_val == ContentType.REFUSAL.value and getattr(
                p,
                "refusal",
                None,
            ):
                text_parts.append(p.refusal)
            elif t_val in (
                ContentType.IMAGE.value,
                ContentType.VIDEO.value,
                ContentType.AUDIO.value,
                ContentType.FILE.value,
            ):
                media_parts.append(p)

        body = "\n".join(text_parts) if text_parts else ""
        prefix = (meta or {}).get("bot_prefix", "") or ""
        if prefix and body:
            body = prefix + body

        for m in media_parts:
            t_val = (
                m.type.value
                if isinstance(m.type, ContentType)
                else str(m.type)
                if m.type
                else ""
            )
            if t_val == ContentType.IMAGE.value and getattr(
                m,
                "image_url",
                None,
            ):
                body += f"\n[Image: {m.image_url}]"
            elif t_val == ContentType.VIDEO.value and getattr(
                m,
                "video_url",
                None,
            ):
                body += f"\n[Video: {m.video_url}]"
            elif t_val == ContentType.FILE.value and (
                getattr(m, "file_url", None) or getattr(m, "file_id", None)
            ):
                body += f"\n[File: {getattr(m, 'file_url', '') or getattr(m, 'file_id', '')}]"
            elif t_val == ContentType.AUDIO.value and getattr(m, "data", None):
                body += "\n[Audio]"

        if body.strip():
            await self.send(to_handle, body.strip(), meta)
        for m in media_parts:
            await self.send_media(to_handle, m, meta)

    async def send_media(
        self,
        to_handle: str,
        part: OutgoingContentPart,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send a single media part. Default: no-op (appended to text).

        Subclasses override to send real attachments.
        """

    async def send_response(
        self,
        to_handle: str,
        response: Any,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Convert a full response to this channel's reply and send."""
        text = self._response_to_text(response)
        await self.send(to_handle, text or "", meta)

    def _response_to_text(self, response: Any) -> str:
        """Extract reply text from a response object."""
        output = getattr(response, "output", None)
        if not output:
            if isinstance(response, dict):
                output = response.get("output")
            if not output:
                return ""

        last_msg = output[-1] if isinstance(output, list) else output
        content = (
            last_msg.get("content")
            if isinstance(last_msg, dict)
            else getattr(last_msg, "content", None)
        )
        if not content:
            return ""

        parts = []
        for c in content if isinstance(content, list) else [content]:
            t = getattr(c, "type", None)
            t_val = (
                t.value if isinstance(t, ContentType) else str(t) if t else ""
            )
            if t_val == ContentType.TEXT.value and getattr(c, "text", None):
                parts.append(c.text)
            elif t_val == ContentType.REFUSAL.value and getattr(
                c,
                "refusal",
                None,
            ):
                parts.append(c.refusal)
        return "".join(parts)

    # ── clone ──────────────────────────────────────────────────────

    def clone(self, config: Any) -> "BaseChannel":
        """Clone a new channel with updated config."""
        return self.__class__.from_config(
            process=self._process,
            config=config,
            on_reply_sent=self._on_reply_sent,
            show_tool_details=self._show_tool_details,
            filter_tool_messages=getattr(
                self,
                "_filter_tool_messages",
                False,
            ),
        )

    # ── lifecycle ──────────────────────────────────────────────────

    async def start(self) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        raise NotImplementedError

    async def send(
        self,
        to_handle: str,
        text: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Subclass: send one text message to to_handle."""
        raise NotImplementedError

    # ── cron / proactive send helpers ──────────────────────────────

    def to_handle_from_target(self, *, user_id: str, session_id: str) -> str:
        """Map dispatch target to channel-specific to_handle.

        Default: use user_id.
        """
        return user_id

    async def send_event(
        self,
        *,
        user_id: str,
        session_id: str,
        event: Any,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send a runner Event to this channel (non-stream).

        Only sends when event is a completed message.
        """
        obj = getattr(event, "object", None)
        status = getattr(event, "status", None)
        status_val = (
            (status.value if hasattr(status, "value") else str(status))
            if status
            else ""
        )

        if obj != "message" or status_val not in (
            RunStatus.Completed,
            "completed",
        ):
            return

        to_handle = self.to_handle_from_target(
            user_id=user_id,
            session_id=session_id,
        )
        await self.send_message_content(to_handle, event, meta)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} channel={self.channel}>"
