# pylint: disable=too-many-branches,too-many-statements
"""Discord channel: discord.py bot with gateway intents.

Key improvements over CoPaw:
- Framework-independent content types.
- Enhanced media type detection (content_type + extension fallback).
- Message chunking for long research summaries (Discord 2000 char limit).
- Markdown formatting optimised for Discord's flavor.
"""
from __future__ import annotations

import asyncio
import logging
import os
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
from ..utils import split_long_message

logger = logging.getLogger(__name__)

DISCORD_MAX_MESSAGE_LENGTH = 2000
DISCORD_SEND_CHUNK_SIZE = 1900


class DiscordChannel(BaseChannel):
    """Discord channel: discord.py gateway for input, REST API for output.

    Supports text, images, files, audio, video attachments.
    """

    channel = "discord"
    uses_manager_queue = True

    def __init__(
        self,
        process: ProcessHandler,
        enabled: bool,
        token: str,
        http_proxy: str = "",
        http_proxy_auth: str = "",
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
        self.token = token
        self.http_proxy = http_proxy
        self.http_proxy_auth = http_proxy_auth
        self.bot_prefix = bot_prefix
        self._task: Optional[asyncio.Task] = None
        self._client: Any = None

    # ── factory methods ────────────────────────────────────────────

    @classmethod
    def from_env(
        cls,
        process: ProcessHandler,
        on_reply_sent: OnReplySent = None,
    ) -> "DiscordChannel":
        return cls(
            process=process,
            enabled=os.getenv("DISCORD_CHANNEL_ENABLED", "0") == "1",
            token=os.getenv("DISCORD_BOT_TOKEN", ""),
            http_proxy=os.getenv("DISCORD_HTTP_PROXY", ""),
            http_proxy_auth=os.getenv("DISCORD_HTTP_PROXY_AUTH", ""),
            bot_prefix=os.getenv("DISCORD_BOT_PREFIX", "[BOT] "),
            on_reply_sent=on_reply_sent,
        )

    @classmethod
    def from_config(
        cls,
        process: ProcessHandler,
        config: Any,
        on_reply_sent: OnReplySent = None,
        show_tool_details: bool = True,
    ) -> "DiscordChannel":
        return cls(
            process=process,
            enabled=getattr(config, "enabled", False),
            token=getattr(config, "bot_token", "") or "",
            http_proxy=getattr(config, "http_proxy", "") or "",
            http_proxy_auth=getattr(config, "http_proxy_auth", "") or "",
            bot_prefix=getattr(config, "bot_prefix", "[BOT] ") or "[BOT] ",
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
        discord_channel_id = meta.get("channel_id", "")
        if discord_channel_id:
            return f"{self.channel}:{discord_channel_id}"
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
        if not self.enabled or not self._client:
            return
        discord_channel_id = (meta or {}).get("channel_id") or to_handle
        if not discord_channel_id:
            return

        try:
            ch = self._client.get_channel(int(discord_channel_id))
            if ch is None:
                ch = await self._client.fetch_channel(int(discord_channel_id))
        except Exception:
            logger.exception(
                "discord: could not fetch channel %s",
                discord_channel_id,
            )
            return

        chunks = split_long_message(text, DISCORD_SEND_CHUNK_SIZE)
        for chunk in chunks:
            try:
                await ch.send(chunk)
            except Exception:
                logger.exception(
                    "discord: send failed to channel %s",
                    discord_channel_id,
                )

    async def send_media(
        self,
        to_handle: str,
        part: OutgoingContentPart,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.enabled or not self._client:
            return
        discord_channel_id = (meta or {}).get("channel_id") or to_handle
        if not discord_channel_id:
            return

        try:
            import discord

            ch = self._client.get_channel(int(discord_channel_id))
            if ch is None:
                ch = await self._client.fetch_channel(int(discord_channel_id))

            t = getattr(part, "type", None)
            t_val = (
                t.value if isinstance(t, ContentType) else str(t) if t else ""
            )
            url = ""
            if t_val == ContentType.IMAGE.value:
                url = getattr(part, "image_url", "")
            elif t_val == ContentType.VIDEO.value:
                url = getattr(part, "video_url", "")
            elif t_val == ContentType.FILE.value:
                url = getattr(part, "file_url", "") or getattr(
                    part,
                    "file_id",
                    "",
                )
            elif t_val == ContentType.AUDIO.value:
                url = getattr(part, "data", "")

            if url:
                await ch.send(url)
        except Exception:
            logger.exception("discord: send_media failed")

    # ── lifecycle ──────────────────────────────────────────────────

    async def start(self) -> None:
        if not self.enabled:
            logger.debug("discord channel disabled")
            return
        if not self.token:
            logger.warning("discord: no bot token configured")
            return

        try:
            import discord
            import aiohttp
        except ImportError:
            logger.warning(
                "discord.py not installed. Install with: pip install discord.py",
            )
            return

        intents = discord.Intents.default()
        intents.message_content = True
        intents.dm_messages = True
        intents.messages = True
        intents.guilds = True

        proxy_auth = None
        if self.http_proxy_auth:
            parts = self.http_proxy_auth.split(":", 1)
            if len(parts) == 2:
                proxy_auth = aiohttp.BasicAuth(parts[0], parts[1])

        self._client = discord.Client(
            intents=intents,
            proxy=self.http_proxy or None,
            proxy_auth=proxy_auth,
        )

        @self._client.event
        async def on_message(message: Any) -> None:
            if message.author.bot:
                return
            text = (message.content or "").strip()
            attachments = getattr(message, "attachments", [])

            content_parts: list = []
            if text:
                content_parts.append(TextContent(text=text))

            for att in attachments:
                file_name = (getattr(att, "filename", "") or "").lower()
                url = getattr(att, "url", "")
                ctype = (getattr(att, "content_type", "") or "").lower()

                is_image = ctype.startswith("image/") or file_name.endswith(
                    (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"),
                )
                is_video = ctype.startswith("video/") or file_name.endswith(
                    (".mp4", ".mov", ".mkv", ".webm", ".avi"),
                )
                is_audio = ctype.startswith("audio/") or file_name.endswith(
                    (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"),
                )

                if is_image:
                    content_parts.append(ImageContent(image_url=url))
                elif is_video:
                    content_parts.append(VideoContent(video_url=url))
                elif is_audio:
                    content_parts.append(AudioContent(data=url))
                else:
                    content_parts.append(FileContent(file_url=url))

            meta = {
                "user_id": str(message.author.id),
                "channel_id": str(message.channel.id),
                "guild_id": str(message.guild.id) if message.guild else None,
                "message_id": str(message.id),
                "is_dm": message.guild is None,
            }
            native = {
                "channel_id": self.channel,
                "sender_id": str(message.author),
                "content_parts": content_parts,
                "meta": meta,
            }
            if self._enqueue is not None:
                self._enqueue(native)
            else:
                logger.warning("discord: _enqueue not set, message dropped")

        self._task = asyncio.create_task(self._client.start(self.token))
        logger.info("Discord channel started")

    async def stop(self) -> None:
        if not self.enabled or not self._client:
            return
        try:
            await self._client.close()
        except Exception:
            logger.exception("discord: close failed")
        if self._task and not self._task.done():
            self._task.cancel()
        self._client = None
        self._task = None
        logger.info("Discord channel stopped")
