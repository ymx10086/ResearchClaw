"""Watch config.json and hot-reload channels / heartbeat schedule."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

from .config import config_path, load_config
from ..app.channels.manager import ChannelManager
from ..app.channels.registry import get_channel_registry

logger = logging.getLogger(__name__)

DEFAULT_POLL_INTERVAL = 2.0


def _to_namespace(value: Any) -> Any:
    if isinstance(value, dict):
        return SimpleNamespace(**{k: _to_namespace(v) for k, v in value.items()})
    if isinstance(value, list):
        return [_to_namespace(v) for v in value]
    return value


def _json_hash(value: Any) -> int:
    try:
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        payload = str(value)
    return hash(payload)


class ConfigWatcher:
    """Poll config file changes and apply incremental channel reloads."""

    def __init__(
        self,
        *,
        channel_manager: ChannelManager,
        process: Any,
        on_last_dispatch: Any = None,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        config_file_path: Optional[Path] = None,
        cron_manager: Any = None,
    ):
        self._channel_manager = channel_manager
        self._process = process
        self._on_last_dispatch = on_last_dispatch
        self._poll_interval = poll_interval
        self._config_path = config_file_path or config_path()
        self._cron_manager = cron_manager

        self._task: Optional[asyncio.Task] = None
        self._last_mtime: float = 0.0
        self._last_channels_dump: dict[str, Any] = {}
        self._last_desired_channels: set[str] = set()
        self._last_heartbeat_hash: Optional[int] = None

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._snapshot()
        self._task = asyncio.create_task(self._poll_loop(), name="config_watcher")
        logger.info(
            "ConfigWatcher started (poll=%.1fs, path=%s)",
            self._poll_interval,
            self._config_path,
        )

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("ConfigWatcher stopped")

    def _load_raw_config(self) -> dict[str, Any]:
        cfg = load_config(self._config_path)
        if isinstance(cfg, dict):
            return cfg
        return {}

    @staticmethod
    def _normalize_channels(raw_config: dict[str, Any]) -> dict[str, Any]:
        source = raw_config.get("channels")
        out = dict(source) if isinstance(source, dict) else {}

        channel_keys = {
            "console",
            "telegram",
            "discord",
            "dingtalk",
            "feishu",
            "imessage",
            "qq",
            "voice",
        }
        for key in channel_keys:
            top_level = raw_config.get(key)
            if key not in out and isinstance(top_level, dict):
                out[key] = top_level

        console_cfg = out.get("console")
        if not isinstance(console_cfg, dict):
            out["console"] = {"enabled": True, "bot_prefix": "[BOT] "}
        else:
            console_cfg.setdefault("enabled", True)
            console_cfg.setdefault("bot_prefix", "[BOT] ")

        available = out.get("available")
        if not isinstance(available, list):
            available = [
                k
                for k, v in out.items()
                if k != "available" and isinstance(v, dict) and v.get("enabled")
            ]
            if not available and out.get("console", {}).get("enabled"):
                available = ["console"]
            out["available"] = available

        return out

    @staticmethod
    def _desired_channels(channels: dict[str, Any]) -> set[str]:
        available = channels.get("available")
        if isinstance(available, list):
            return {str(x) for x in available if str(x).strip()}
        return {
            k
            for k, v in channels.items()
            if k != "available" and isinstance(v, dict) and v.get("enabled")
        }

    @staticmethod
    def _extract_heartbeat_payload(raw_config: dict[str, Any]) -> dict[str, Any]:
        hb = (
            raw_config.get("agents", {})
            .get("defaults", {})
            .get("heartbeat")
        )
        hb = hb if isinstance(hb, dict) else {}
        if "enabled" not in hb and "heartbeat_enabled" in raw_config:
            hb["enabled"] = bool(raw_config.get("heartbeat_enabled"))
        if "every" not in hb and "heartbeat_every" in raw_config:
            hb["every"] = raw_config.get("heartbeat_every")
        if "target" not in hb and "heartbeat_target" in raw_config:
            hb["target"] = raw_config.get("heartbeat_target")
        return hb

    def _snapshot(self) -> None:
        try:
            self._last_mtime = (
                self._config_path.stat().st_mtime if self._config_path.exists() else 0.0
            )
        except Exception:
            self._last_mtime = 0.0

        raw = self._load_raw_config()
        channels = self._normalize_channels(raw)
        self._last_channels_dump = {
            k: v for k, v in channels.items() if k != "available"
        }
        self._last_desired_channels = self._desired_channels(channels)
        self._last_heartbeat_hash = _json_hash(self._extract_heartbeat_payload(raw))

    def _build_channel(self, name: str, ch_cfg: dict[str, Any], show_tool_details: bool):
        registry = get_channel_registry()
        ch_cls = registry.get(name)
        if ch_cls is None:
            logger.warning("ConfigWatcher: unknown channel '%s', skip", name)
            return None

        ns_cfg = _to_namespace(ch_cfg)
        filter_tool_messages = bool(getattr(ns_cfg, "filter_tool_messages", False))
        try:
            return ch_cls.from_config(
                self._process,
                ns_cfg,
                on_reply_sent=self._on_last_dispatch,
                show_tool_details=show_tool_details,
                filter_tool_messages=filter_tool_messages,
            )
        except TypeError:
            return ch_cls.from_config(
                self._process,
                ns_cfg,
                on_reply_sent=self._on_last_dispatch,
                show_tool_details=show_tool_details,
            )

    async def _apply_channel_changes(self, raw: dict[str, Any]) -> None:
        channels = self._normalize_channels(raw)
        desired_channels = self._desired_channels(channels)
        show_tool_details = bool(raw.get("show_tool_details", True))
        new_dump = {k: v for k, v in channels.items() if k != "available"}

        names = sorted(
            set(self._last_channels_dump.keys())
            | set(new_dump.keys())
            | set(self._last_desired_channels)
            | set(desired_channels)
        )
        for name in names:
            old_cfg = self._last_channels_dump.get(name)
            new_cfg = new_dump.get(name)

            should_run = name in desired_channels
            was_running = name in self._last_desired_channels

            if not should_run:
                if was_running:
                    removed = await self._channel_manager.remove_channel(name)
                    if removed:
                        logger.info("ConfigWatcher: channel '%s' removed", name)
                continue

            if new_cfg is None:
                logger.warning(
                    "ConfigWatcher: desired channel '%s' has no config, skip",
                    name,
                )
                continue

            if old_cfg == new_cfg and was_running:
                continue
            try:
                old_channel = await self._channel_manager.get_channel(name)
                if old_channel is not None:
                    new_channel = old_channel.clone(_to_namespace(new_cfg))
                else:
                    new_channel = self._build_channel(name, new_cfg, show_tool_details)
                if new_channel is None:
                    continue
                await self._channel_manager.replace_channel(new_channel)
                logger.info("ConfigWatcher: channel '%s' reloaded", name)
            except Exception:
                logger.exception("ConfigWatcher: failed to reload channel '%s'", name)

        self._last_channels_dump = new_dump
        self._last_desired_channels = desired_channels

    async def _apply_heartbeat_change(self, raw: dict[str, Any]) -> None:
        new_hash = _json_hash(self._extract_heartbeat_payload(raw))
        if new_hash == self._last_heartbeat_hash:
            return
        self._last_heartbeat_hash = new_hash
        if self._cron_manager is not None and hasattr(self._cron_manager, "reschedule_heartbeat"):
            try:
                await self._cron_manager.reschedule_heartbeat()
                logger.info("ConfigWatcher: heartbeat rescheduled")
            except Exception:
                logger.exception("ConfigWatcher: heartbeat reschedule failed")

    async def _check(self) -> None:
        try:
            mtime = self._config_path.stat().st_mtime
        except FileNotFoundError:
            return
        except Exception:
            logger.exception("ConfigWatcher: stat config failed")
            return

        if mtime == self._last_mtime:
            return
        self._last_mtime = mtime

        raw = self._load_raw_config()
        await self._apply_channel_changes(raw)
        await self._apply_heartbeat_change(raw)

    async def _poll_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self._poll_interval)
                await self._check()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("ConfigWatcher: poll iteration failed")
