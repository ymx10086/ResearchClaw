"""Core configuration read/write helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from researchclaw.constant import WORKING_DIR


def config_path() -> Path:
    return Path(WORKING_DIR) / "config.json"


def load_config() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_config(data: dict[str, Any]) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
