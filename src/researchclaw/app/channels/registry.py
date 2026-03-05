"""Channel registry: built-in + custom channels from working dir."""

from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path
from typing import Dict, Type

from ...constant import CUSTOM_CHANNELS_DIR
from .base import BaseChannel

logger = logging.getLogger(__name__)

_BUILTIN_SPECS: tuple[tuple[str, str, str], ...] = (
    ("console", "researchclaw.app.channels.console_channel", "ConsoleChannel"),
    ("telegram", "researchclaw.app.channels.telegram", "TelegramChannel"),
    ("discord", "researchclaw.app.channels.discord_", "DiscordChannel"),
    ("dingtalk", "researchclaw.app.channels.dingtalk", "DingTalkChannel"),
    ("feishu", "researchclaw.app.channels.feishu", "FeishuChannel"),
    ("imessage", "researchclaw.app.channels.imessage", "IMessageChannel"),
    ("qq", "researchclaw.app.channels.qq", "QQChannel"),
    ("voice", "researchclaw.app.channels.voice", "VoiceChannel"),
)


def _load_builtin_channels() -> Dict[str, Type[BaseChannel]]:
    out: Dict[str, Type[BaseChannel]] = {}
    for key, mod_path, cls_name in _BUILTIN_SPECS:
        try:
            mod = importlib.import_module(mod_path)
            cls = getattr(mod, cls_name)
            if isinstance(cls, type) and issubclass(cls, BaseChannel):
                out[key] = cls
        except Exception as exc:  # optional dependencies may be missing
            logger.warning(
                "skip builtin channel '%s' (%s): %s",
                key,
                mod_path,
                exc,
            )
    return out


def _discover_custom_channels() -> Dict[str, Type[BaseChannel]]:
    out: Dict[str, Type[BaseChannel]] = {}
    custom_dir = Path(CUSTOM_CHANNELS_DIR)
    if not custom_dir.is_dir():
        return out

    dir_str = str(custom_dir)
    if dir_str not in sys.path:
        sys.path.insert(0, dir_str)

    for path in sorted(custom_dir.iterdir()):
        if path.suffix == ".py" and path.stem != "__init__":
            name = path.stem
        elif path.is_dir() and (path / "__init__.py").exists():
            name = path.name
        else:
            continue
        try:
            mod = importlib.import_module(name)
        except Exception:
            logger.exception("failed to load custom channel: %s", name)
            continue
        for obj in vars(mod).values():
            if (
                isinstance(obj, type)
                and issubclass(obj, BaseChannel)
                and obj is not BaseChannel
            ):
                key = getattr(obj, "channel", None)
                if key:
                    out[key] = obj
                    logger.debug("custom channel registered: %s", key)
    return out


def get_channel_registry() -> Dict[str, Type[BaseChannel]]:
    out = _load_builtin_channels()
    out.update(_discover_custom_channels())
    return out


def register_default_channels(manager: "ChannelManager") -> None:  # noqa: F821
    from .manager import ChannelManager as _CM  # noqa: F811

    if not isinstance(manager, _CM):
        return
    # Kept for backward compatibility. _app currently only boots console.
    logger.debug("register_default_channels: console only (legacy)")


BUILTIN_CHANNEL_KEYS = frozenset(k for k, *_ in _BUILTIN_SPECS)
