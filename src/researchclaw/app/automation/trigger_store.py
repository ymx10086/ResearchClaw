"""In-memory store for automation trigger run history."""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AutomationRunStore:
    """Keeps a bounded history of automation trigger runs."""

    def __init__(self, max_runs: int = 200) -> None:
        self._max_runs = max(20, int(max_runs))
        self._runs: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self._lock = asyncio.Lock()

    async def create(
        self,
        *,
        run_id: str,
        message: str,
        session_id: str,
        deliver: bool,
        dispatches: List[Dict[str, str]],
        source: str = "api",
        agent_id: str = "",
    ) -> Dict[str, Any]:
        run = {
            "id": run_id,
            "status": "queued",
            "source": source,
            "agent_id": agent_id,
            "message": message,
            "session_id": session_id,
            "deliver": bool(deliver),
            "dispatches": dispatches,
            "created_at": _iso_now(),
            "started_at": None,
            "finished_at": None,
            "response": None,
            "error": None,
            "delivery_results": [],
        }
        async with self._lock:
            self._runs[run_id] = run
            while len(self._runs) > self._max_runs:
                self._runs.popitem(last=False)
            return deepcopy(run)

    async def mark_running(self, run_id: str) -> Dict[str, Any] | None:
        async with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return None
            run["status"] = "running"
            run["started_at"] = _iso_now()
            return deepcopy(run)

    async def mark_success(
        self,
        run_id: str,
        *,
        response: str,
        delivery_results: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any] | None:
        async with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return None
            run["status"] = "succeeded"
            run["finished_at"] = _iso_now()
            run["response"] = response
            run["delivery_results"] = list(delivery_results or [])
            return deepcopy(run)

    async def mark_failed(
        self,
        run_id: str,
        *,
        error: str,
        delivery_results: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any] | None:
        async with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return None
            run["status"] = "failed"
            run["finished_at"] = _iso_now()
            run["error"] = error
            run["delivery_results"] = list(delivery_results or [])
            return deepcopy(run)

    async def get(self, run_id: str) -> Dict[str, Any] | None:
        async with self._lock:
            run = self._runs.get(run_id)
            return deepcopy(run) if run is not None else None

    async def list(self, limit: int = 50) -> List[Dict[str, Any]]:
        cap = max(1, min(int(limit), self._max_runs))
        async with self._lock:
            items = list(self._runs.values())[-cap:]
            items.reverse()
            return [deepcopy(item) for item in items]

    async def stats(self) -> Dict[str, int]:
        async with self._lock:
            out = {
                "total": len(self._runs),
                "queued": 0,
                "running": 0,
                "succeeded": 0,
                "failed": 0,
            }
            for run in self._runs.values():
                status = str(run.get("status", "")).lower()
                if status in out:
                    out[status] += 1
            return out
