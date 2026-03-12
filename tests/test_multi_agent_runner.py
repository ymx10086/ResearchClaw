from __future__ import annotations

import asyncio
from types import SimpleNamespace

from researchclaw.app.runner import multi_manager as mm


class _FakeSession:
    def __init__(self, session_id: str):
        self.session_id = session_id

    def to_dict(self):
        return {"session_id": self.session_id}


class _FakeSessionManager:
    def __init__(self, agent_id: str):
        self._agent_id = agent_id
        self._sessions = {
            "main": _FakeSession("main"),
            f"{agent_id}-s1": _FakeSession(f"{agent_id}-s1"),
        }

    def list_sessions(self):
        return [
            {
                "session_id": sid,
                "title": f"{self._agent_id}-{sid}",
                "updated_at": 100 if sid == "main" else 90,
            }
            for sid in self._sessions
        ]

    def get_session(self, session_id: str):
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str):
        self._sessions.pop(session_id, None)


class _FakeAgentRunnerManager:
    def __init__(
        self,
        *,
        working_dir=None,
        model_config=None,
        agent_id="main",
    ):
        self.agent_id = agent_id
        self.working_dir = str(working_dir or "")
        self._model_config = dict(model_config or {})
        self.session_manager = _FakeSessionManager(agent_id)
        self.is_running = False
        self.agent = SimpleNamespace(tool_names=["t1", "t2"])
        self.runner = SimpleNamespace(_last_model_config=self._model_config)
        self._chat_manager = None

    async def start(self):
        self.is_running = True

    async def stop(self):
        self.is_running = False

    def set_chat_manager(self, chat_manager):
        self._chat_manager = chat_manager

    def set_mcp_manager(self, mcp_manager):
        return None

    async def refresh_mcp_clients(self, force=False):
        return None

    async def chat(self, message: str, session_id: str | None = None):
        return f"{self.agent_id}:{session_id}:{message}"

    async def chat_stream(self, message: str, session_id: str | None = None):
        yield {"type": "done", "content": f"{self.agent_id}:{message}"}

    async def stream_query(self, request):
        yield {
            "object": "message",
            "status": "completed",
            "type": "content",
            "content": f"ok:{self.agent_id}",
        }

    async def apply_provider(self, model_config):
        self._model_config = dict(model_config or {})

    def get_usage_stats(self):
        return {
            "agent_id": self.agent_id,
            "requests": 1,
            "succeeded": 1,
            "failed": 0,
            "fallbacks": 0,
            "input_tokens": 10,
            "output_tokens": 20,
            "providers": [
                {
                    "provider": "openai",
                    "model_name": "gpt-test",
                    "requests": 1,
                    "succeeded": 1,
                    "failed": 0,
                    "input_tokens": 10,
                    "output_tokens": 20,
                },
            ],
        }


def test_multi_agent_reload_and_default_selection(monkeypatch):
    monkeypatch.setattr(mm, "AgentRunnerManager", _FakeAgentRunnerManager)
    cfg = {
        "agents": {
            "defaults": {"default_agent_id": "research"},
            "list": [
                {"id": "main", "workspace": "./w-main"},
                {"id": "research", "workspace": "./w-research"},
            ],
        },
    }
    manager = mm.MultiAgentRunnerManager(config_loader=lambda: cfg)

    asyncio.run(manager.reload_from_config())
    agents = manager.list_agents()

    assert manager.default_agent_id == "research"
    assert {item["id"] for item in agents} == {"main", "research"}
    assert all("workspace" in item for item in agents)


def test_multi_agent_stream_query_binding(monkeypatch):
    monkeypatch.setattr(mm, "AgentRunnerManager", _FakeAgentRunnerManager)
    cfg = {
        "agents": {
            "defaults": {"default_agent_id": "main"},
            "list": [{"id": "main"}, {"id": "papers"}],
        },
        "bindings": [
            {
                "agent_id": "papers",
                "match": {"channel": "telegram", "user_id": "alice"},
            },
        ],
    }
    manager = mm.MultiAgentRunnerManager(config_loader=lambda: cfg)
    asyncio.run(manager.reload_from_config())

    request = {
        "channel": "telegram",
        "user_id": "alice",
        "session_id": "telegram:alice",
        "input": [
            {"role": "user", "content": [{"type": "text", "text": "hi"}]},
        ],
    }

    async def _run():
        rows = []
        async for event in manager.stream_query(request):
            rows.append(event)
        return rows

    events = asyncio.run(_run())
    assert manager._last_routed_agent_id == "papers"  # noqa: SLF001
    assert events and events[0].get("agent_id") == "papers"
    assert request.get("agent_id") == "papers"


def test_multi_agent_sessions_are_namespaced(monkeypatch):
    monkeypatch.setattr(mm, "AgentRunnerManager", _FakeAgentRunnerManager)
    cfg = {
        "agents": {
            "list": [{"id": "main"}, {"id": "lab"}],
        },
    }
    manager = mm.MultiAgentRunnerManager(config_loader=lambda: cfg)
    asyncio.run(manager.reload_from_config())

    all_rows = manager.list_sessions()
    lab_rows = manager.list_sessions(agent_id="lab")

    assert len(all_rows) >= len(lab_rows)
    assert all("agent_id" in row for row in all_rows)
    assert all(row["agent_id"] == "lab" for row in lab_rows)


def test_multi_agent_usage_stats_aggregate(monkeypatch):
    monkeypatch.setattr(mm, "AgentRunnerManager", _FakeAgentRunnerManager)
    cfg = {"agents": {"list": [{"id": "main"}, {"id": "lab"}]}}
    manager = mm.MultiAgentRunnerManager(config_loader=lambda: cfg)
    asyncio.run(manager.reload_from_config())

    stats = manager.list_usage_stats()
    assert stats["requests"] == 2
    assert len(stats["agents"]) == 2
    assert stats["providers"][0]["model_name"] == "gpt-test"


def test_multi_agent_running_reflects_any_running_agent(monkeypatch):
    monkeypatch.setattr(mm, "AgentRunnerManager", _FakeAgentRunnerManager)
    cfg = {"agents": {"defaults": {"default_agent_id": "main"}, "list": [{"id": "main"}, {"id": "lab"}]}}
    manager = mm.MultiAgentRunnerManager(config_loader=lambda: cfg)
    asyncio.run(manager.reload_from_config())

    manager._agents["lab"].is_running = True  # noqa: SLF001

    assert manager.is_running is True


def test_multi_agent_status_snapshot_prefers_running_agent(monkeypatch):
    monkeypatch.setattr(mm, "AgentRunnerManager", _FakeAgentRunnerManager)
    cfg = {"agents": {"defaults": {"default_agent_id": "main"}, "list": [{"id": "main"}, {"id": "lab"}]}}
    manager = mm.MultiAgentRunnerManager(config_loader=lambda: cfg)
    asyncio.run(manager.reload_from_config())

    manager._agents["lab"].is_running = True  # noqa: SLF001
    manager._agents["lab"].agent = SimpleNamespace(tool_names=["search"])  # noqa: SLF001

    snapshot = manager.get_status_snapshot()

    assert snapshot["running"] is True
    assert snapshot["agent_name"] == "lab"
    assert snapshot["tool_count"] == 1
