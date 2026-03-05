"""AgentRunnerManager – top-level manager for the agent runner lifecycle."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from researchclaw.app.runner.runner import AgentRunner
from researchclaw.app.runner.session import ChatSession, SessionManager
from researchclaw.app.channels.schema import DEFAULT_CHANNEL
from researchclaw.constant import WORKING_DIR

logger = logging.getLogger(__name__)


class AgentRunnerManager:
    """Coordinates agent runner and session management.

    Used in the FastAPI lifespan to start/stop the agent, and provides
    a unified interface for chat operations.
    """

    def __init__(self):
        self.runner = AgentRunner()
        self.session_manager = SessionManager()
        self._model_config: dict[str, Any] = {}
        self._chat_manager: Any = None

    @property
    def is_running(self) -> bool:
        return self.runner.is_running

    @property
    def agent(self):
        return self.runner.agent

    def set_chat_manager(self, chat_manager: Any) -> None:
        self._chat_manager = chat_manager

    def set_mcp_manager(self, mcp_manager: Any) -> None:
        self.runner.set_mcp_manager(mcp_manager)

    async def refresh_mcp_clients(self, force: bool = False) -> None:
        await self.runner.refresh_mcp_clients(force=force)

    @staticmethod
    def _extract_value(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    @staticmethod
    def _normalize_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return str(value)

    def _get_or_create_session(
        self,
        session_id: str | None,
    ) -> ChatSession:
        if session_id:
            existing = self.session_manager.get_session(session_id)
            if existing:
                return existing
            session = ChatSession(session_id=session_id)
            self.session_manager._sessions[session_id] = session
            self.session_manager._save_session(session)
            return session
        return self.session_manager.create_session()

    def _request_to_prompt(self, request: Any) -> str:
        """Flatten request.input[0].content into one textual prompt."""
        inp = self._extract_value(request, "input", []) or []
        if not inp:
            return ""
        first_msg = inp[0] if isinstance(inp, list) else inp
        contents = self._extract_value(first_msg, "content", []) or []
        if not isinstance(contents, list):
            contents = [contents]

        out: list[str] = []
        for item in contents:
            if isinstance(item, str):
                s = item.strip()
                if s:
                    out.append(s)
                continue

            t = self._extract_value(item, "type", "")
            t_val = (
                t.value if hasattr(t, "value") else str(t) if t else ""
            ).lower()
            if t_val == "text":
                txt = self._normalize_text(
                    self._extract_value(item, "text", ""),
                ).strip()
                if txt:
                    out.append(txt)
                continue
            if t_val == "refusal":
                txt = self._normalize_text(
                    self._extract_value(item, "refusal", ""),
                ).strip()
                if txt:
                    out.append(txt)
                continue
            if t_val == "image":
                url = self._normalize_text(
                    self._extract_value(item, "image_url", ""),
                ).strip()
                out.append(f"[Image: {url or 'uploaded image'}]")
                continue
            if t_val == "video":
                url = self._normalize_text(
                    self._extract_value(item, "video_url", ""),
                ).strip()
                out.append(f"[Video: {url or 'uploaded video'}]")
                continue
            if t_val == "file":
                file_ref = self._normalize_text(
                    self._extract_value(
                        item,
                        "file_url",
                        self._extract_value(item, "file_id", ""),
                    ),
                ).strip()
                out.append(f"[File: {file_ref or 'uploaded file'}]")
                continue
            if t_val == "audio":
                out.append("[Audio message]")
                continue

            txt = self._normalize_text(
                self._extract_value(item, "text", ""),
            ).strip()
            if txt:
                out.append(txt)

        return "\n".join(out).strip()

    @staticmethod
    def _build_message_event(
        *,
        event_type: str,
        content_items: list[dict[str, Any]],
    ) -> Any:
        return SimpleNamespace(
            object="message",
            status="completed",
            type=event_type,
            data=SimpleNamespace(
                content=[SimpleNamespace(**i) for i in content_items],
            ),
        )

    @staticmethod
    def _build_response_event(error_message: str | None = None) -> Any:
        err = (
            SimpleNamespace(message=error_message)
            if error_message
            else None
        )
        return SimpleNamespace(
            object="response",
            status="failed" if error_message else "completed",
            type="response",
            error=err,
        )

    async def start(self):
        """Start the agent runner with persisted config."""
        self._model_config = self._load_model_config()
        if self._model_config.get("model_name") or self._model_config.get(
            "api_key",
        ):
            try:
                await self.runner.start(self._model_config)
            except Exception:
                logger.warning(
                    "Failed to auto-start agent. "
                    "Configure model via CLI or API and restart.",
                )
        else:
            logger.info(
                "No model configured. Use 'researchclaw init' or the "
                "API to set up a model before chatting.",
            )

    async def stop(self):
        """Stop the agent runner."""
        await self.runner.stop()

    async def chat(self, message: str, session_id: str | None = None) -> str:
        """Send a chat message, creating a session if needed."""
        if not self.runner.is_running:
            # Try to start with current config
            await self.start()
            if not self.runner.is_running:
                return (
                    "Scholar is not ready. Please configure your LLM provider first.\n"
                    "Run `researchclaw init` or set up via Settings."
                )

        session = self._get_or_create_session(session_id)

        session.add_message("user", message)
        response = await self.runner.chat(message, session.session_id)
        session.add_message("assistant", response)
        self.session_manager._save_session(session)

        return response

    async def chat_stream(self, message: str, session_id: str | None = None):
        """Stream a chat response, yielding SSE event dicts."""
        if not self.runner.is_running:
            await self.start()
            if not self.runner.is_running:
                yield {
                    "type": "error",
                    "content": (
                        "Scholar is not ready. Please configure your LLM "
                        "provider first.\nRun `researchclaw init` or set "
                        "up via Settings."
                    ),
                }
                return

        session = self._get_or_create_session(session_id)

        session.add_message("user", message)
        full_content = ""

        async for event in self.runner.chat_stream(
            message,
            session.session_id,
        ):
            if event.get("type") == "done":
                full_content = event.get("content", full_content)
            yield event

        if full_content:
            session.add_message("assistant", full_content)
            self.session_manager._save_session(session)

    async def stream_query(self, request: Any):
        """CoPaw-compatible process adapter for channel manager.

        Accepts a channel-built request and yields Event-like objects with
        ``object/status/type`` fields expected by channel renderers.
        """
        session_id = self._extract_value(request, "session_id", None)
        user_id = self._normalize_text(
            self._extract_value(request, "user_id", ""),
        ).strip() or "main"
        channel = self._normalize_text(
            self._extract_value(request, "channel", DEFAULT_CHANNEL),
        ).strip() or DEFAULT_CHANNEL
        prompt = self._request_to_prompt(request)
        if not prompt:
            prompt = self._normalize_text(
                self._extract_value(request, "message", ""),
            )

        content_chunks: list[str] = []
        chat_spec = None
        if self._chat_manager and session_id:
            try:
                chat_spec = await self._chat_manager.get_or_create_chat(
                    session_id=session_id,
                    user_id=user_id,
                    channel=channel,
                    name=(prompt[:50] or "New Chat"),
                )
            except Exception:
                logger.debug(
                    "stream_query: auto-register chat failed",
                    exc_info=True,
                )

        try:
            async for raw_event in self.chat_stream(
                prompt,
                session_id=session_id,
            ):
                event_type = self._extract_value(raw_event, "type", "")
                if event_type == "thinking":
                    text = self._normalize_text(
                        self._extract_value(raw_event, "content", ""),
                    ).strip()
                    if text:
                        yield self._build_message_event(
                            event_type="thinking",
                            content_items=[
                                {"type": "thinking", "text": text},
                            ],
                        )
                    continue

                if event_type == "tool_call":
                    name = self._normalize_text(
                        self._extract_value(raw_event, "name", "tool"),
                    )
                    args = self._extract_value(raw_event, "arguments", "")
                    yield self._build_message_event(
                        event_type="tool_call",
                        content_items=[
                            {
                                "type": "tool_call",
                                "name": name,
                                "arguments": args,
                            },
                        ],
                    )
                    continue

                if event_type == "tool_result":
                    name = self._normalize_text(
                        self._extract_value(raw_event, "name", ""),
                    )
                    result = self._extract_value(raw_event, "result", "")
                    yield self._build_message_event(
                        event_type="tool_result",
                        content_items=[
                            {
                                "type": "tool_output",
                                "name": name,
                                "output": result,
                            },
                        ],
                    )
                    continue

                if event_type == "content":
                    chunk = self._normalize_text(
                        self._extract_value(raw_event, "content", ""),
                    )
                    if chunk:
                        content_chunks.append(chunk)
                    continue

                if event_type == "error":
                    err = self._normalize_text(
                        self._extract_value(raw_event, "content", ""),
                    ).strip()
                    if content_chunks:
                        yield self._build_message_event(
                            event_type="content",
                            content_items=[
                                {
                                    "type": "text",
                                    "text": "".join(content_chunks),
                                },
                            ],
                        )
                    yield self._build_response_event(
                        error_message=err or "Unknown error",
                    )
                    return

                if event_type == "done":
                    full_text = self._normalize_text(
                        self._extract_value(raw_event, "content", ""),
                    ).strip() or "".join(content_chunks).strip()
                    if full_text:
                        yield self._build_message_event(
                            event_type="content",
                            content_items=[
                                {"type": "text", "text": full_text},
                            ],
                        )
                    yield self._build_response_event()
                    return

                maybe_text = self._normalize_text(
                    self._extract_value(raw_event, "content", ""),
                )
                if maybe_text:
                    content_chunks.append(maybe_text)

            if content_chunks:
                yield self._build_message_event(
                    event_type="content",
                    content_items=[
                        {"type": "text", "text": "".join(content_chunks)},
                    ],
                )
            yield self._build_response_event()
        except Exception as e:
            yield self._build_response_event(error_message=str(e))
        finally:
            if self._chat_manager and chat_spec is not None:
                try:
                    await self._chat_manager.update_chat(chat_spec)
                except Exception:
                    logger.debug(
                        "stream_query: chat update failed",
                        exc_info=True,
                    )

    async def apply_provider(self, model_config: dict[str, Any]) -> None:
        """Hot-reload the agent with a new provider config."""
        logger.info(
            "Applying new provider config: %s / %s",
            model_config.get("provider"),
            model_config.get("model_name"),
        )
        await self.runner.restart(model_config)
        self._model_config = model_config
        logger.info("Agent restarted with new provider config")

    def _load_model_config(self) -> dict[str, Any]:
        """Load model config from working directory."""
        config_path = Path(WORKING_DIR) / "config.json"
        if not config_path.exists():
            return {}
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
