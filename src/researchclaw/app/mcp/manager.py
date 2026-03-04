"""MCP manager for tool server connections."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from researchclaw.constant import WORKING_DIR

logger = logging.getLogger(__name__)


class MCPManager:
    """Stores and manages MCP client configurations."""

    def __init__(self, file_path: str | None = None):
        self._clients: dict[str, dict[str, Any]] = {}
        self.file_path = Path(
            file_path or (Path(WORKING_DIR) / "mcp_clients.json"),
        )
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def register(self, name: str, config: dict[str, Any]) -> None:
        self._clients[name] = config

    def remove(self, name: str) -> None:
        self._clients.pop(name, None)

    def list_clients(self) -> list[dict[str, Any]]:
        return [{"key": k, **v} for k, v in self._clients.items()]

    async def start(self) -> None:
        await self.load()
        logger.debug("MCP manager started with %d clients", len(self._clients))

    async def stop(self) -> None:
        await self.save()
        logger.debug("MCP manager stopped")

    async def load(self) -> None:
        if not self.file_path.exists():
            self._clients = {}
            return
        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self._clients = data
        except Exception:
            logger.exception(
                "Failed to load MCP clients from %s",
                self.file_path,
            )

    async def save(self) -> None:
        try:
            self.file_path.write_text(
                json.dumps(self._clients, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            logger.exception(
                "Failed to save MCP clients to %s",
                self.file_path,
            )
