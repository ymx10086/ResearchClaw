"""Core configuration read/write helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from types import SimpleNamespace

from researchclaw.constant import WORKING_DIR


def config_path() -> Path:
    return Path(WORKING_DIR) / "config.json"


def load_config(path: Path | None = None) -> dict[str, Any]:
    path = path or config_path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_config(data: dict[str, Any], path: Path | None = None) -> None:
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def get_heartbeat_query_path() -> Path:
    """Return HEARTBEAT.md path (prefers md_files/)."""
    working = Path(WORKING_DIR)
    candidate = working / "md_files" / "HEARTBEAT.md"
    if candidate.exists():
        return candidate
    return working / "HEARTBEAT.md"


def get_heartbeat_config() -> Any:
    """Return heartbeat config as attribute-access object."""
    data = load_config()
    hb = (
        data.get("agents", {})
        .get("defaults", {})
        .get("heartbeat")
    )
    if not isinstance(hb, dict):
        hb = {}

    # Legacy top-level keys fallback
    if "heartbeat_enabled" in data and "enabled" not in hb:
        hb["enabled"] = bool(data.get("heartbeat_enabled"))
    if "heartbeat_every" in data and "every" not in hb:
        hb["every"] = str(data.get("heartbeat_every") or "").strip()
    if "heartbeat_target" in data and "target" not in hb:
        hb["target"] = str(data.get("heartbeat_target") or "").strip()

    merged: dict[str, Any] = {
        "enabled": bool(hb.get("enabled", False)),
        "every": str(hb.get("every") or "30m"),
        "target": str(hb.get("target") or "last"),
    }
    active = hb.get("active_hours") or hb.get("activeHours")
    if isinstance(active, dict):
        merged["active_hours"] = SimpleNamespace(
            start=str(active.get("start") or "08:00"),
            end=str(active.get("end") or "22:00"),
        )
    else:
        merged["active_hours"] = None
    return SimpleNamespace(**merged)


def update_last_dispatch(channel: str, user_id: str, session_id: str) -> None:
    """Persist last channel dispatch target for heartbeat target=last."""
    data = load_config()
    data["last_dispatch"] = {
        "channel": channel or "",
        "user_id": user_id or "",
        "session_id": session_id or "",
    }
    save_config(data)
