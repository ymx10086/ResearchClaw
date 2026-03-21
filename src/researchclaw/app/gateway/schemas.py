"""Schemas shared by the internal gateway boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class GatewayRuntimeSnapshot:
    """Lightweight snapshot of runtime handles exposed through the gateway."""

    push_store: Any = None
    automation_store: Any = None
    runner: Any = None
    chat_manager: Any = None
    channel_manager: Any = None
    mcp_manager: Any = None
    mcp_watcher: Any = None
    cron_manager: Any = None
    config_watcher: Any = None
    research_service: Any = None
    research_runtime: Any = None
    started_at: float | None = None
