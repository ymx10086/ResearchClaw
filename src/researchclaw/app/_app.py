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
from ..constant import (
    CORS_ORIGINS,
    DOCS_ENABLED,
    WORKING_DIR,
)
from ..envs import load_envs_into_environ
from ..utils.logging import add_researchclaw_file_handler
from .gateway.runtime import (
    bootstrap_gateway_runtime,
    shutdown_gateway_runtime,
)

logger = logging.getLogger(__name__)

# Ensure persisted envs are applied before service components boot.
load_envs_into_environ()

# Fix common MIME types
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")


# ── Lifecycle ───────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    logger.info("ResearchClaw v%s starting up...", __version__)
    add_researchclaw_file_handler(Path(WORKING_DIR) / "researchclaw.log")

    # Ensure working directory exists
    os.makedirs(WORKING_DIR, exist_ok=True)
    app.state.started_at = time.time()
    await bootstrap_gateway_runtime(app)

    yield

    # Shutdown
    logger.info("ResearchClaw shutting down...")
    await shutdown_gateway_runtime(app)


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
    ("researchclaw.app.routers.automation", "/api/automation", ["Automation"]),
    ("researchclaw.app.routers.config", "/api/config", ["Config"]),
    ("researchclaw.app.routers.console", "/api/console", ["Console"]),
    ("researchclaw.app.routers.control", "/api/control", ["Control"]),
    ("researchclaw.app.routers.envs", "/api/envs", ["Environments"]),
    (
        "researchclaw.app.routers.local_models",
        "/api",
        ["LocalModels"],
    ),
    ("researchclaw.app.routers.mcp", "/api/mcp", ["MCP"]),
    (
        "researchclaw.app.routers.ollama_models",
        "/api",
        ["OllamaModels"],
    ),
    ("researchclaw.app.routers.papers", "/api/papers", ["Papers"]),
    ("researchclaw.app.routers.providers", "/api/providers", ["Providers"]),
    ("researchclaw.app.routers.research", "/api/research", ["Research"]),
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

    def _console_index_response() -> HTMLResponse | FileResponse:
        index_path = _console_dir / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return HTMLResponse(
            "<h1>ResearchClaw</h1>"
            "<p>Console build is temporarily unavailable. Rebuild with "
            "<code>cd console && npm run build</code></p>"
            f"<p>API is available at <a href='/docs'>/docs</a> (if enabled)</p>"
            f"<p>Version: {__version__}</p>",
            status_code=503,
        )

    # Mount static assets
    assets_dir = _console_dir / "assets"
    if assets_dir.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=str(assets_dir)),
            name="assets",
        )

    @app.api_route("/", methods=["GET", "HEAD"])
    async def serve_index():
        """Serve the console SPA index page."""
        return _console_index_response()

    @app.api_route("/{path:path}", methods=["GET", "HEAD"])
    async def serve_spa(path: str):
        """SPA fallback – serve index.html for all non-API routes."""
        if path.startswith("api/"):
            return JSONResponse({"error": "Not found"}, status_code=404)

        file_path = _console_dir / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))

        return _console_index_response()

else:

    @app.api_route("/", methods=["GET", "HEAD"])
    async def no_console():
        """Fallback when console is not built."""
        return HTMLResponse(
            "<h1>ResearchClaw</h1>"
            "<p>Console not found. Build it with <code>cd console && npm run build</code></p>"
            f"<p>API is available at <a href='/docs'>/docs</a> (if enabled)</p>"
            f"<p>Version: {__version__}</p>",
        )
