"""Gateway runtime bootstrapping and state access helpers."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI

from ...constant import CHATS_FILE, JOBS_FILE, WORKING_DIR
from .schemas import GatewayRuntimeSnapshot

logger = logging.getLogger(__name__)


def _to_namespace(value: Any) -> Any:
    """Recursively convert dict/list values to attribute-access objects."""
    if isinstance(value, dict):
        return SimpleNamespace(
            **{key: _to_namespace(val) for key, val in value.items()},
        )
    if isinstance(value, list):
        return [_to_namespace(item) for item in value]
    return value


def build_channel_runtime_config(raw_config: dict[str, Any]) -> Any:
    """Normalize config shape so ChannelManager.from_config can consume it."""
    cfg = raw_config if isinstance(raw_config, dict) else {}
    channels_raw = cfg.get("channels")
    if not isinstance(channels_raw, dict):
        channels_raw = {}

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
        top_level = cfg.get(key)
        if key not in channels_raw and isinstance(top_level, dict):
            channels_raw[key] = top_level

    if "console" not in channels_raw:
        channels_raw["console"] = {"enabled": True, "bot_prefix": "[BOT] "}
    elif not isinstance(channels_raw["console"], dict):
        channels_raw["console"] = {"enabled": True, "bot_prefix": "[BOT] "}
    else:
        channels_raw["console"].setdefault("enabled", True)
        channels_raw["console"].setdefault("bot_prefix", "[BOT] ")

    available = channels_raw.get("available")
    if not isinstance(available, list):
        available = [
            key
            for key, value in channels_raw.items()
            if key != "available"
            and isinstance(value, dict)
            and value.get("enabled")
        ]
        if not available and channels_raw.get("console", {}).get("enabled"):
            available = ["console"]
        channels_raw["available"] = available

    runtime_cfg = {
        "channels": channels_raw,
        "show_tool_details": bool(cfg.get("show_tool_details", True)),
        "extra_channels": cfg.get("extra_channels", {}),
        "channel_accounts": cfg.get("channel_accounts", {}),
        "last_dispatch": cfg.get("last_dispatch", {}),
    }
    return _to_namespace(runtime_cfg)


class GatewayRuntime:
    """Thin wrapper around FastAPI app.state for runtime component access."""

    def __init__(self, app: FastAPI):
        self._app = app

    def bind(self, name: str, value: Any) -> Any:
        """Attach a runtime component to app.state and return it."""
        setattr(self._app.state, name, value)
        return value

    def get(self, name: str, default: Any = None) -> Any:
        """Read a runtime component from app.state."""
        return getattr(self._app.state, name, default)

    def snapshot(self) -> GatewayRuntimeSnapshot:
        """Return a lightweight snapshot of current runtime handles."""
        return GatewayRuntimeSnapshot(
            push_store=self.get("push_store"),
            automation_store=self.get("automation_store"),
            runner=self.get("runner"),
            chat_manager=self.get("chat_manager"),
            channel_manager=self.get("channel_manager"),
            mcp_manager=self.get("mcp_manager"),
            mcp_watcher=self.get("mcp_watcher"),
            cron_manager=self.get("cron_manager", self.get("cron")),
            config_watcher=self.get("config_watcher"),
            research_service=self.get("research_service"),
            research_runtime=self.get("research_runtime"),
            started_at=self.get("started_at"),
        )


def get_gateway_runtime(app: FastAPI) -> GatewayRuntime:
    """Return the gateway runtime wrapper stored on app.state."""
    runtime = getattr(app.state, "gateway_runtime", None)
    if runtime is None:
        runtime = GatewayRuntime(app)
        app.state.gateway_runtime = runtime
    return runtime


async def bootstrap_gateway_runtime(app: FastAPI) -> GatewayRuntime:
    """Start runtime components and bind them under the gateway boundary."""
    runtime = get_gateway_runtime(app)

    try:
        from ..console_push_store import ConsolePushStore

        runtime.bind("push_store", ConsolePushStore())
        logger.info("Console push store initialized")
    except Exception:
        logger.debug("Console push store not initialized", exc_info=True)

    try:
        from ..automation import AutomationRunStore

        max_runs = int(
            os.environ.get("RESEARCHCLAW_AUTOMATION_MAX_RUNS", "200"),
        )
        runtime.bind("automation_store", AutomationRunStore(max_runs=max_runs))
        logger.info("Automation run store initialized")
    except Exception:
        logger.debug("Automation run store not initialized", exc_info=True)

    try:
        from ...research import JsonResearchStore, ResearchService

        research_service = ResearchService(store=JsonResearchStore())
        os.environ["RESEARCHCLAW_RESEARCH_STATE_PATH"] = str(research_service.path)
        runtime.bind("research_service", research_service)
        logger.info("Research service initialized")
    except Exception:
        logger.debug("Research service not initialized", exc_info=True)

    runner = None
    try:
        from ..runner.multi_manager import MultiAgentRunnerManager

        runner = MultiAgentRunnerManager()
        await runner.start()
        runtime.bind("runner", runner)
        logger.info("Agent runner started (multi-agent)")
    except Exception:
        logger.exception("Failed to start agent runner")

    try:
        from ..runner.chat_manager import ChatManager
        from ..runner.repo.json_repo import JsonChatRepository

        chat_repo = JsonChatRepository(Path(WORKING_DIR) / CHATS_FILE)
        chat_manager = ChatManager(repo=chat_repo)
        runtime.bind("chat_manager", chat_manager)
        if runner is not None:
            runner.set_chat_manager(chat_manager)
        logger.info("Chat manager started")
    except Exception:
        logger.debug("Chat manager not started", exc_info=True)

    try:
        if runner is None:
            raise RuntimeError("runner not initialized")

        from ...config import load_config, update_last_dispatch
        from ..channels.manager import ChannelManager
        from ..channels.utils import make_process_from_runner

        raw_config = load_config()
        runtime_config = build_channel_runtime_config(raw_config)
        channel_manager = ChannelManager.from_config(
            process=make_process_from_runner(runner),
            config=runtime_config,
            on_last_dispatch=update_last_dispatch,
            show_tool_details=getattr(
                runtime_config,
                "show_tool_details",
                True,
            ),
        )
        await channel_manager.start_all()
        runtime.bind("channel_manager", channel_manager)
        logger.info("Channel manager started")
    except Exception:
        logger.debug("Channel manager not started", exc_info=True)

    try:
        from ...research import ResearchWorkflowRuntime

        if runtime.get("research_service") is None:
            raise RuntimeError("research_service not initialized")
        research_runtime = ResearchWorkflowRuntime(
            service=runtime.get("research_service"),
            channel_manager=runtime.get("channel_manager"),
            runner=runtime.get("runner"),
        )
        runtime.bind("research_runtime", research_runtime)
        logger.info("Research runtime initialized")
    except Exception:
        logger.debug("Research runtime not initialized", exc_info=True)

    try:
        from ...config import load_config
        from ...config.config import config_path
        from ..mcp.manager import MCPManager
        from ..mcp.watcher import MCPWatcher

        mcp_manager = MCPManager()
        await mcp_manager.init_from_config(load_config())

        async def _refresh_runner_mcp_clients() -> None:
            if runner is None:
                return
            try:
                await runner.refresh_mcp_clients(force=True)
            except Exception:
                logger.debug(
                    "Refresh MCP clients on runner failed",
                    exc_info=True,
                )

        if runner is not None:
            runner.set_mcp_manager(mcp_manager)
            await _refresh_runner_mcp_clients()

        mcp_watcher = MCPWatcher(
            mcp_manager=mcp_manager,
            config_loader=load_config,
            config_file_path=config_path(),
            on_reloaded=_refresh_runner_mcp_clients,
        )
        await mcp_watcher.start()
        runtime.bind("mcp_manager", mcp_manager)
        runtime.bind("mcp_watcher", mcp_watcher)
        logger.info("MCP manager started")
    except Exception:
        logger.debug("MCP manager not started", exc_info=True)

    try:
        from ...constant import (
            HEARTBEAT_ENABLED,
            HEARTBEAT_INTERVAL_MINUTES,
            RESEARCH_FOLLOWUP_ENABLED,
            RESEARCH_FOLLOWUP_INTERVAL_MINUTES,
        )
        from ..crons.deadline_reminder import deadline_reminder
        from ..crons.heartbeat import run_heartbeat_once
        from ..crons.manager import CronManager
        from ..crons.paper_digest import paper_digest
        from ..crons.repo.json_repo import JsonJobRepository

        cron_repo = JsonJobRepository(Path(WORKING_DIR) / JOBS_FILE)
        cron = CronManager(
            repo=cron_repo,
            runner=runner,
            channel_manager=runtime.get("channel_manager"),
            timezone="UTC",
        )

        async def heartbeat_job() -> None:
            if runner is None:
                logger.warning("heartbeat skipped: runner not initialized")
                return
            await run_heartbeat_once(
                runner=runner,
                channel_manager=runtime.get("channel_manager"),
            )

        cron.register(
            "heartbeat",
            heartbeat_job,
            interval_seconds=max(1, HEARTBEAT_INTERVAL_MINUTES) * 60,
            enabled=HEARTBEAT_ENABLED,
        )
        cron.register(
            "paper_digest",
            paper_digest,
            interval_seconds=6 * 3600,
            enabled=True,
        )
        cron.register(
            "deadline_reminder",
            deadline_reminder,
            interval_seconds=12 * 3600,
            enabled=True,
        )
        research_runtime = runtime.get("research_runtime")
        if research_runtime is not None:

            async def research_followup_job() -> None:
                await research_runtime.run_proactive_cycle()

            cron.register(
                "research_followup",
                research_followup_job,
                interval_seconds=max(1, RESEARCH_FOLLOWUP_INTERVAL_MINUTES)
                * 60,
                enabled=RESEARCH_FOLLOWUP_ENABLED,
            )
        await cron.start()
        runtime.bind("cron", cron)
        runtime.bind("cron_manager", cron)
        logger.info("Cron manager started")
    except Exception:
        logger.debug("Cron manager not started", exc_info=True)

    try:
        if runner is None or runtime.get("channel_manager") is None:
            raise RuntimeError("runner/channel_manager not initialized")

        from ...config import update_last_dispatch
        from ...config.watcher import ConfigWatcher
        from ..channels.utils import make_process_from_runner

        config_watcher = ConfigWatcher(
            channel_manager=runtime.get("channel_manager"),
            process=make_process_from_runner(runner),
            on_last_dispatch=update_last_dispatch,
            cron_manager=runtime.get("cron_manager"),
        )
        await config_watcher.start()
        runtime.bind("config_watcher", config_watcher)
        logger.info("Config watcher started")
    except Exception:
        logger.debug("Config watcher not started", exc_info=True)

    return runtime


async def shutdown_gateway_runtime(app: FastAPI) -> None:
    """Stop runtime components in reverse dependency order."""
    runtime = get_gateway_runtime(app)
    if runtime.get("config_watcher") is not None:
        await runtime.get("config_watcher").stop()
    if runtime.get("cron") is not None:
        await runtime.get("cron").stop()
    if runtime.get("mcp_watcher") is not None:
        await runtime.get("mcp_watcher").stop()
    if runtime.get("mcp_manager") is not None:
        await runtime.get("mcp_manager").stop()
    if runtime.get("channel_manager") is not None:
        await runtime.get("channel_manager").stop_all()
    if runtime.get("runner") is not None:
        await runtime.get("runner").stop()
