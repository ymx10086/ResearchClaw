"""Persisted environment profile store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from researchclaw.constant import WORKING_DIR


class EnvStore:
    """Stores named environment profiles in JSON."""

    def __init__(self, file_path: str | None = None):
        self.file_path = Path(file_path or (Path(WORKING_DIR) / "envs.json"))
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def list(self) -> list[dict[str, Any]]:
        return self._load()

    def get(self, name: str) -> dict[str, Any] | None:
        for item in self._load():
            if item.get("name") == name:
                return item
        return None

    def save(self, profile: dict[str, Any]) -> None:
        items = self._load()
        updated = False
        for idx, item in enumerate(items):
            if item.get("name") == profile.get("name"):
                items[idx] = profile
                updated = True
                break
        if not updated:
            items.append(profile)
        self._save(items)

    def remove(self, name: str) -> None:
        items = [item for item in self._load() if item.get("name") != name]
        self._save(items)

    def _load(self) -> list[dict[str, Any]]:
        if not self.file_path.exists():
            return []
        return json.loads(self.file_path.read_text(encoding="utf-8"))

    def _save(self, items: list[dict[str, Any]]) -> None:
        self.file_path.write_text(
            json.dumps(items, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
