"""AgentRunnerManager – top-level manager for the agent runner lifecycle."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

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

    def __init__(
        self,
        *,
        working_dir: str | None = None,
        model_config: Optional[dict[str, Any]] = None,
        agent_id: str = "main",
    ):
        self.agent_id = (agent_id or "main").strip() or "main"
        self.working_dir = str(
            Path(working_dir or WORKING_DIR).expanduser().resolve(),
        )
        self.runner = AgentRunner()
        self.session_manager = SessionManager(
            sessions_dir=str(Path(self.working_dir) / "sessions"),
        )
        self._model_config: dict[str, Any] = dict(model_config or {})
        self._chat_manager: Any = None
        self._usage_stats: dict[str, Any] = {
            "agent_id": self.agent_id,
            "requests": 0,
            "succeeded": 0,
            "failed": 0,
            "fallbacks": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "providers": {},
        }

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
        err = SimpleNamespace(message=error_message) if error_message else None
        return SimpleNamespace(
            object="response",
            status="failed" if error_message else "completed",
            type="response",
            error=err,
        )

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        text = str(text or "")
        if not text:
            return 0
        try:
            from researchclaw.agents.utils.token_counting import (
                safe_count_str_tokens,
            )

            return int(safe_count_str_tokens(text))
        except Exception:
            return max(1, len(text) // 4)

    @staticmethod
    def _normalize_fallback_item(item: Any) -> dict[str, Any] | None:
        if isinstance(item, dict):
            provider = str(item.get("provider", "") or "").strip()
            model_name = str(item.get("model_name", "") or "").strip()
            if not provider and not model_name:
                return None
            out = {
                "provider": provider,
                "model_name": model_name,
            }
            for key in ("api_key", "base_url"):
                value = item.get(key)
                if value:
                    out[key] = value
            return out

        text = str(item or "").strip()
        if not text:
            return None
        if "/" in text:
            provider = text.split("/", 1)[0].strip().lower()
            return {"provider": provider, "model_name": text}
        return {"model_name": text}

    def _base_model_config(self) -> dict[str, Any]:
        base = dict(self._model_config or {})
        base.setdefault("working_dir", self.working_dir)
        return base

    def _fallback_configs(self) -> list[dict[str, Any]]:
        raw: list[Any] = []
        for key in ("model_fallbacks", "fallbacks"):
            value = self._model_config.get(key)
            if isinstance(value, list):
                raw.extend(value)
        model_cfg = self._model_config.get("model")
        if isinstance(model_cfg, dict):
            fb = model_cfg.get("fallbacks")
            if isinstance(fb, list):
                raw.extend(fb)

        # Optional provider-store fallback: remaining enabled providers.
        try:
            from researchclaw.providers.store import ProviderStore

            store = ProviderStore()
            active = store.get_active_provider()
            active_name = active.name if active is not None else ""
            for item in store.list_providers():
                if not item.get("enabled", False):
                    continue
                if item.get("name") == active_name:
                    continue
                raw.append(
                    {
                        "provider": item.get("provider_type", ""),
                        "model_name": item.get("model_name", ""),
                        "api_key": item.get("api_key", ""),
                        "base_url": item.get("base_url", ""),
                    },
                )
        except Exception:
            pass

        out: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str, str]] = set()
        base = self._base_model_config()
        for item in raw:
            normalized = self._normalize_fallback_item(item)
            if normalized is None:
                continue
            cfg = dict(base)
            cfg.update(normalized)
            cfg.setdefault("working_dir", self.working_dir)
            key = (
                str(cfg.get("provider", "")).strip(),
                str(cfg.get("model_name", "")).strip(),
                str(cfg.get("api_key", "")).strip(),
                str(cfg.get("base_url", "")).strip(),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(cfg)
        return out

    def _attempt_chain(self) -> list[dict[str, Any]]:
        primary = self._base_model_config()
        out = [primary]
        out.extend(self._fallback_configs())
        return out

    def _record_usage(
        self,
        *,
        prompt: str,
        response: str,
        provider: str,
        model_name: str,
        success: bool,
        fallback_used: bool,
    ) -> None:
        input_tokens = self._estimate_tokens(prompt)
        output_tokens = self._estimate_tokens(response)
        stats = self._usage_stats
        stats["requests"] += 1
        if success:
            stats["succeeded"] += 1
        else:
            stats["failed"] += 1
        if fallback_used:
            stats["fallbacks"] += 1
        stats["input_tokens"] += input_tokens
        stats["output_tokens"] += output_tokens

        key = f"{provider or 'unknown'}::{model_name or 'unknown'}"
        per = stats["providers"].setdefault(
            key,
            {
                "provider": provider or "",
                "model_name": model_name or "",
                "requests": 0,
                "succeeded": 0,
                "failed": 0,
                "input_tokens": 0,
                "output_tokens": 0,
            },
        )
        per["requests"] += 1
        if success:
            per["succeeded"] += 1
        else:
            per["failed"] += 1
        per["input_tokens"] += input_tokens
        per["output_tokens"] += output_tokens

    def get_usage_stats(self) -> dict[str, Any]:
        rows = list(self._usage_stats.get("providers", {}).values())
        rows.sort(
            key=lambda x: (
                int(x.get("requests", 0)),
                str(x.get("model_name", "")),
            ),
            reverse=True,
        )
        return {
            "agent_id": self.agent_id,
            "requests": int(self._usage_stats.get("requests", 0)),
            "succeeded": int(self._usage_stats.get("succeeded", 0)),
            "failed": int(self._usage_stats.get("failed", 0)),
            "fallbacks": int(self._usage_stats.get("fallbacks", 0)),
            "input_tokens": int(self._usage_stats.get("input_tokens", 0)),
            "output_tokens": int(self._usage_stats.get("output_tokens", 0)),
            "providers": rows,
        }

    async def start(self):
        """Start the agent runner with persisted config."""
        loaded = self._load_model_config()
        if loaded:
            self._model_config = loaded
        self._model_config.setdefault("working_dir", self.working_dir)
        if not (
            self._model_config.get("model_name")
            or self._model_config.get("api_key")
        ):
            logger.info(
                "No model configured. Use 'researchclaw init' or the "
                "API to set up a model before chatting.",
            )
            return

        attempts = self._attempt_chain()
        for idx, candidate in enumerate(attempts):
            try:
                if idx == 0:
                    await self.runner.start(candidate)
                else:
                    logger.warning(
                        "start fallback: agent=%s provider=%s model=%s try=%s/%s",
                        self.agent_id,
                        candidate.get("provider", ""),
                        candidate.get("model_name", ""),
                        idx + 1,
                        len(attempts),
                    )
                    await self.runner.restart(candidate)
                self._model_config = dict(candidate)
                return
            except Exception:
                if idx == len(attempts) - 1:
                    logger.warning(
                        "Failed to auto-start agent. "
                        "Configure model via CLI or API and restart.",
                    )

    async def stop(self):
        """Stop the agent runner."""
        await self.runner.stop()

    async def chat(self, message: str, session_id: str | None = None) -> str:
        """Send a chat message, creating a session if needed."""
        if not self.runner.is_running:
            await self.start()

        if not self.runner.is_running:
            return (
                "Scholar is not ready. Please configure your LLM provider first.\n"
                "Run `researchclaw init` or set up via Settings."
            )

        session = self._get_or_create_session(session_id)
        session.add_message("user", message)

        attempts = self._attempt_chain()
        last_error: Exception | None = None
        for idx, candidate in enumerate(attempts):
            provider = str(candidate.get("provider", "") or "")
            model_name = str(candidate.get("model_name", "") or "")
            try:
                if idx > 0:
                    await self.runner.restart(candidate)
                    self._model_config = dict(candidate)
                response = await self.runner.chat(message, session.session_id)
                session.add_message("assistant", response)
                self.session_manager._save_session(session)
                self._record_usage(
                    prompt=message,
                    response=response,
                    provider=provider,
                    model_name=model_name,
                    success=True,
                    fallback_used=idx > 0,
                )
                return response
            except Exception as exc:
                last_error = exc
                self._record_usage(
                    prompt=message,
                    response=str(exc),
                    provider=provider,
                    model_name=model_name,
                    success=False,
                    fallback_used=idx > 0,
                )
                logger.warning(
                    "chat attempt failed: agent=%s provider=%s model=%s try=%s/%s err=%s",
                    self.agent_id,
                    provider,
                    model_name,
                    idx + 1,
                    len(attempts),
                    exc,
                )

        if last_error is not None:
            raise last_error
        raise RuntimeError("chat failed with unknown error")

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
        attempts = self._attempt_chain()
        last_error: Exception | None = None

        for idx, candidate in enumerate(attempts):
            provider = str(candidate.get("provider", "") or "")
            model_name = str(candidate.get("model_name", "") or "")
            emitted_any_event = False
            content_chunks: list[str] = []
            full_content = ""
            stream_error = ""
            saw_done = False
            retry_immediately = False

            try:
                if idx > 0:
                    await self.runner.restart(candidate)
                    self._model_config = dict(candidate)
                async for event in self.runner.chat_stream(
                    message,
                    session.session_id,
                ):
                    event_type = self._normalize_text(
                        event.get("type", ""),
                    ).strip()
                    if event_type == "content":
                        chunk = self._normalize_text(event.get("content", ""))
                        if chunk:
                            content_chunks.append(chunk)
                    elif event_type == "done":
                        full_content = self._normalize_text(
                            event.get("content", full_content),
                        )
                        saw_done = True
                    elif event_type == "error":
                        stream_error = self._normalize_text(
                            event.get("content", ""),
                        ).strip()

                    # If stream failed before yielding anything, try fallback.
                    if (
                        event_type == "error"
                        and not emitted_any_event
                        and idx < len(attempts) - 1
                    ):
                        logger.warning(
                            "chat_stream fallback: agent=%s provider=%s model=%s try=%s/%s err=%s",
                            self.agent_id,
                            provider,
                            model_name,
                            idx + 1,
                            len(attempts),
                            stream_error or "stream error",
                        )
                        self._record_usage(
                            prompt=message,
                            response=stream_error or "stream error",
                            provider=provider,
                            model_name=model_name,
                            success=False,
                            fallback_used=idx > 0,
                        )
                        stream_error = ""
                        retry_immediately = True
                        break

                    emitted_any_event = True
                    yield event
            except Exception as exc:
                last_error = exc
                self._record_usage(
                    prompt=message,
                    response=str(exc),
                    provider=provider,
                    model_name=model_name,
                    success=False,
                    fallback_used=idx > 0,
                )
                if not emitted_any_event and idx < len(attempts) - 1:
                    logger.warning(
                        "chat_stream attempt failed before emit: agent=%s provider=%s model=%s try=%s/%s err=%s",
                        self.agent_id,
                        provider,
                        model_name,
                        idx + 1,
                        len(attempts),
                        exc,
                    )
                    continue
                yield {"type": "error", "content": str(exc)}
                return

            if retry_immediately and idx < len(attempts) - 1:
                continue

            if saw_done:
                final = (full_content or "".join(content_chunks)).strip()
                if final:
                    session.add_message("assistant", final)
                    self.session_manager._save_session(session)
                self._record_usage(
                    prompt=message,
                    response=final,
                    provider=provider,
                    model_name=model_name,
                    success=True,
                    fallback_used=idx > 0,
                )
                return

            if stream_error:
                self._record_usage(
                    prompt=message,
                    response=stream_error,
                    provider=provider,
                    model_name=model_name,
                    success=False,
                    fallback_used=idx > 0,
                )
                return

            # No terminal event: fallback only if nothing was emitted.
            if not emitted_any_event and idx < len(attempts) - 1:
                self._record_usage(
                    prompt=message,
                    response="stream ended without terminal event",
                    provider=provider,
                    model_name=model_name,
                    success=False,
                    fallback_used=idx > 0,
                )
                continue

            if not emitted_any_event:
                msg = "stream ended without terminal event"
                self._record_usage(
                    prompt=message,
                    response=msg,
                    provider=provider,
                    model_name=model_name,
                    success=False,
                    fallback_used=idx > 0,
                )
                yield {"type": "error", "content": msg}
            return

        if last_error is not None:
            yield {"type": "error", "content": str(last_error)}
            return
        yield {
            "type": "error",
            "content": "All model attempts failed before streaming output.",
        }

    async def stream_query(self, request: Any):
        """CoPaw-compatible process adapter for channel manager.

        Accepts a channel-built request and yields Event-like objects with
        ``object/status/type`` fields expected by channel renderers.
        """
        session_id = self._extract_value(request, "session_id", None)
        user_id = (
            self._normalize_text(
                self._extract_value(request, "user_id", ""),
            ).strip()
            or "main"
        )
        channel = (
            self._normalize_text(
                self._extract_value(request, "channel", DEFAULT_CHANNEL),
            ).strip()
            or DEFAULT_CHANNEL
        )
        prompt = self._request_to_prompt(request)
        if not prompt:
            prompt = self._normalize_text(
                self._extract_value(request, "message", ""),
            )

        content_chunks: list[str] = []
        chat_spec = None
        if self._chat_manager and session_id:
            chat_session_id = (
                f"{self.agent_id}:{session_id}"
                if self.agent_id != "main"
                else session_id
            )
            try:
                chat_spec = await self._chat_manager.get_or_create_chat(
                    session_id=chat_session_id,
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
                    full_text = (
                        self._normalize_text(
                            self._extract_value(raw_event, "content", ""),
                        ).strip()
                        or "".join(content_chunks).strip()
                    )
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
            "Applying provider config: agent=%s model=%s / %s",
            self.agent_id,
            model_config.get("provider"),
            model_config.get("model_name"),
        )
        model_config = dict(model_config or {})
        model_config.setdefault("working_dir", self.working_dir)
        await self.runner.restart(model_config)
        self._model_config = model_config
        logger.info(
            "Agent restarted with new provider config: %s",
            self.agent_id,
        )

    def _load_model_config(self) -> dict[str, Any]:
        """Load model config from working directory."""
        config_path = Path(self.working_dir) / "config.json"
        if not config_path.exists():
            return {}
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
