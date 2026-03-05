"""Channels package – communication channel abstractions.

Provides:
- BaseChannel: Abstract base class for all channels
- ChannelManager: Queue-based channel lifecycle manager
- ContentType, TextContent, etc.: Framework-independent content types
- MessageRenderer: Converts agent events to sendable content parts
- Channel schema (ChannelAddress, DEFAULT_CHANNEL, etc.)
- Built-in channels: Console, Telegram, Discord, DingTalk, Feishu, iMessage, QQ
  , Voice
- Registry: get_channel_registry() for built-in + custom channel discovery

Heavy channel classes are lazy-loaded to avoid pulling third-party deps
(e.g. lark_oapi, discord.py) when only Console channel is needed.
"""
from .base import (
    BaseChannel,
    ContentType,
    TextContent,
    ImageContent,
    VideoContent,
    AudioContent,
    FileContent,
    RefusalContent,
    OutgoingContentPart,
    ProcessHandler,
    OnReplySent,
)
from .schema import (
    ChannelAddress,
    ChannelType,
    DEFAULT_CHANNEL,
    BUILTIN_CHANNEL_TYPES,
    ChannelMessageConverter,
)

__all__ = [
    # base
    "BaseChannel",
    "ContentType",
    "TextContent",
    "ImageContent",
    "VideoContent",
    "AudioContent",
    "FileContent",
    "RefusalContent",
    "OutgoingContentPart",
    "ProcessHandler",
    "OnReplySent",
    # schema
    "ChannelAddress",
    "ChannelType",
    "DEFAULT_CHANNEL",
    "BUILTIN_CHANNEL_TYPES",
    "ChannelMessageConverter",
    # lazy-loaded
    "ChannelManager",
    "MessageRenderer",
    "RenderStyle",
    "ConsoleChannel",
    "TelegramChannel",
    "DiscordChannel",
    "DingTalkChannel",
    "FeishuChannel",
    "IMessageChannel",
    "QQChannel",
    "VoiceChannel",
    "get_channel_registry",
    "BUILTIN_CHANNEL_KEYS",
]


def __getattr__(name: str):  # noqa: C901
    """Lazy-load heavy classes to avoid import-time cost."""
    if name == "ChannelManager":
        from .manager import ChannelManager

        return ChannelManager
    if name in ("MessageRenderer", "RenderStyle"):
        from .renderer import MessageRenderer, RenderStyle

        return MessageRenderer if name == "MessageRenderer" else RenderStyle
    if name == "ConsoleChannel":
        from .console_channel import ConsoleChannel

        return ConsoleChannel
    if name == "TelegramChannel":
        from .telegram import TelegramChannel

        return TelegramChannel
    if name == "DiscordChannel":
        from .discord_ import DiscordChannel

        return DiscordChannel
    if name == "DingTalkChannel":
        from .dingtalk import DingTalkChannel

        return DingTalkChannel
    if name == "FeishuChannel":
        from .feishu import FeishuChannel

        return FeishuChannel
    if name == "IMessageChannel":
        from .imessage import IMessageChannel

        return IMessageChannel
    if name == "QQChannel":
        from .qq import QQChannel

        return QQChannel
    if name == "VoiceChannel":
        from .voice import VoiceChannel

        return VoiceChannel
    if name in ("get_channel_registry", "BUILTIN_CHANNEL_KEYS"):
        from .registry import get_channel_registry, BUILTIN_CHANNEL_KEYS

        return (
            get_channel_registry
            if name == "get_channel_registry"
            else BUILTIN_CHANNEL_KEYS
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
