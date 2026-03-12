from __future__ import annotations

import asyncio
from types import SimpleNamespace

from researchclaw.app.routers import agent as agent_router


def test_agent_status_prefers_runner_snapshot() -> None:
    snapshot = {
        "running": True,
        "agent_name": "lab",
        "tool_count": 3,
        "tool_names": ["search", "read", "write"],
        "agents": [{"id": "lab", "running": True}],
    }
    runner = SimpleNamespace(get_status_snapshot=lambda: snapshot)
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(runner=runner)))

    result = asyncio.run(agent_router.agent_status(req))

    assert result == snapshot


def test_list_tools_prefers_runner_snapshot() -> None:
    runner = SimpleNamespace(
        get_status_snapshot=lambda: {"tool_names": ["search", "read"]},
        agent=None,
    )
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(runner=runner)))

    result = asyncio.run(agent_router.list_tools(req))

    assert result == {"tools": ["search", "read"]}
