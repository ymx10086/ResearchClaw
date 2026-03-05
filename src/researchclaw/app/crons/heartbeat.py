"""Heartbeat: run agent with HEARTBEAT.md as query at scheduled intervals.

Uses config functions for paths and settings. Supports active hours
filtering and optional dispatch to the last active channel.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Any, Dict

from ...constant import WORKING_DIR

logger = logging.getLogger(__name__)

# Pattern for "30m", "1h", "2h30m", "90s"
_EVERY_PATTERN = re.compile(
    r"^(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?(?:(?P<seconds>\d+)s)?$",
    re.IGNORECASE,
)

# Default heartbeat target constant
HEARTBEAT_TARGET_LAST = "last"


def parse_heartbeat_every(every: str) -> int:
    """Parse interval string (e.g. '30m', '1h') to total seconds.

    Examples:
        >>> parse_heartbeat_every('30m')
        1800
        >>> parse_heartbeat_every('1h')
        3600
        >>> parse_heartbeat_every('2h30m')
        9000
        >>> parse_heartbeat_every('')
        1800
    """
    every = (every or "").strip()
    if not every:
        return 30 * 60  # default 30 min

    m = _EVERY_PATTERN.match(every)
    if not m:
        logger.warning("heartbeat every=%r invalid, using 30m", every)
        return 30 * 60

    hours = int(m.group("hours") or 0)
    minutes = int(m.group("minutes") or 0)
    seconds = int(m.group("seconds") or 0)
    total = hours * 3600 + minutes * 60 + seconds
    if total <= 0:
        return 30 * 60
    return total


def _in_active_hours(active_hours: Any) -> bool:
    """Return True if current local time is within [start, end].

    Handles wrapping around midnight (e.g. 22:00 - 06:00).
    """
    if (
        not active_hours
        or not hasattr(active_hours, "start")
        or not hasattr(active_hours, "end")
    ):
        return True

    try:
        start_parts = active_hours.start.strip().split(":")
        end_parts = active_hours.end.strip().split(":")
        start_t = dt_time(
            int(start_parts[0]),
            int(start_parts[1]) if len(start_parts) > 1 else 0,
        )
        end_t = dt_time(
            int(end_parts[0]),
            int(end_parts[1]) if len(end_parts) > 1 else 0,
        )
    except (ValueError, IndexError, AttributeError):
        return True

    now = datetime.now().time()
    if start_t <= end_t:
        return start_t <= now <= end_t
    # Wraps around midnight
    return now >= start_t or now <= end_t


async def run_heartbeat_once(
    *,
    runner: Any,
    channel_manager: Any,
) -> None:
    """Run one heartbeat: read HEARTBEAT.md, run the agent, optionally dispatch.

    Reads the heartbeat query from HEARTBEAT.md in the working directory.
    If config has target='last' and there's a last dispatch record,
    sends results to that channel. Otherwise, runs agent-only.

    Args:
        runner: Agent runner with stream_query method
        channel_manager: Channel manager for dispatching results
    """
    working_dir = Path(WORKING_DIR)

    # Try to get heartbeat config
    hb_config = _get_heartbeat_config_safe()

    if hb_config and not _in_active_hours(
        getattr(hb_config, "active_hours", None),
    ):
        logger.debug("heartbeat skipped: outside active hours")
        return

    # Find the heartbeat query file
    path = _get_heartbeat_query_path(working_dir)
    if not path or not path.is_file():
        logger.debug("heartbeat skipped: no HEARTBEAT.md file found")
        return

    query_text = path.read_text(encoding="utf-8").strip()
    if not query_text:
        logger.debug("heartbeat skipped: empty query file")
        return

    # Build request: single user message with query text
    req: Dict[str, Any] = {
        "input": [
            {
                "role": "user",
                "content": [{"type": "text", "text": query_text}],
            },
        ],
        "session_id": "main",
        "user_id": "main",
    }

    # Check if we should dispatch to the last active channel
    target = ""
    last_dispatch = None
    if hb_config:
        target = (getattr(hb_config, "target", "") or "").strip().lower()
        last_dispatch = _get_last_dispatch_safe()

    if (
        target == HEARTBEAT_TARGET_LAST
        and last_dispatch
        and channel_manager is not None
    ):
        ld_channel = getattr(last_dispatch, "channel", None)
        ld_user_id = getattr(last_dispatch, "user_id", None)
        ld_session_id = getattr(last_dispatch, "session_id", None)

        if ld_channel and (ld_user_id or ld_session_id):

            async def _run_and_dispatch() -> None:
                async for event in runner.stream_query(req):
                    await channel_manager.send_event(
                        channel=ld_channel,
                        user_id=ld_user_id,
                        session_id=ld_session_id,
                        event=event,
                        meta={},
                    )

            try:
                await asyncio.wait_for(_run_and_dispatch(), timeout=120)
            except asyncio.TimeoutError:
                logger.warning("heartbeat run timed out")
            return

    # No dispatch target: run agent only
    async def _run_only() -> None:
        async for _ in runner.stream_query(req):
            pass

    try:
        await asyncio.wait_for(_run_only(), timeout=120)
    except asyncio.TimeoutError:
        logger.warning("heartbeat run timed out")

    # Write heartbeat status
    _write_heartbeat_status(working_dir)


def _get_heartbeat_config_safe() -> Any:
    """Safely get heartbeat config, returning None if not available."""
    try:
        from ...config import get_heartbeat_config

        return get_heartbeat_config()
    except (ImportError, Exception):
        return None


def _get_last_dispatch_safe() -> Any:
    """Safely get last dispatch record from config."""
    try:
        from ...config import load_config

        config = load_config()
        if isinstance(config, dict):
            last = config.get("last_dispatch")
            if isinstance(last, dict):
                from types import SimpleNamespace

                return SimpleNamespace(**last)
            return None
        return getattr(config, "last_dispatch", None)
    except (ImportError, Exception):
        return None


def _get_heartbeat_query_path(working_dir: Path) -> Path | None:
    """Find the HEARTBEAT.md file in the working directory."""
    # Try config-based path first
    try:
        from ...config import get_heartbeat_query_path

        return get_heartbeat_query_path()
    except (ImportError, Exception):
        pass

    # Fallback: check common locations
    candidates = [
        working_dir / "md_files" / "HEARTBEAT.md",
        working_dir / "HEARTBEAT.md",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def _write_heartbeat_status(working_dir: Path) -> None:
    """Write heartbeat status file for monitoring."""
    hb_file = working_dir / "heartbeat.json"
    hb_file.parent.mkdir(parents=True, exist_ok=True)
    hb_file.write_text(
        json.dumps(
            {"timestamp": time.time(), "status": "alive"},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
