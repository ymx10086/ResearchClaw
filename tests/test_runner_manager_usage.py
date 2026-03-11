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
