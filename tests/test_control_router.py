from __future__ import annotations

import asyncio
from types import SimpleNamespace

from researchclaw.app.routers import control as control_router


def test_deep_merge_keeps_nested_values() -> None:
    merged = control_router._deep_merge(
        {"agents": {"defaults": {"id": "main"}, "x": 1}, "a": 1},
        {"agents": {"defaults": {"id": "research"}}},
    )
    assert merged["agents"]["defaults"]["id"] == "research"
    assert merged["agents"]["x"] == 1
    assert merged["a"] == 1


def test_list_sessions_prefers_multi_agent_runner() -> None:
    runner = SimpleNamespace(
        list_sessions=lambda agent_id=None: [
            {"session_id": "s1", "agent_id": agent_id or "main"},
        ],
    )
    req = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(runner=runner)),
    )
    rows = asyncio.run(control_router.list_sessions(req, agent_id="papers"))
    assert rows == [{"session_id": "s1", "agent_id": "papers"}]


def test_apply_config_calls_runtime_hooks(monkeypatch) -> None:
    saved = {}

    def _load_config():
        return {"a": {"b": 1}}

    def _save_config(data):
        saved.update(data)

    monkeypatch.setattr(control_router, "load_config", _load_config)
    monkeypatch.setattr(control_router, "save_config", _save_config)

    class _Watcher:
        def __init__(self):
            self.called = False

        async def apply_now(self):
            self.called = True

    class _Runner:
        def __init__(self):
            self.called = False

        async def reload_from_config(self):
            self.called = True

        def list_agents(self):
            return [{"id": "main"}]

    watcher = _Watcher()
    runner = _Runner()
    req = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(config_watcher=watcher, runner=runner),
        ),
    )
    payload = control_router.ConfigApplyRequest(
        patch={"a": {"c": 2}},
        replace=False,
    )

    result = asyncio.run(control_router.apply_config(req, payload))

    assert saved == {"a": {"b": 1, "c": 2}}
    assert watcher.called is True
    assert runner.called is True
    assert result["applied"] is True


def test_usage_stats_prefers_runner_usage_api() -> None:
    runner = SimpleNamespace(
        list_usage_stats=lambda agent_id=None: {
            "requests": 3,
            "succeeded": 2,
            "failed": 1,
            "fallbacks": 1,
            "providers": [],
            "agents": [],
        },
    )
    req = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(runner=runner)),
    )
    result = asyncio.run(control_router.usage_stats(req))
    assert result["requests"] == 3
    assert result["fallbacks"] == 1


def test_update_bindings_updates_root_and_agents(monkeypatch) -> None:
    saved = {}

    def _load_config():
        return {"agents": {"defaults": {"default_agent_id": "main"}}}

    def _save_config(data):
        saved.update(data)

    monkeypatch.setattr(
        control_router,
        "load_config",
        _load_config,
    )
    monkeypatch.setattr(control_router, "save_config", _save_config)

    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    payload = control_router.BindingsUpdateRequest(
        bindings=[{"agent_id": "research", "match": {"channel": "telegram"}}],
    )
    out = asyncio.run(control_router.update_bindings(req, payload))
    assert out["updated"] is True
    assert saved["bindings"][0]["agent_id"] == "research"
    assert saved["agents"]["bindings"][0]["agent_id"] == "research"


def test_install_and_remove_custom_channel(monkeypatch, tmp_path) -> None:
    saved = {}

    def _load_config():
        return {"channels": {}}

    def _save_config(data):
        saved.update(data)

    monkeypatch.setattr(control_router, "CUSTOM_CHANNELS_DIR", str(tmp_path))
    monkeypatch.setattr(control_router, "load_config", _load_config)
    monkeypatch.setattr(control_router, "save_config", _save_config)

    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    install_payload = control_router.ChannelInstallRequest(key="mychannel")
    installed = asyncio.run(
        control_router.install_custom_channel(req, install_payload),
    )
    assert installed["installed"] is True
    assert (tmp_path / "mychannel.py").exists()
    assert "mychannel" in saved["channels"]["available"]

    removed = asyncio.run(
        control_router.remove_custom_channel(req, "mychannel"),
    )
    assert removed["removed"] is True
    assert not (tmp_path / "mychannel.py").exists()
