from __future__ import annotations

import asyncio

from researchclaw.app.runner.manager import AgentRunnerManager


class _FakeRunner:
    def __init__(self):
        self.is_running = True
        self._attempt = 0

    async def restart(self, model_config):
        self._attempt += 1

    async def chat_stream(self, message: str, session_id: str | None = None):
        if self._attempt == 0:
            yield {"type": "error", "content": "primary failed"}
            return
        yield {"type": "content", "content": "hello"}
        yield {"type": "content", "content": " world"}
        yield {"type": "done", "content": "hello world"}


def test_chat_stream_fallback_records_usage(tmp_path) -> None:
    manager = AgentRunnerManager(
        working_dir=str(tmp_path),
        model_config={
            "provider": "openai",
            "model_name": "gpt-main",
            "fallbacks": [
                {"provider": "anthropic", "model_name": "claude-fallback"},
            ],
        },
        agent_id="research",
    )
    manager.runner = _FakeRunner()

    async def _run():
        rows = []
        async for event in manager.chat_stream("ping", session_id="s1"):
            rows.append(event)
        return rows

    events = asyncio.run(_run())
    assert events[-1]["type"] == "done"
    assert events[-1]["content"] == "hello world"

    stats = manager.get_usage_stats()
    assert stats["requests"] == 2
    assert stats["succeeded"] == 1
    assert stats["failed"] == 1
    assert stats["fallbacks"] == 1

    session = manager.session_manager.get_session("s1")
    assert session is not None
    assert any(
        m["role"] == "assistant" and m["content"] == "hello world"
        for m in session.messages
    )


def test_start_loads_active_provider_from_provider_store(
    tmp_path, monkeypatch
) -> None:
    import researchclaw.providers.store as provider_store

    (tmp_path / "config.json").write_text(
        '{"language":"zh"}',
        encoding="utf-8",
    )

    class _FakeProvider:
        def to_dict(self):
            return {
                "name": "lab-openai",
                "provider_type": "openai",
                "model_name": "gpt-lab",
                "api_key": "sk-test",
                "base_url": "https://example.test/v1",
                "enabled": True,
            }

    class _FakeStore:
        def get_active_provider(self):
            return _FakeProvider()

    class _BootRunner:
        def __init__(self):
            self.is_running = False
            self.started_with = None

        async def start(self, model_config):
            self.started_with = dict(model_config)
            self.is_running = True

    monkeypatch.setattr(provider_store, "ProviderStore", _FakeStore)

    manager = AgentRunnerManager(working_dir=str(tmp_path))
    manager.runner = _BootRunner()

    asyncio.run(manager.start())

    assert manager.runner.started_with is not None
    assert manager.runner.started_with["provider"] == "openai"
    assert manager.runner.started_with["model_name"] == "gpt-lab"
    assert manager.runner.started_with["api_key"] == "sk-test"
    assert manager.runner.started_with["base_url"] == "https://example.test/v1"
