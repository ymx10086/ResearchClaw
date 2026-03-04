"""App/server related CLI commands."""

from __future__ import annotations

import logging
import os

import click
import uvicorn

from ..constant import DEFAULT_HOST, DEFAULT_PORT, LOG_LEVEL_ENV
from ..utils.logging import setup_logger


class _SuppressPathAccessLogFilter(logging.Filter):
    """Suppress uvicorn access-log entries whose path contains a substring."""

    def __init__(self, paths: list[str]) -> None:
        super().__init__()
        self._paths = paths

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not any(p in msg for p in self._paths)


@click.command("app")
@click.option(
    "--host",
    default=DEFAULT_HOST,
    show_default=True,
    help="Bind host",
)
@click.option(
    "--port",
    default=DEFAULT_PORT,
    type=int,
    show_default=True,
    help="Bind port",
)
@click.option("--reload", is_flag=True, help="Enable auto-reload (dev only)")
@click.option(
    "--workers",
    default=1,
    type=int,
    show_default=True,
    help="Worker processes",
)
@click.option(
    "--log-level",
    default="info",
    type=click.Choice(
        ["critical", "error", "warning", "info", "debug", "trace"],
        case_sensitive=False,
    ),
    show_default=True,
    help="Log level",
)
@click.option(
    "--hide-access-paths",
    multiple=True,
    default=("/console/push-messages",),
    show_default=True,
    help="Path substrings to hide from uvicorn access log (repeatable).",
)
def app_cmd(
    host: str,
    port: int,
    reload: bool,
    workers: int,
    log_level: str,
    hide_access_paths: tuple[str, ...],
) -> None:
    """Run ResearchClaw FastAPI app."""
    os.environ[LOG_LEVEL_ENV] = log_level
    setup_logger(log_level)

    if log_level in ("debug", "trace"):
        try:
            from .main import log_init_timings

            log_init_timings()
        except ImportError:
            pass

    paths = [p for p in hide_access_paths if p]
    if paths:
        logging.getLogger("uvicorn.access").addFilter(
            _SuppressPathAccessLogFilter(paths),
        )

    uvicorn.run(
        "researchclaw.app._app:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level=log_level,
    )
