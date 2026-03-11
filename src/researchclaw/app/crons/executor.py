"""Cron job executor — runs text and agent tasks.

Dispatches results to channels via the channel manager.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Iterable

from .models import CronJobSpec

logger = logging.getLogger(__name__)


class CronExecutor:
    """Executes a single cron job.

    Supports two task types:
    - text: send fixed text message to the target channel
    - agent: ask the agent with a prompt, stream/dispatch the response
    """

    def __init__(self, *, runner: Any, channel_manager: Any):
        self._runner = runner
        self._channel_manager = channel_manager

    @staticmethod
    def _extract_text_from_content_items(items: Iterable[Any]) -> str:
        parts: list[str] = []
        for item in items:
            if isinstance(item, dict):
                t = str(item.get("type", "")).lower()
                if t == "text":
                    text = str(item.get("text", "") or "").strip()
                    if text:
                        parts.append(text)
                continue
            t = str(getattr(item, "type", "") or "").lower()
            if t == "text":
                text = str(getattr(item, "text", "") or "").strip()
                if text:
                    parts.append(text)
        return "\n".join(parts).strip()

    def _extract_event_text(self, event: Any) -> str:
        """Extract textual content from a runner event."""
        if event is None:
            return ""

        if isinstance(event, dict):
            # SSE-style done/content events
            event_type = str(event.get("type", "")).lower()
            if event_type in {"content", "done", "content_replace"}:
                return str(event.get("content", "") or "").strip()

            data = event.get("data")
            if isinstance(data, dict):
                content = data.get("content")
                if isinstance(content, list):
                    return self._extract_text_from_content_items(content)
            return ""

        # Event-like object from stream_query adapter
        obj = str(getattr(event, "object", "") or "").lower()
        status = str(getattr(event, "status", "") or "").lower()
        ev_type = str(getattr(event, "type", "") or "").lower()
        if obj == "message" and status == "completed" and ev_type == "content":
            data = getattr(event, "data", None)
            content = (
                getattr(data, "content", None) if data is not None else None
            )
            if isinstance(content, list):
                return self._extract_text_from_content_items(content)
        return ""

    async def _save_console_result_as_new_chat(
        self,
        *,
        job: CronJobSpec,
        result_text: str,
        agent_id: str = "main",
    ) -> None:
        """Persist console cron output as a new chat session."""
        if str(job.dispatch.channel or "").lower() != "console":
            return
        if not result_text.strip():
            return

        if hasattr(self._runner, "get_session_manager"):
            session_manager = self._runner.get_session_manager(agent_id)
        else:
            session_manager = getattr(self._runner, "session_manager", None)
        if session_manager is None:
            return

        title = f"[Cron] {job.name}"
        try:
            session = session_manager.create_session(title=title)
            prompt_text = ""
            if job.task_type == "agent" and job.request is not None:
                inp = job.request.model_dump(mode="json").get("input") or []
                if isinstance(inp, list) and inp:
                    first = inp[0] if isinstance(inp[0], dict) else {}
                    contents = (
                        first.get("content") if isinstance(first, dict) else []
                    ) or []
                    if isinstance(contents, list):
                        prompt_parts: list[str] = []
                        for c in contents:
                            if (
                                isinstance(c, dict)
                                and str(c.get("type", "")).lower() == "text"
                            ):
                                txt = str(c.get("text", "") or "").strip()
                                if txt:
                                    prompt_parts.append(txt)
                        prompt_text = "\n".join(prompt_parts).strip()

            if prompt_text:
                session.add_message(
                    "user",
                    f"[定时任务: {job.name}]\n{prompt_text}",
                )
            else:
                session.add_message("user", f"[定时任务触发] {job.name}")

            session.add_message("assistant", result_text.strip())
            # Persist updates after appending messages.
            session_manager._save_session(session)  # noqa: SLF001
            # Keep chats.json in sync when chat manager is attached.
            chat_manager = getattr(
                self._runner,
                "_chat_manager",
                None,
            )  # noqa: SLF001
            if chat_manager is not None and hasattr(
                chat_manager,
                "get_or_create_chat",
            ):
                await chat_manager.get_or_create_chat(
                    session_id=session.session_id,
                    user_id=job.dispatch.target.user_id or "cron",
                    channel="console",
                    name=title,
                )
        except Exception:
            logger.debug(
                "save console cron result as chat failed: job_id=%s",
                job.id,
                exc_info=True,
            )

    async def execute(self, job: CronJobSpec) -> None:
        """Execute one job once.

        Args:
            job: The cron job spec to execute

        Raises:
            asyncio.TimeoutError: If execution exceeds the job's timeout
        """
        target_user_id = job.dispatch.target.user_id
        target_session_id = job.dispatch.target.session_id
        dispatch_meta: Dict[str, Any] = dict(job.dispatch.meta or {})
        agent_id = str(
            dispatch_meta.get("agent_id")
            or dispatch_meta.get("agentId")
            or "",
        ).strip()
        if not agent_id:
            agent_id = "main"

        logger.info(
            "cron execute: job_id=%s channel=%s task_type=%s "
            "target_user_id=%s target_session_id=%s",
            job.id,
            job.dispatch.channel,
            job.task_type,
            target_user_id[:40] if target_user_id else "",
            target_session_id[:40] if target_session_id else "",
        )

        if job.task_type == "text" and job.text:
            logger.info(
                "cron send_text: job_id=%s channel=%s len=%s",
                job.id,
                job.dispatch.channel,
                len(job.text or ""),
            )
            await self._channel_manager.send_text(
                channel=job.dispatch.channel,
                user_id=target_user_id,
                session_id=target_session_id,
                text=job.text.strip(),
                meta=dispatch_meta,
            )
            await self._save_console_result_as_new_chat(
                job=job,
                result_text=job.text.strip(),
                agent_id=agent_id,
            )
            return

        # agent: run request as the dispatch target user
        logger.info(
            "cron agent: job_id=%s channel=%s stream_query then send_event",
            job.id,
            job.dispatch.channel,
        )
        assert job.request is not None
        req: Dict[str, Any] = job.request.model_dump(mode="json")
        req["user_id"] = target_user_id or "cron"
        req["session_id"] = target_session_id or f"cron:{job.id}"
        if agent_id:
            req["agent_id"] = agent_id
        result_chunks: list[str] = []

        async def _run() -> None:
            async for event in self._runner.stream_query(req):
                await self._channel_manager.send_event(
                    channel=job.dispatch.channel,
                    user_id=target_user_id,
                    session_id=target_session_id,
                    event=event,
                    meta=dispatch_meta,
                )
                text = self._extract_event_text(event)
                if text:
                    result_chunks.append(text)

        await asyncio.wait_for(_run(), timeout=job.runtime.timeout_seconds)
        await self._save_console_result_as_new_chat(
            job=job,
            result_text="\n".join(result_chunks).strip(),
            agent_id=agent_id,
        )
