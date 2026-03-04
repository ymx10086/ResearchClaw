"""Persistent store for model providers."""

from __future__ import annotations

import json
from pathlib import Path

from researchclaw.constant import WORKING_DIR

from .models import ProviderConfig


class ProviderStore:
    """Stores provider configurations in working directory."""

    def __init__(self, file_path: str | None = None):
        self.file_path = Path(
            file_path or (Path(WORKING_DIR) / "providers.json"),
        )
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def list_providers(self) -> list[dict]:
        return [item.to_dict() for item in self._load()]

    def save_provider(self, provider: dict) -> None:
        items = self._load()
        config = ProviderConfig.from_dict(provider)
        replaced = False
        for idx, item in enumerate(items):
            if item.name == config.name:
                items[idx] = config
                replaced = True
                break
        if not replaced:
            items.append(config)
        self._save(items)

    def remove_provider(self, name: str) -> None:
        items = self._load()
        new_items = [item for item in items if item.name != name]
        if len(new_items) == len(items):
            raise KeyError(name)
        self._save(new_items)

    def _load(self) -> list[ProviderConfig]:
        if not self.file_path.exists():
            return []
        data = json.loads(self.file_path.read_text(encoding="utf-8"))
        return [ProviderConfig.from_dict(item) for item in data]

    def _save(self, items: list[ProviderConfig]) -> None:
        self.file_path.write_text(
            json.dumps(
                [item.to_dict() for item in items],
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
