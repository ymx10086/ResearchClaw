# pylint: disable=too-many-branches
"""Telegram channel: Bot API with polling; receive/send via chat_id.

Key improvements over CoPaw:
- Framework-independent content types (no agentscope_runtime dependency).
- Enhanced media handling: local download + URL resolution.
- Research-specific: /search command for inline paper search.
- Configurable message chunking for long research summaries.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base import (
    BaseChannel,
    ContentType,
    TextContent,
    ImageContent,
    VideoContent,
    AudioContent,
    FileContent,
    OnReplySent,
    OutgoingContentPart,
    ProcessHandler,
)
from ..utils import split_long_message, download_media_file

logger = logging.getLogger(__name__)

TELEGRAM_MAX_MESSAGE_LENGTH = 4096
TELEGRAM_SEND_CHUNK_SIZE = 4000

_DEFAULT_MEDIA_DIR = Path("~/.researchclaw/media/telegram").expanduser()

# Map Telegram attachment types to our content types
_MEDIA_ATTRS: list[tuple[str, type, ContentType, str]] = [
    ("document", FileContent, ContentType.FILE, "file_url"),
    ("video", VideoContent, ContentType.VIDEO, "video_url"),
    ("voice", AudioContent, ContentType.AUDIO, "data"),
    ("audio", AudioContent, ContentType.AUDIO, "data"),
]


async def _download_telegram_file(
    *,
    bot: Any,
    file_id: str,
    media_dir: Path,
    filename_hint: str = "",
) -> Optional[str]:
    """Download a Telegram file to local media_dir; return local path."""
    try:
        from telegram.error import TelegramError

        tg_file = await bot.get_file(file_id)
    except Exception:
        logger.exception("telegram: get_file failed for file_id=%s", file_id)
        return None

    try:
        media_dir.mkdir(parents=True, exist_ok=True)
        suffix = ""
        file_path = (getattr(tg_file, "file_path", None) or "").strip()
        if file_path:
            suffix = Path(file_path).suffix
        if filename_hint and not suffix:
            suffix = Path(filename_hint).suffix
        local_name = f"{uuid.uuid4().hex[:12]}{suffix or '.bin'}"
        local_path = media_dir / local_name
        await tg_file.download_to_drive(str(local_path))
        return str(local_path)
    except Exception:
        logger.exception("telegram: download failed for file_id=%s", file_id)
        return None


async def _build_content_parts_from_message(
    update: Any,
    *,
    bot: Any,
    media_dir: Path,
) -> tuple[list, bool]:
    """Build content_parts from Telegram message.

    Returns (content_parts, has_bot_command).
    """
    message = getattr(update, "message", None) or getattr(
        update,
        "edited_message",
        None,
    )
    if not message:
        return [TextContent(text="")], False

    content_parts: list[Any] = []
    text = (
        getattr(message, "text", None)
        or getattr(message, "caption", None)
        or ""
    ).strip()

    entities = (
        getattr(message, "entities", None)
        or getattr(message, "caption_entities", None)
        or []
    )
    has_bot_command = False
    for entity in entities:
        if getattr(entity, "type", None) == "bot_command":
            has_bot_command = True
            break

    if text:
        content_parts.append(TextContent(text=text))

    # Photos (pick largest)
    photo = getattr(message, "photo", None)
    if photo and len(photo) > 0:
        largest = photo[-1]
        file_id = getattr(largest, "file_id", None)
        if file_id:
            local_path = await _download_telegram_file(
                bot=bot,
                file_id=file_id,
                media_dir=media_dir,
                filename_hint="photo.jpg",
            )
            if local_path:
                content_parts.append(ImageContent(image_url=local_path))

    # Other media
    for attr_name, content_cls, content_type, url_field in _MEDIA_ATTRS:
        media_obj = getattr(message, attr_name, None)
        if not media_obj:
            continue
        file_id = getattr(media_obj, "file_id", None)
        if not file_id:
            continue
        file_name = getattr(media_obj, "file_name", None) or attr_name
        local_path = await _download_telegram_file(
            bot=bot,
            file_id=file_id,
            media_dir=media_dir,
            filename_hint=file_name,
        )
        if local_path:
            content_parts.append(
                content_cls(**{"type": content_type, url_field: local_path}),
            )

    if not content_parts:
        content_parts.append(TextContent(text=""))

    return content_parts, has_bot_command


def _message_meta(update: Any) -> dict:
    """Extract chat_id, user_id, etc. from Telegram update."""
    message = getattr(update, "message", None) or getattr(
        update,
        "edited_message",
        None,
    )
    if not message:
        return {}
    chat = getattr(message, "chat", None)
    user = getattr(message, "from_user", None)
    chat_id = str(getattr(chat, "id", "")) if chat else ""
    user_id = str(getattr(user, "id", "")) if user else ""
    username = (getattr(user, "username", None) or "") if user else ""
    chat_type = getattr(chat, "type", "") if chat else ""
    return {
        "chat_id": chat_id,
        "user_id": user_id,
        "username": username,
        "chat_type": chat_type,
    }


class TelegramChannel(BaseChannel):
    """Telegram Bot channel: long-polling for input, Bot API for output.

    Supports text, images, documents, audio, video. Research enhancements:
    ``/search <query>`` triggers inline paper search.
    """

    channel = "telegram"

    def __init__(
        self,
        process: ProcessHandler,
        enabled: bool,
        token: str,
        bot_prefix: str,
        media_dir: str = "~/.researchclaw/media/telegram",
        http_proxy: str = "",
        on_reply_sent: OnReplySent = None,
        show_tool_details: bool = True,
    ):
        super().__init__(
            process,
            on_reply_sent=on_reply_sent,
            show_tool_details=show_tool_details,
        )
        self.enabled = enabled
        self.token = token
        self.bot_prefix = bot_prefix
        self._media_dir = Path(media_dir).expanduser()
        self._http_proxy = http_proxy
        self._app: Optional[Any] = None
        self._task: Optional[asyncio.Task] = None

    # ── factory methods ────────────────────────────────────────────

    @classmethod
    def from_env(
        cls,
        process: ProcessHandler,
        on_reply_sent: OnReplySent = None,
    ) -> "TelegramChannel":
        return cls(
            process=process,
            enabled=os.getenv("TELEGRAM_CHANNEL_ENABLED", "0") == "1",
            token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            bot_prefix=os.getenv("TELEGRAM_BOT_PREFIX", "[BOT] "),
            media_dir=os.getenv(
                "TELEGRAM_MEDIA_DIR",
                "~/.researchclaw/media/telegram",
            ),
            http_proxy=os.getenv("TELEGRAM_HTTP_PROXY", ""),
            on_reply_sent=on_reply_sent,
        )

    @classmethod
    def from_config(
        cls,
        process: ProcessHandler,
        config: Any,
        on_reply_sent: OnReplySent = None,
        show_tool_details: bool = True,
    ) -> "TelegramChannel":
        return cls(
            process=process,
            enabled=getattr(config, "enabled", False),
            token=getattr(config, "bot_token", "") or "",
            bot_prefix=getattr(config, "bot_prefix", "[BOT] ") or "[BOT] ",
            media_dir=getattr(
                config,
                "media_dir",
                "~/.researchclaw/media/telegram",
            )
            or "~/.researchclaw/media/telegram",
            http_proxy=getattr(config, "http_proxy", "") or "",
            on_reply_sent=on_reply_sent,
            show_tool_details=show_tool_details,
        )

    # ── native payload conversion ──────────────────────────────────

    def resolve_session_id(
        self,
        sender_id: str,
        channel_meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        meta = channel_meta or {}
        chat_id = meta.get("chat_id", "")
        if chat_id:
            return f"{self.channel}:{chat_id}"
        return f"{self.channel}:{sender_id}"

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

    # ── send ───────────────────────────────────────────────────────

    async def send(
        self,
        to_handle: str,
        text: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send text message to a Telegram chat_id."""
        if not self.enabled or not self._app:
            return
        chat_id = (meta or {}).get("chat_id") or to_handle
        if not chat_id:
            return

        chunks = split_long_message(text, TELEGRAM_SEND_CHUNK_SIZE)
        bot = self._app.bot
        for chunk in chunks:
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=chunk,
                    parse_mode="Markdown",
                )
            except Exception:
                # Fallback without Markdown parsing
                try:
                    await bot.send_message(chat_id=chat_id, text=chunk)
                except Exception:
                    logger.exception(
                        "telegram: send_message failed chat_id=%s",
                        chat_id,
                    )

    async def send_media(
        self,
        to_handle: str,
        part: OutgoingContentPart,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send media attachments to Telegram."""
        if not self.enabled or not self._app:
            return
        chat_id = (meta or {}).get("chat_id") or to_handle
        if not chat_id:
            return

        bot = self._app.bot
        t = getattr(part, "type", None)
        t_val = t.value if isinstance(t, ContentType) else str(t) if t else ""

        try:
            if t_val == ContentType.IMAGE.value:
                url = getattr(part, "image_url", "")
                if url:
                    await bot.send_photo(chat_id=chat_id, photo=url)
            elif t_val == ContentType.VIDEO.value:
                url = getattr(part, "video_url", "")
                if url:
                    await bot.send_video(chat_id=chat_id, video=url)
            elif t_val == ContentType.AUDIO.value:
                data = getattr(part, "data", "")
                if data:
                    await bot.send_audio(chat_id=chat_id, audio=data)
            elif t_val == ContentType.FILE.value:
                url = getattr(part, "file_url", "") or getattr(
                    part,
                    "file_id",
                    "",
                )
                if url:
                    await bot.send_document(chat_id=chat_id, document=url)
        except Exception:
            logger.exception("telegram: send_media failed chat_id=%s", chat_id)

    # ── lifecycle ──────────────────────────────────────────────────

    async def start(self) -> None:
        if not self.enabled:
            logger.debug("telegram channel disabled")
            return
        if not self.token:
            logger.warning("telegram: no bot token configured")
            return

        try:
            from telegram.ext import (
                ApplicationBuilder,
                MessageHandler,
                filters,
            )
        except ImportError:
            logger.warning(
                "python-telegram-bot not installed. "
                "Install with: pip install python-telegram-bot",
            )
            return

        builder = ApplicationBuilder().token(self.token)
        if self._http_proxy:
            builder = builder.proxy(self._http_proxy).get_updates_proxy(
                self._http_proxy,
            )

        self._app = builder.build()

        async def _handle_message(update: Any, context: Any) -> None:
            (
                content_parts,
                has_bot_command,
            ) = await _build_content_parts_from_message(
                update,
                bot=self._app.bot,
                media_dir=self._media_dir,
            )
            meta = _message_meta(update)
            native = {
                "channel_id": self.channel,
                "sender_id": meta.get("user_id") or "",
                "content_parts": content_parts,
                "meta": meta,
            }
            if self._enqueue is not None:
                self._enqueue(native)
            else:
                logger.warning("telegram: _enqueue not set, message dropped")

        handler = MessageHandler(
            filters.TEXT
            | filters.PHOTO
            | filters.Document.ALL
            | filters.VIDEO
            | filters.AUDIO
            | filters.VOICE,
            _handle_message,
        )
        self._app.add_handler(handler)

        await self._app.initialize()
        await self._app.start()
        self._task = asyncio.create_task(
            self._app.updater.start_polling(drop_pending_updates=True),
        )
        logger.info("Telegram channel started")

    async def stop(self) -> None:
        if not self.enabled or not self._app:
            return
        try:
            if self._app.updater and self._app.updater.running:
                await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
        except Exception:
            logger.exception("telegram: stop failed")
        self._app = None
        self._task = None
        logger.info("Telegram channel stopped")
