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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ..__version__ import __version__
from ..constant import CORS_ORIGINS, DOCS_ENABLED, WORKING_DIR

logger = logging.getLogger(__name__)

# Fix common MIME types
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")


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

    try:
        from .runner.manager import AgentRunnerManager

        runner = AgentRunnerManager()
        await runner.start()
        app.state.runner = runner
        logger.info("Agent runner started")
    except Exception:
        logger.exception("Failed to start agent runner")

    try:
        from .channels.manager import ChannelManager
        from .channels.registry import register_default_channels

        channel_manager = ChannelManager()
        register_default_channels(channel_manager)
        await channel_manager.start_all()
        app.state.channel_manager = channel_manager
        logger.info("Channel manager started")
    except Exception:
        logger.debug("Channel manager not started", exc_info=True)

    try:
        from .mcp.manager import MCPManager
        from .mcp.watcher import MCPWatcher

        mcp_manager = MCPManager()
        await mcp_manager.start()
        mcp_watcher = MCPWatcher()
        await mcp_watcher.start()
        app.state.mcp_manager = mcp_manager
        app.state.mcp_watcher = mcp_watcher
        logger.info("MCP manager started")
    except Exception:
        logger.debug("MCP manager not started", exc_info=True)

    try:
        from .crons.manager import CronManager
        from .crons.deadline_reminder import deadline_reminder
        from .crons.heartbeat import heartbeat_ping
        from .crons.paper_digest import paper_digest
        from ..constant import HEARTBEAT_ENABLED, HEARTBEAT_INTERVAL_MINUTES

        cron = CronManager()
        cron.register(
            "heartbeat",
            heartbeat_ping,
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
        logger.info("Cron manager started")
    except Exception:
        logger.debug("Cron manager not started", exc_info=True)

    yield

    # Shutdown
    logger.info("ResearchClaw shutting down...")
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

try:
    from .routers import (
        agent,
        config,
        console,
        control,
        envs,
        mcp,
        papers,
        providers,
        skills,
        workspace,
    )
    from .crons.api import router as cron_router
    from .runner.api import router as runner_router

    app.include_router(agent.router, prefix="/api/agent", tags=["Agent"])
    app.include_router(config.router, prefix="/api/config", tags=["Config"])
    app.include_router(console.router, prefix="/api/console", tags=["Console"])
    app.include_router(control.router, prefix="/api/control", tags=["Control"])
    app.include_router(cron_router, prefix="/api/crons", tags=["Crons"])
    app.include_router(envs.router, prefix="/api/envs", tags=["Environments"])
    app.include_router(mcp.router, prefix="/api/mcp", tags=["MCP"])
    app.include_router(papers.router, prefix="/api/papers", tags=["Papers"])
    app.include_router(
        providers.router,
        prefix="/api/providers",
        tags=["Providers"],
    )
    app.include_router(runner_router, prefix="/api/runner", tags=["Runner"])
    app.include_router(skills.router, prefix="/api/skills", tags=["Skills"])
    app.include_router(
        workspace.router,
        prefix="/api/workspace",
        tags=["Workspace"],
    )
except ImportError as e:
    logger.warning("Some routers could not be loaded: %s", e)


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
