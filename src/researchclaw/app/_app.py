"""ResearchClaw FastAPI application entry point.

Creates and configures the FastAPI app with:
- Agent runner
- API routes
- Console (frontend) serving
- Lifecycle management
"""

from __future__ import annotations

import logging
import mimetypes
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ..__version__ import __version__
from ..constant import CHATS_FILE, CORS_ORIGINS, DOCS_ENABLED, WORKING_DIR

logger = logging.getLogger(__name__)

# Fix common MIME types
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")


def _to_namespace(value: Any) -> Any:
    """Recursively convert dict/list to attribute-access objects."""
    if isinstance(value, dict):
        return SimpleNamespace(
            **{k: _to_namespace(v) for k, v in value.items()},
        )
    if isinstance(value, list):
        return [_to_namespace(v) for v in value]
    return value


def _build_channel_runtime_config(raw_config: dict[str, Any]) -> Any:
    """Normalize config shape so ChannelManager.from_config can consume it."""
    cfg = raw_config if isinstance(raw_config, dict) else {}
    channels_raw = cfg.get("channels")
    if not isinstance(channels_raw, dict):
        channels_raw = {}

    # Backward-compat: allow top-level "<channel>": {...} style.
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
            k
            for k, v in channels_raw.items()
            if k != "available" and isinstance(v, dict) and v.get("enabled")
        ]
        if not available and channels_raw.get("console", {}).get("enabled"):
            available = ["console"]
        channels_raw["available"] = available

    runtime_cfg = {
        "channels": channels_raw,
        "show_tool_details": bool(cfg.get("show_tool_details", True)),
        "extra_channels": cfg.get("extra_channels", {}),
        "last_dispatch": cfg.get("last_dispatch", {}),
    }
    return _to_namespace(runtime_cfg)


# ── Lifecycle ───────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    logger.info("ResearchClaw v%s starting up...", __version__)

    # Ensure working directory exists
    os.makedirs(WORKING_DIR, exist_ok=True)
    app.state.started_at = time.time()

    # Initialise components
    try:
        from .console_push_store import ConsolePushStore

        app.state.push_store = ConsolePushStore()
        logger.info("Console push store initialized")
    except Exception:
        logger.debug("Console push store not initialized", exc_info=True)

    runner = None
    try:
        from .runner.manager import AgentRunnerManager

        runner = AgentRunnerManager()
        await runner.start()
        app.state.runner = runner
        logger.info("Agent runner started")
    except Exception:
        logger.exception("Failed to start agent runner")

    try:
        from .runner.chat_manager import ChatManager
        from .runner.repo.json_repo import JsonChatRepository

        chat_repo = JsonChatRepository(Path(WORKING_DIR) / CHATS_FILE)
        chat_manager = ChatManager(repo=chat_repo)
        app.state.chat_manager = chat_manager
        if runner is not None:
            runner.set_chat_manager(chat_manager)
        logger.info("Chat manager started")
    except Exception:
        logger.debug("Chat manager not started", exc_info=True)

    try:
        if runner is None:
            raise RuntimeError("runner not initialized")

        from .channels.manager import ChannelManager
        from .channels.utils import make_process_from_runner
        from ..config import load_config, update_last_dispatch

        raw_config = load_config()
        runtime_config = _build_channel_runtime_config(raw_config)
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
        app.state.channel_manager = channel_manager
        logger.info("Channel manager started")
    except Exception:
        logger.debug("Channel manager not started", exc_info=True)

    try:
        from .mcp.manager import MCPManager
        from .mcp.watcher import MCPWatcher
        from ..config import load_config
        from ..config.config import config_path

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
        app.state.mcp_manager = mcp_manager
        app.state.mcp_watcher = mcp_watcher
        logger.info("MCP manager started")
    except Exception:
        logger.debug("MCP manager not started", exc_info=True)

    try:
        from .crons.manager import CronManager
        from .crons.deadline_reminder import deadline_reminder
        from .crons.heartbeat import run_heartbeat_once
        from .crons.paper_digest import paper_digest
        from ..constant import HEARTBEAT_ENABLED, HEARTBEAT_INTERVAL_MINUTES

        cron = CronManager()

        async def heartbeat_job() -> None:
            if runner is None:
                logger.warning("heartbeat skipped: runner not initialized")
                return
            await run_heartbeat_once(
                runner=runner,
                channel_manager=getattr(app.state, "channel_manager", None),
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
        await cron.start()
        app.state.cron = cron
        app.state.cron_manager = cron
        logger.info("Cron manager started")
    except Exception:
        logger.debug("Cron manager not started", exc_info=True)

    try:
        if runner is None or not hasattr(app.state, "channel_manager"):
            raise RuntimeError("runner/channel_manager not initialized")
        from .channels.utils import make_process_from_runner
        from ..config import update_last_dispatch
        from ..config.watcher import ConfigWatcher

        config_watcher = ConfigWatcher(
            channel_manager=app.state.channel_manager,
            process=make_process_from_runner(runner),
            on_last_dispatch=update_last_dispatch,
            cron_manager=getattr(app.state, "cron_manager", None),
        )
        await config_watcher.start()
        app.state.config_watcher = config_watcher
        logger.info("Config watcher started")
    except Exception:
        logger.debug("Config watcher not started", exc_info=True)

    yield

    # Shutdown
    logger.info("ResearchClaw shutting down...")
    if hasattr(app.state, "config_watcher"):
        await app.state.config_watcher.stop()
    if hasattr(app.state, "cron"):
        await app.state.cron.stop()
    if hasattr(app.state, "mcp_watcher"):
        await app.state.mcp_watcher.stop()
    if hasattr(app.state, "mcp_manager"):
        await app.state.mcp_manager.stop()
    if hasattr(app.state, "channel_manager"):
        await app.state.channel_manager.stop_all()
    if hasattr(app.state, "runner"):
        await app.state.runner.stop()


# ── FastAPI app ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="ResearchClaw",
    description="AI Research Assistant API",
    version=__version__,
    docs_url="/docs" if DOCS_ENABLED else None,
    redoc_url="/redoc" if DOCS_ENABLED else None,
    lifespan=lifespan,
)

