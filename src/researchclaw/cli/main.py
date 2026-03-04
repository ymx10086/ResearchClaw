"""Main CLI entry for ResearchClaw."""

from __future__ import annotations

import logging
import sys
import time

import click

# On Windows, force UTF-8 for stdout/stderr.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

logger = logging.getLogger(__name__)
_init_timings: list[tuple[str, float]] = []
_t0_main = time.perf_counter()
_init_timings.append(("main.py loaded", 0.0))


def _record(label: str, elapsed: float) -> None:
    _init_timings.append((label, elapsed))
    logger.debug("%.3fs %s", elapsed, label)


# Timed imports (order intentional).
_t = time.perf_counter()
from .app_cmd import app_cmd  # noqa: E402

_record(".app_cmd", time.perf_counter() - _t)

_t = time.perf_counter()
from .channels_cmd import channels_group  # noqa: E402

_record(".channels_cmd", time.perf_counter() - _t)

_t = time.perf_counter()
from .chats_cmd import chats_group  # noqa: E402

_record(".chats_cmd", time.perf_counter() - _t)

_t = time.perf_counter()
from .clean_cmd import clean_cmd  # noqa: E402

_record(".clean_cmd", time.perf_counter() - _t)

_t = time.perf_counter()
from .cron_cmd import cron_group  # noqa: E402

_record(".cron_cmd", time.perf_counter() - _t)

_t = time.perf_counter()
from .env_cmd import env_group  # noqa: E402

_record(".env_cmd", time.perf_counter() - _t)

_t = time.perf_counter()
from .init_cmd import init_cmd  # noqa: E402

_record(".init_cmd", time.perf_counter() - _t)

_t = time.perf_counter()
from .papers_cmd import papers  # noqa: E402

_record(".papers_cmd", time.perf_counter() - _t)

_t = time.perf_counter()
from .providers_cmd import models_group  # noqa: E402

_record(".providers_cmd", time.perf_counter() - _t)

_t = time.perf_counter()
from .skills_cmd import skills_group  # noqa: E402

_record(".skills_cmd", time.perf_counter() - _t)

_t = time.perf_counter()
from .uninstall_cmd import uninstall_cmd  # noqa: E402

_record(".uninstall_cmd", time.perf_counter() - _t)

_total = time.perf_counter() - _t0_main
_init_timings.append(("(total imports)", _total))
logger.debug("%.3fs (total imports)", _total)

from ..__version__ import __version__  # noqa: E402
from ..constant import DEFAULT_HOST, DEFAULT_PORT  # noqa: E402


def log_init_timings() -> None:
    """Emit init timing debug lines after setup_logger(debug) in app_cmd."""
    for label, elapsed in _init_timings:
        logger.debug("%.3fs %s", elapsed, label)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="researchclaw")
@click.option("--host", default=None, help="API Host")
@click.option("--port", default=None, type=int, help="API Port")
@click.pass_context
def cli(ctx: click.Context, host: str | None, port: int | None) -> None:
    """ResearchClaw – AI assistant for researchers."""
    host = host or DEFAULT_HOST
    port = port or DEFAULT_PORT
    ctx.ensure_object(dict)
    ctx.obj["host"] = host
    ctx.obj["port"] = port


cli.add_command(app_cmd, "app")
cli.add_command(channels_group)
cli.add_command(chats_group)
cli.add_command(clean_cmd)
cli.add_command(cron_group)
cli.add_command(env_group, "env")
cli.add_command(init_cmd, "init")
cli.add_command(models_group, "models")
cli.add_command(papers)
cli.add_command(skills_group, "skills")
cli.add_command(uninstall_cmd)


if __name__ == "__main__":
    cli()
