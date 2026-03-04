"""Deadline reminder cron – alerts about upcoming conference/journal deadlines."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from researchclaw.constant import WORKING_DIR

logger = logging.getLogger(__name__)


async def deadline_reminder():
    """Check for upcoming deadlines and generate reminders.

    Reads deadlines from a user-maintained deadlines.json file and
    generates notifications for deadlines within the alert window.
    """
    deadlines_path = Path(WORKING_DIR) / "deadlines.json"

    if not deadlines_path.exists():
        logger.debug("No deadlines.json found, skipping reminder check")
        return

    try:
        deadlines = json.loads(deadlines_path.read_text(encoding="utf-8"))
    except Exception:
        logger.debug("Failed to parse deadlines.json")
        return

    if not isinstance(deadlines, list):
        return

    now = time.time()
    reminders = []

    for dl in deadlines:
        deadline_ts = dl.get("timestamp") or dl.get("deadline_timestamp")
        if not deadline_ts:
            continue

        days_remaining = (deadline_ts - now) / 86400

        if 0 < days_remaining <= 30:  # Alert for deadlines within 30 days
            reminders.append(
                {
                    "name": dl.get("name", "Unknown"),
                    "venue": dl.get("venue", ""),
                    "days_remaining": round(days_remaining, 1),
                    "deadline": dl.get("deadline", ""),
                    "url": dl.get("url", ""),
                },
            )

    if reminders:
        # Save reminders for the console or notification system
        reminders_path = Path(WORKING_DIR) / "reminders"
        reminders_path.mkdir(parents=True, exist_ok=True)

        reminder_file = reminders_path / f"reminder_{int(now)}.json"
        reminder_file.write_text(
            json.dumps(
                {"timestamp": now, "reminders": reminders},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        logger.info(
            "Generated %d deadline reminders (nearest: %s in %.1f days)",
            len(reminders),
            reminders[0]["name"],
            reminders[0]["days_remaining"],
        )