# CORS
origins = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ── Health & version ────────────────────────────────────────────────────────


@app.get("/api/version")
async def get_version():
    """Return the current version."""
    return {"version": __version__, "name": "ResearchClaw"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


# ── API routes ──────────────────────────────────────────────────────────────

_router_defs: list[tuple[str, str, list[str]]] = [
    ("researchclaw.app.routers.agent", "/api/agent", ["Agent"]),
    ("researchclaw.app.routers.config", "/api/config", ["Config"]),
    ("researchclaw.app.routers.console", "/api/console", ["Console"]),
    ("researchclaw.app.routers.control", "/api/control", ["Control"]),
    ("researchclaw.app.routers.envs", "/api/envs", ["Environments"]),
    ("researchclaw.app.routers.mcp", "/api/mcp", ["MCP"]),
    ("researchclaw.app.routers.papers", "/api/papers", ["Papers"]),
    ("researchclaw.app.routers.providers", "/api/providers", ["Providers"]),
    ("researchclaw.app.routers.skills", "/api/skills", ["Skills"]),
    ("researchclaw.app.routers.workspace", "/api/workspace", ["Workspace"]),
]

for _mod_path, _prefix, _tags in _router_defs:
    try:
        import importlib as _il

        _mod = _il.import_module(_mod_path)
        app.include_router(_mod.router, prefix=_prefix, tags=_tags)
    except Exception as e:
        logger.warning("Router %s could not be loaded: %s", _mod_path, e)

# Extra routers with non-standard module paths
for _mod_path, _prefix, _tags in [
    ("researchclaw.app.crons.api", "/api/crons", ["Crons"]),
    ("researchclaw.app.runner.api", "/api/runner", ["Runner"]),
]:
    try:
        import importlib as _il

        _mod = _il.import_module(_mod_path)
        app.include_router(_mod.router, prefix=_prefix, tags=_tags)
    except Exception as e:
        logger.warning("Router %s could not be loaded: %s", _mod_path, e)

# Voice router uses Twilio-facing root paths (not /api)
try:
    from .routers.voice import voice_router

    app.include_router(voice_router, tags=["Voice"])
except Exception as e:
    logger.warning("Voice router could not be loaded: %s", e)


# ── Console (SPA) static file serving ──────────────────────────────────────


def _find_console_dir() -> Path | None:
    """Find the console build directory."""
    # 1. Package-bundled console
    pkg_console = Path(__file__).parent.parent / "console"
    if (pkg_console / "index.html").exists():
        return pkg_console

    # 2. Development: console/dist
    dev_console = (
        Path(__file__).parent.parent.parent.parent / "console" / "dist"
    )
    if (dev_console / "index.html").exists():
        return dev_console

    return None


_console_dir = _find_console_dir()

if _console_dir:
    # Mount static assets
    assets_dir = _console_dir / "assets"
    if assets_dir.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=str(assets_dir)),
            name="assets",
        )

    @app.get("/")
    async def serve_index():
        """Serve the console SPA index page."""
        return FileResponse(str(_console_dir / "index.html"))

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        """SPA fallback – serve index.html for all non-API routes."""
        if path.startswith("api/"):
            return JSONResponse({"error": "Not found"}, status_code=404)

        file_path = _console_dir / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))

        return FileResponse(str(_console_dir / "index.html"))

else:

    @app.get("/")
    async def no_console():
        """Fallback when console is not built."""
        return HTMLResponse(
            "<h1>ResearchClaw</h1>"
            "<p>Console not found. Build it with <code>cd console && npm run build</code></p>"
            f"<p>API is available at <a href='/docs'>/docs</a> (if enabled)</p>"
            f"<p>Version: {__version__}</p>",
        )
