"""Independent watcher for MCP configuration changes."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from ...config.config import config_path, load_config
from .manager import MCPManager

logger = logging.getLogger(__name__)

DEFAULT_POLL_INTERVAL = 2.0


class MCPWatcher:
    """Watch MCP config and hot-reload runtime clients on change."""

    def __init__(
        self,
        *,
        mcp_manager: MCPManager,
        config_loader: Callable[[], Any] = load_config,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        config_file_path: Optional[Path] = None,
        on_reloaded: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> None:
        self._mcp_manager = mcp_manager
        self._config_loader = config_loader
        self._poll_interval = poll_interval
        self._config_path = config_file_path or config_path()
        self._on_reloaded = on_reloaded

        self._task: Optional[asyncio.Task] = None
        self._reload_task: Optional[asyncio.Task] = None
        self._last_mtime: float = 0.0
        self._last_hash: Optional[int] = None

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._snapshot()
        self._task = asyncio.create_task(self._poll_loop(), name="mcp_watcher")
        logger.info(
            "MCPWatcher started (poll=%.1fs, path=%s)",
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

        if self._reload_task and not self._reload_task.done():
            try:
                await asyncio.wait_for(self._reload_task, timeout=5.0)
            except Exception:
                self._reload_task.cancel()
        self._reload_task = None
        logger.info("MCPWatcher stopped")

    def _load_clients(self) -> dict[str, dict[str, Any]]:
        try:
            cfg = self._config_loader()
        except Exception:
            logger.debug("MCPWatcher: config loader failed", exc_info=True)
            return {}
        return MCPManager._extract_client_configs(cfg)

    @staticmethod
    def _clients_hash(clients: dict[str, dict[str, Any]]) -> int:
        payload = json.dumps(
            clients,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        return hash(payload)

    def _snapshot(self) -> None:
        try:
            self._last_mtime = (
                self._config_path.stat().st_mtime if self._config_path.exists() else 0.0
            )
        except Exception:
            self._last_mtime = 0.0
        self._last_hash = self._clients_hash(self._load_clients())

    async def _check(self) -> None:
        try:
            mtime = self._config_path.stat().st_mtime
        except FileNotFoundError:
            return
        except Exception:
            logger.debug("MCPWatcher: failed to stat config", exc_info=True)
            return

        if mtime == self._last_mtime:
            return
        self._last_mtime = mtime

        new_clients = self._load_clients()
        new_hash = self._clients_hash(new_clients)
        if new_hash == self._last_hash:
            return

        if self._reload_task and not self._reload_task.done():
            logger.debug(
                "MCPWatcher: skip reload, previous reload still running",
            )
            return

        self._reload_task = asyncio.create_task(
            self._reload(new_clients, new_hash),
            name="mcp_reload",
        )

    async def _reload(self, clients: dict[str, dict[str, Any]], new_hash: int) -> None:
        try:
            await self._mcp_manager.init_from_config({"clients": clients})
            if self._on_reloaded is not None:
                await self._on_reloaded()
        except Exception:
            logger.warning("MCPWatcher: reload failed", exc_info=True)
            return
        self._last_hash = new_hash
        logger.info("MCPWatcher: MCP clients reloaded from config.json")

    async def _poll_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self._poll_interval)
                await self._check()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("MCPWatcher: poll iteration failed")
