"""Persistent JSON store for research workflows and linked graph state."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from researchclaw.constant import RESEARCH_DIR, RESEARCH_STATE_FILE

from .models import ResearchState


class JsonResearchStore:
    """Single-file JSON persistence for the research domain."""

    def __init__(self, path: str | Path | None = None) -> None:
        if path is None:
            env_path = os.environ.get("RESEARCHCLAW_RESEARCH_STATE_PATH", "").strip()
            path = env_path or (Path(RESEARCH_DIR) / RESEARCH_STATE_FILE)
        self._path = Path(path).expanduser().resolve()
        self._lock = asyncio.Lock()

    @property
    def path(self) -> Path:
        return self._path

    async def load(self) -> ResearchState:
        async with self._lock:
            if not self._path.exists():
                return ResearchState()
            payload = self._path.read_text(encoding="utf-8")
            return ResearchState.model_validate_json(payload)

    async def save(self, state: ResearchState) -> None:
        async with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
            payload = state.model_dump(mode="json")
            tmp_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            tmp_path.replace(self._path)
