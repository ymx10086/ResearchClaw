"""MCP client manager with hot-reloadable lifecycle management."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from researchclaw.constant import WORKING_DIR

logger = logging.getLogger(__name__)


class MCPManager:
    """Manages MCP clients with runtime replacement support."""

    def __init__(self, file_path: str | None = None):
        self._clients: Dict[str, Any] = {}
        self._client_configs: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self.file_path = Path(file_path or (Path(WORKING_DIR) / "config.json"))
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Backward-compatible config operations (used by MCP API routes)
    # ------------------------------------------------------------------

    def register(self, name: str, config: dict[str, Any]) -> None:
        self._client_configs[name] = dict(config or {})

    def remove(self, name: str) -> None:
        self._client_configs.pop(name, None)

    def list_clients(self) -> list[dict[str, Any]]:
        return [
            {"key": k, **dict(v or {})}
            for k, v in self._client_configs.items()
        ]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        await self.load()
        await self.reload()
        logger.debug(
            "MCP manager started with %d configured clients",
            len(self._client_configs),
        )

    async def stop(self) -> None:
        await self.close_all()
        await self.save()
        logger.debug("MCP manager stopped")

    async def load(self) -> None:
        if not self.file_path.exists():
            self._client_configs = {}
            return
        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
            mcp = data.get("mcp", {}) if isinstance(data, dict) else {}
            clients = mcp.get("clients", {}) if isinstance(mcp, dict) else {}
            if isinstance(clients, dict):
                self._client_configs = {
                    str(k): dict(v or {})
                    for k, v in clients.items()
                    if isinstance(v, dict)
                }
            else:
                self._client_configs = {}
        except Exception:
            logger.exception("Failed to load MCP config from %s", self.file_path)
            self._client_configs = {}

    async def save(self) -> None:
        try:
            data: dict[str, Any] = {}
            if self.file_path.exists():
                try:
                    old = json.loads(self.file_path.read_text(encoding="utf-8"))
                    if isinstance(old, dict):
                        data = old
                except Exception:
                    logger.debug("MCP save: ignore invalid old config.json")

            mcp = data.get("mcp")
            if not isinstance(mcp, dict):
                mcp = {}
                data["mcp"] = mcp
            mcp["clients"] = self._client_configs

            self.file_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            logger.exception("Failed to save MCP config to %s", self.file_path)

    # ------------------------------------------------------------------
    # Runtime clients
    # ------------------------------------------------------------------

    async def init_from_config(self, config: Any) -> None:
        """Apply MCP config and hot-reload runtime clients."""
        clients_cfg = self._extract_client_configs(config)
        self._client_configs = clients_cfg

        # Remove disabled or deleted runtime clients.
        for key in list(self._clients.keys()):
            cfg = clients_cfg.get(key)
            if cfg is None or not bool(cfg.get("enabled", True)):
                await self.remove_client(key)

        # Add/update enabled clients.
        for key, cfg in clients_cfg.items():
            if not bool(cfg.get("enabled", True)):
                continue
            new_info = self._rebuild_info_for_config(key, cfg)
            old_info = self._rebuild_info_for_client(self._clients.get(key))
            if key not in self._clients or old_info != new_info:
                try:
                    await self.replace_client(key, cfg)
                except Exception:
                    logger.warning(
                        "Failed to (re)connect MCP client '%s'",
                        key,
                        exc_info=True,
                    )

    async def reload(self) -> None:
        await self.init_from_config({"clients": self._client_configs})

    async def get_clients(self) -> List[Any]:
        async with self._lock:
            return [c for c in self._clients.values() if c is not None]

    async def replace_client(
        self,
        key: str,
        client_config: Dict[str, Any],
        timeout: float = 60.0,
    ) -> None:
        """Connect new client then swap and close old one."""
        cfg = self._normalize_client_config(key, client_config)
        if not cfg.get("enabled", True):
            await self.remove_client(key)
            return

        new_client = self._build_client(key, cfg)
        if new_client is None:
            return

        try:
            await asyncio.wait_for(new_client.connect(), timeout=timeout)
        except Exception:
            try:
                await new_client.close()
            except Exception:
                pass
            raise

        async with self._lock:
            old_client = self._clients.get(key)
            self._clients[key] = new_client

        if old_client is not None:
            try:
                await old_client.close()
            except Exception:
                logger.warning("Error closing old MCP client '%s'", key)

    async def remove_client(self, key: str) -> None:
        """Remove and close one runtime client."""
        async with self._lock:
            old_client = self._clients.pop(key, None)
        if old_client is not None:
            try:
                await old_client.close()
            except Exception:
                logger.warning("Error closing MCP client '%s'", key)

    async def close_all(self) -> None:
        async with self._lock:
            snapshot = list(self._clients.items())
            self._clients.clear()
        for key, client in snapshot:
            try:
                await client.close()
            except Exception:
                logger.warning("Error closing MCP client '%s'", key)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_transport(raw: str) -> str:
        transport = (raw or "").strip().lower()
        alias = {
            "http": "streamable_http",
            "streamablehttp": "streamable_http",
            "streamable_http": "streamable_http",
            "sse": "sse",
            "stdio": "stdio",
        }
        return alias.get(transport, transport or "stdio")

    @classmethod
    def _normalize_client_config(
        cls,
        key: str,
        cfg: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = dict(cfg or {})
        if "enabled" not in payload and "isActive" in payload:
            payload["enabled"] = bool(payload.get("isActive"))
        if "url" not in payload and "baseUrl" in payload:
            payload["url"] = payload.get("baseUrl")
        if "transport" not in payload and "type" in payload:
            payload["transport"] = payload.get("type")
        transport = cls._normalize_transport(str(payload.get("transport", "")))
        return {
            "name": str(payload.get("name") or key),
            "description": str(payload.get("description") or ""),
            "enabled": bool(payload.get("enabled", True)),
            "transport": transport,
            "url": str(payload.get("url") or ""),
            "headers": dict(payload.get("headers") or {}),
            "command": str(payload.get("command") or ""),
            "args": list(payload.get("args") or []),
            "env": dict(payload.get("env") or {}),
            "cwd": str(payload.get("cwd") or ""),
        }

    @classmethod
    def _extract_client_configs(cls, config: Any) -> Dict[str, Dict[str, Any]]:
        if isinstance(config, dict):
            if "clients" in config and isinstance(config["clients"], dict):
                source = config["clients"]
            elif (
                "mcp" in config
                and isinstance(config["mcp"], dict)
                and isinstance(config["mcp"].get("clients"), dict)
            ):
                source = config["mcp"]["clients"]
            else:
                source = {}
            return {
                str(k): cls._normalize_client_config(str(k), v)
                for k, v in source.items()
                if isinstance(v, dict)
            }

        mcp = getattr(config, "mcp", None)
        if mcp is not None:
            clients = getattr(mcp, "clients", None)
        else:
            clients = getattr(config, "clients", None)
        if not isinstance(clients, dict):
            return {}
        return {
            str(k): cls._normalize_client_config(str(k), v)
            for k, v in clients.items()
            if isinstance(v, dict)
        }

    @staticmethod
    def _rebuild_info_for_config(key: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "key": key,
            "name": cfg.get("name", key),
            "transport": cfg.get("transport", "stdio"),
            "url": cfg.get("url", ""),
            "headers": cfg.get("headers", {}),
            "command": cfg.get("command", ""),
            "args": cfg.get("args", []),
            "env": cfg.get("env", {}),
            "cwd": cfg.get("cwd", ""),
        }

    @staticmethod
    def _rebuild_info_for_client(client: Any) -> Optional[Dict[str, Any]]:
        if client is None:
            return None
        return getattr(client, "_researchclaw_rebuild_info", None)

    def _build_client(self, key: str, cfg: Dict[str, Any]) -> Any:
        try:
            from agentscope.mcp import HttpStatefulClient, StdIOStatefulClient
        except Exception:
            logger.warning(
                "agentscope.mcp not available; skip MCP runtime client '%s'",
                cfg.get("name", ""),
            )
            return None

        transport = cfg.get("transport", "stdio")
        if transport == "stdio":
            if not cfg.get("command"):
                logger.warning(
                    "Skip MCP client '%s': stdio requires command",
                    cfg.get("name", ""),
                )
                return None
            client = StdIOStatefulClient(
                name=cfg.get("name", ""),
                command=cfg.get("command", ""),
                args=cfg.get("args", []),
                env=cfg.get("env", {}),
                cwd=cfg.get("cwd") or None,
            )
        else:
            if not cfg.get("url"):
                logger.warning(
                    "Skip MCP client '%s': %s requires url",
                    cfg.get("name", ""),
                    transport,
                )
                return None
            client = HttpStatefulClient(
                name=cfg.get("name", ""),
                transport=transport,
                url=cfg.get("url", ""),
                headers=cfg.get("headers") or None,
            )

        setattr(
            client,
            "_researchclaw_rebuild_info",
            self._rebuild_info_for_config(key, cfg),
        )
        return client
