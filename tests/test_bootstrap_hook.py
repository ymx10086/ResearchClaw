from __future__ import annotations

import json
from pathlib import Path

from researchclaw.agents.hooks.bootstrap import BootstrapHook


class _DummyAgent:
    def __init__(self, working_dir: Path):
        self.working_dir = str(working_dir)
        self.rebuild_calls = 0

    def rebuild_sys_prompt(self) -> None:
        self.rebuild_calls += 1


def test_bootstrap_gap_guidance_keeps_original_message_en(tmp_path: Path):
    hook = BootstrapHook(_DummyAgent(tmp_path))

    user_msg = "I already edited SOUL.md. What should I do next?"
    out = hook.pre_reply(user_msg)

    assert "[Setup incomplete]" in out
    assert "[Original user message]" in out
    assert user_msg in out


def test_bootstrap_gap_guidance_keeps_original_message_zh(tmp_path: Path):
    (tmp_path / "config.json").write_text(
        json.dumps({"language": "zh"}, ensure_ascii=False),
        encoding="utf-8",
    )
    hook = BootstrapHook(_DummyAgent(tmp_path))

    user_msg = "我已经改好了 SOUL.md，下一步做什么？"
    out = hook.pre_reply(user_msg)

    assert "【初始化未完成】" in out
    assert "【用户原始消息】" in out
    assert user_msg in out
