"""Voice channel router.

Twilio-facing endpoints mounted at root level:
- POST /voice/incoming
- WS   /voice/ws
- POST /voice/status-callback
"""

from __future__ import annotations

import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)

logger = logging.getLogger(__name__)

voice_router = APIRouter(tags=["voice"])


def _get_voice_channel(request_or_ws):
    app = getattr(request_or_ws, "app", None)
    if not app:
        return None
    cm = getattr(app.state, "channel_manager", None)
    if not cm:
        return None
    for ch in cm.channels:
        if ch.channel == "voice":
            return ch
    return None


async def _validate_twilio_signature(request: Request) -> None:
    voice_ch = _get_voice_channel(request)
    if not voice_ch:
        return

    auth_token = getattr(voice_ch.config, "twilio_auth_token", "")
    if not auth_token:
        return

    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        raise HTTPException(status_code=403, detail="Missing Twilio signature")

    try:
        from twilio.request_validator import RequestValidator
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "twilio package is required for request signature "
                "validation (pip install twilio)"
            ),
        ) from exc

    validator = RequestValidator(auth_token)
    form = await request.form()
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    url = f"{proto}://{host}{request.url.path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"
    params = {k: str(v) for k, v in form.items()}
    if not validator.validate(url, params, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")


@voice_router.post(
    "/voice/incoming",
    dependencies=[Depends(_validate_twilio_signature)],
)
async def voice_incoming(request: Request) -> Response:
    from ..channels.voice.twiml import (
        build_conversation_relay_twiml,
        build_error_twiml,
    )

    voice_ch = _get_voice_channel(request)
    if not voice_ch:
        twiml = build_error_twiml("Voice channel is not available.")
        return Response(content=twiml, media_type="application/xml")

    config = voice_ch.config
    wss_url = voice_ch.get_tunnel_wss_url()
    if not wss_url:
        twiml = build_error_twiml("Voice websocket URL not available.")
        return Response(content=twiml, media_type="application/xml")

    token = voice_ch.create_ws_token()
    ws_url = f"{wss_url}/voice/ws?token={token}"
    twiml = build_conversation_relay_twiml(
        ws_url,
        welcome_greeting=getattr(
            config,
            "welcome_greeting",
            "Hi! This is ResearchClaw. How can I help you?",
        ),
        tts_provider=getattr(config, "tts_provider", "google"),
        tts_voice=getattr(config, "tts_voice", "en-US-Journey-D"),
        stt_provider=getattr(config, "stt_provider", "deepgram"),
        language=getattr(config, "language", "en-US"),
    )
    return Response(content=twiml, media_type="application/xml")


@voice_router.websocket("/voice/ws")
async def voice_ws(websocket: WebSocket) -> None:
    from ..channels.voice.conversation_relay import ConversationRelayHandler

    voice_ch = _get_voice_channel(websocket)
    if not voice_ch:
        await websocket.close(code=1008, reason="Voice channel not available")
        return

    token = websocket.query_params.get("token", "")
    if not token or not voice_ch.validate_ws_token(token):
        logger.warning("WS connection rejected: invalid or missing token")
        await websocket.close(code=1008, reason="Invalid token")
        return

    await websocket.accept()
    handler = ConversationRelayHandler(
        ws=websocket,
        process=voice_ch.process,
        session_mgr=voice_ch.session_mgr,
        channel_type=voice_ch.channel,
    )
    try:
        await handler.handle()
    except WebSocketDisconnect:
        logger.info("Voice WS disconnected: call_sid=%s", handler.call_sid)
    finally:
        if handler.call_sid:
            voice_ch.session_mgr.end_session(handler.call_sid)


@voice_router.post(
    "/voice/status-callback",
    dependencies=[Depends(_validate_twilio_signature)],
)
async def voice_status_callback(request: Request) -> Response:
    form = await request.form()
    call_sid = form.get("CallSid", "")
    call_status = form.get("CallStatus", "")
    logger.info(
        "Call status callback: call_sid=%s status=%s",
        call_sid,
        call_status,
    )
    if call_status in ("completed", "busy", "no-answer", "canceled", "failed"):
        voice_ch = _get_voice_channel(request)
        if voice_ch:
            voice_ch.session_mgr.end_session(str(call_sid))
    return Response(content="", status_code=204)
