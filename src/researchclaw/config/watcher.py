"""Simple config watcher placeholder."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Awaitable, Callable


class ConfigWatcher:
    def __init__(
        self,
        path: Path,
        callback: Callable[[], Awaitable[None]],
        interval_seconds: int = 2,
    ):
        self.path = path
        self.callback = callback
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task | None = None
        self._last_mtime = path.stat().st_mtime if path.exists() else 0.0

    async def start(self):
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self):
        while True:
            await asyncio.sleep(self.interval_seconds)
            if not self.path.exists():
                continue
            mtime = self.path.stat().st_mtime
            if mtime > self._last_mtime:
                self._last_mtime = mtime
                await self.callback()
