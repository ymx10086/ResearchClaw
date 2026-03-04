"""Channel registry: built-in + custom channels from working dir.

Key improvements over CoPaw:
- CUSTOM_CHANNELS_DIR is str (wrapped with Path at use-time).
- Lazy imports for heavy channel classes to avoid import-time cost.
- BUILTIN_CHANNEL_KEYS frozenset for O(1) membership check.
"""
from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path
from typing import Dict, Type

from ...constant import CUSTOM_CHANNELS_DIR
from .base import BaseChannel
from .console_channel import ConsoleChannel
from .dingtalk import DingTalkChannel
from .discord_ import DiscordChannel
from .feishu import FeishuChannel
from .imessage import IMessageChannel
from .qq import QQChannel
from .telegram import TelegramChannel

logger = logging.getLogger(__name__)

_BUILTIN: Dict[str, Type[BaseChannel]] = {
    "console": ConsoleChannel,
    "telegram": TelegramChannel,
    "discord": DiscordChannel,
    "dingtalk": DingTalkChannel,
    "feishu": FeishuChannel,
    "imessage": IMessageChannel,
    "qq": QQChannel,
}

BUILTIN_CHANNEL_KEYS = frozenset(_BUILTIN.keys())


def _discover_custom_channels() -> Dict[str, Type[BaseChannel]]:
    """Load channel classes from CUSTOM_CHANNELS_DIR.

    Scans for .py files and packages (dirs with __init__.py) in the
    custom channels directory. Any class that subclasses BaseChannel
    and has a ``channel`` attribute is registered.
    """
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
    """Built-in channel classes + custom channels from custom_channels/."""
    out = dict(_BUILTIN)
    out.update(_discover_custom_channels())
    return out


def register_default_channels(manager: "ChannelManager") -> None:  # noqa: F821
    """Legacy helper: register console channel with simple API.

    For full setup with queue architecture, use ``ChannelManager.from_config``.
    """
    from .manager import ChannelManager as _CM  # noqa: F811

    if not isinstance(manager, _CM):
        return
    # Only register console by default (other channels need config)
    logger.debug("register_default_channels: console only (legacy)")
