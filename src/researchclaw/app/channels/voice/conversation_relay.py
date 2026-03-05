"""ConversationRelay WebSocket handler for a single call."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from fastapi import WebSocketDisconnect

from .session import CallSessionManager

if TYPE_CHECKING:
    from fastapi import WebSocket
    from ..base import ProcessHandler

logger = logging.getLogger(__name__)

_ERROR_MSG = "I'm having trouble right now. Please try again."


class ConversationRelayHandler:
    """Handle one call's WebSocket session with Twilio ConversationRelay."""

    def __init__(
        self,
        ws: "WebSocket",
        process: "ProcessHandler",
        session_mgr: CallSessionManager,
        channel_type: str = "voice",
    ) -> None:
        self.ws = ws
        self._process = process
        self._session_mgr = session_mgr
        self._channel_type = channel_type

        self.call_sid: str = ""
        self.caller_info: dict[str, str] = {}
        self._closed = False

    async def handle(self) -> None:
        try:
            while not self._closed:
                raw = await self.ws.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("Bad JSON from Twilio WS: %s", raw[:200])
                    continue

                msg_type = msg.get("type")
                if msg_type == "setup":
                    await self._handle_setup(msg)
                elif msg_type == "prompt":
                    await self._handle_prompt(msg)
                elif msg_type == "interrupt":
                    await self._handle_interrupt(msg)
                elif msg_type == "dtmf":
                    await self._handle_dtmf(msg)
                else:
                    logger.debug("Unknown WS message type: %s", msg_type)
        except WebSocketDisconnect:
            logger.info(
                "ConversationRelay WS disconnected: call_sid=%s",
                self.call_sid,
            )
        except Exception:
            if not self._closed:
                logger.exception(
                    "Unexpected error in ConversationRelay: call_sid=%s",
                    self.call_sid,
                )
        finally:
            self._closed = True
            try:
                await self.ws.close()
            except Exception:
                pass
            if self.call_sid:
                self._session_mgr.end_session(self.call_sid)

    async def _handle_setup(self, msg: dict) -> None:
        self.call_sid = msg.get("callSid", "")
        self.caller_info = {
            "from": msg.get("from", ""),
            "to": msg.get("to", ""),
        }
        logger.info(
            "Call setup: call_sid=%s from=%s to=%s",
            self.call_sid,
            self.caller_info.get("from"),
            self.caller_info.get("to"),
        )
        if not self.call_sid:
            logger.warning("Setup message missing callSid, closing connection")
            await self.close()
            return
        self._session_mgr.create_session(
            call_sid=self.call_sid,
            handler=self,
            from_number=self.caller_info.get("from", ""),
            to_number=self.caller_info.get("to", ""),
        )

    async def _handle_prompt(self, msg: dict) -> None:
        user_text = msg.get("voicePrompt", "")
        if not user_text.strip():
            return

        logger.info(
            "Voice prompt: call_sid=%s text=%s",
            self.call_sid,
            user_text[:100],
        )
        request = self._build_agent_request(user_text)
        await self._process_and_stream(request)

    async def _handle_interrupt(self, msg: dict) -> None:
        spoken = msg.get("utteranceUntilInterrupt", "")
        logger.info(
            "Call interrupted: call_sid=%s spoken_so_far=%s",
            self.call_sid,
            spoken[:100],
        )

    async def _handle_dtmf(self, msg: dict) -> None:
        digit = msg.get("digit", "")
        logger.info(
            "DTMF received: call_sid=%s digit=%s",
            self.call_sid,
            digit,
        )

    def _build_agent_request(self, text: str) -> Any:
        return {
            "session_id": f"voice:{self.call_sid}",
            "user_id": self.caller_info.get("from", ""),
            "channel": self._channel_type,
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": text}],
                },
            ],
        }

    async def _process_and_stream(self, request: Any) -> None:
        try:
            async for event in self._process(request):
                if self._closed:
                    break
                obj = getattr(event, "object", None)
                status = getattr(event, "status", None)
                status_val = (
                    status.value if hasattr(status, "value") else str(status)
                ) if status else ""
                completed = status_val == "completed"

                if obj == "message" and completed:
                    text = self._extract_text_from_event(event)
                    if text:
                        await self._send_token(text, last=False)
                        await self._send_token("", last=True)
                elif obj == "response":
                    err = getattr(event, "error", None)
                    if err:
                        err_msg = getattr(err, "message", str(err))
                        logger.error(
                            "Agent error: call_sid=%s error=%s",
                            self.call_sid,
                            err_msg,
                        )
                        await self._send_token(_ERROR_MSG, last=False)
                        await self._send_token("", last=True)
        except Exception:
            logger.exception(
                "Error processing voice request: call_sid=%s",
                self.call_sid,
            )
            if not self._closed:
                await self._send_token(_ERROR_MSG, last=False)
                await self._send_token("", last=True)

    @staticmethod
    def _extract_text_from_event(event: Any) -> str:
        data = getattr(event, "data", None)
        content = getattr(data, "content", None)
        if content is None:
            content = getattr(event, "content", None)
        if not content:
            return ""

        parts: list[str] = []
        for c in content:
            ct = getattr(c, "type", None)
            ct_val = (
                ct.value if hasattr(ct, "value") else str(ct) if ct else ""
            ).lower()
            if ct_val == "text":
                text = getattr(c, "text", None)
                if text:
                    parts.append(str(text).strip())
            elif ct_val == "refusal":
                refusal = getattr(c, "refusal", None)
                if refusal:
                    parts.append(str(refusal).strip())
        return " ".join(parts)

    async def _send_token(self, token: str, *, last: bool = False) -> None:
        if self._closed:
            return
        try:
            await self.ws.send_text(
                json.dumps({"type": "text", "token": token, "last": last}),
            )
        except Exception:
            logger.warning(
                "Failed to send text to Twilio WS: call_sid=%s",
                self.call_sid,
            )
            self._closed = True

    async def send_text(self, text: str) -> None:
        await self._send_token(text, last=True)

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            await self.ws.send_text(json.dumps({"type": "end"}))
        except Exception:
            logger.exception("Failed to send end frame in ConversationRelay")
        finally:
            try:
                await self.ws.close()
            except Exception:
                logger.exception("Failed to close WebSocket in ConversationRelay")
