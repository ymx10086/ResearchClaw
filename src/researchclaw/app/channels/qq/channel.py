# pylint: disable=too-many-branches,too-many-statements
"""QQ Channel: WebSocket receive + HTTP API send.

Key improvements over CoPaw:
- Framework-independent content types (no agentscope_runtime dependency).
- Robust reconnect: exponential back-off, quick-disconnect detection,
  rate-limit cooldown, session invalidation with automatic token refresh.
- Async HTTP send via aiohttp; sync WebSocket receive via websocket-client
  in a background thread.
- msg_seq tracking to satisfy QQ's dedup requirement.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

import aiohttp

from ..base import (
    BaseChannel,
    ContentType,
    TextContent,
    OnReplySent,
    OutgoingContentPart,
    ProcessHandler,
)

logger = logging.getLogger(__name__)

# ── WebSocket op codes ─────────────────────────────────────────────
OP_DISPATCH = 0
OP_HEARTBEAT = 1
OP_IDENTIFY = 2
OP_RESUME = 6
OP_RECONNECT = 7
OP_INVALID_SESSION = 9
OP_HELLO = 10
OP_HEARTBEAT_ACK = 11

# ── Intent flags ───────────────────────────────────────────────────
INTENT_PUBLIC_GUILD_MESSAGES = 1 << 30
INTENT_DIRECT_MESSAGE = 1 << 12
INTENT_GROUP_AND_C2C = 1 << 25
INTENT_GUILD_MEMBERS = 1 << 1

# ── Reconnect tuning ──────────────────────────────────────────────
RECONNECT_DELAYS = [1, 2, 5, 10, 30, 60]
RATE_LIMIT_DELAY = 60
MAX_RECONNECT_ATTEMPTS = 100
QUICK_DISCONNECT_THRESHOLD = 5
MAX_QUICK_DISCONNECT_COUNT = 3

DEFAULT_API_BASE = "https://api.sgroup.qq.com"
TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"


# ── Helpers ────────────────────────────────────────────────────────


def _get_api_base() -> str:
    return os.getenv("QQ_API_BASE", DEFAULT_API_BASE).rstrip("/")


def _get_gateway_url_sync(access_token: str) -> str:
    """Fetch gateway WebSocket URL (blocking, for WS thread)."""
    import urllib.error
    import urllib.request

    url = f"{_get_api_base()}/gateway"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"QQBot {access_token}",
            "Content-Type": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode() if exc.fp else ""
        except Exception:
            pass
        raise RuntimeError(
            f"Gateway fetch failed HTTP {exc.code}: {body[:500]}",
        ) from exc
    ws_url = data.get("url")
    if not ws_url:
        raise RuntimeError(f"No 'url' in gateway response: {data}")
    return ws_url


# ── msg_seq tracker (prevents QQ dedup rejection) ─────────────────

_msg_seq: Dict[str, int] = {}
_msg_seq_lock = threading.Lock()


def _next_msg_seq(key: str) -> int:
    with _msg_seq_lock:
        n = _msg_seq.get(key, 0) + 1
        _msg_seq[key] = n
        # keep dict bounded
        if len(_msg_seq) > 1000:
            for k in list(_msg_seq.keys())[:500]:
                del _msg_seq[k]
        return n


# ── Async API helpers ──────────────────────────────────────────────


async def _api(
    session: aiohttp.ClientSession,
    token: str,
    method: str,
    path: str,
    body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    url = f"{_get_api_base()}{path}"
    kwargs: Dict[str, Any] = {
        "headers": {
            "Authorization": f"QQBot {token}",
            "Content-Type": "application/json",
        },
    }
    if body is not None:
        kwargs["json"] = body
    async with session.request(method, url, **kwargs) as resp:
        data = await resp.json()
        if resp.status >= 400:
            raise RuntimeError(f"QQ API {path} {resp.status}: {data}")
        return data


async def _send_c2c(
    session: aiohttp.ClientSession,
    token: str,
    openid: str,
    content: str,
    msg_id: Optional[str] = None,
) -> None:
    body: Dict[str, Any] = {
        "content": content,
        "msg_type": 0,
        "msg_seq": _next_msg_seq(msg_id or "c2c"),
    }
    if msg_id:
        body["msg_id"] = msg_id
    await _api(session, token, "POST", f"/v2/users/{openid}/messages", body)


async def _send_channel(
    session: aiohttp.ClientSession,
    token: str,
    channel_id: str,
    content: str,
    msg_id: Optional[str] = None,
) -> None:
    body: Dict[str, Any] = {"content": content}
    if msg_id:
        body["msg_id"] = msg_id
    await _api(
        session,
        token,
        "POST",
        f"/channels/{channel_id}/messages",
        body,
    )


async def _send_group(
    session: aiohttp.ClientSession,
    token: str,
    group_openid: str,
    content: str,
    msg_id: Optional[str] = None,
) -> None:
    body: Dict[str, Any] = {
        "content": content,
        "msg_type": 0,
        "msg_seq": _next_msg_seq(msg_id or "group"),
    }
    if msg_id:
        body["msg_id"] = msg_id
    await _api(
        session,
        token,
        "POST",
        f"/v2/groups/{group_openid}/messages",
        body,
    )


# ── Channel ───────────────────────────────────────────────────────


class QQChannel(BaseChannel):
    """QQ Bot channel.

    Incoming: WebSocket (websocket-client) in a background thread.
    Outgoing: HTTP API (aiohttp) from the event-loop.
    """

    channel = "qq"

    def __init__(
        self,
        process: ProcessHandler,
        enabled: bool,
        app_id: str,
        client_secret: str,
        bot_prefix: str = "",
        on_reply_sent: OnReplySent = None,
        show_tool_details: bool = True,
    ):
        super().__init__(
            process,
            on_reply_sent=on_reply_sent,
            show_tool_details=show_tool_details,
        )
        self.enabled = enabled
        self.app_id = app_id
        self.client_secret = client_secret
        self.bot_prefix = bot_prefix

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._token_cache: Optional[Dict[str, Any]] = None
        self._token_lock = threading.Lock()
        self._http: Optional[aiohttp.ClientSession] = None

    # ── token management ───────────────────────────────────────────

    def _get_token_sync(self) -> str:
        """Blocking token fetch (for WS thread)."""
        with self._token_lock:
            if (
                self._token_cache
                and time.time() < self._token_cache["expires_at"] - 300
            ):
                return self._token_cache["token"]
        import urllib.request

        req = urllib.request.Request(
            TOKEN_URL,
            data=json.dumps(
                {"appId": self.app_id, "clientSecret": self.client_secret},
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        token = data.get("access_token")
        if not token:
            raise RuntimeError(f"No access_token: {data}")
        expires_in = int(data.get("expires_in", 7200))
        with self._token_lock:
            self._token_cache = {
                "token": token,
                "expires_at": time.time() + expires_in,
            }
        return token

    async def _get_token_async(self) -> str:
        """Non-blocking token fetch (for send path)."""
        with self._token_lock:
            if (
                self._token_cache
                and time.time() < self._token_cache["expires_at"] - 300
            ):
                return self._token_cache["token"]
        assert self._http is not None
        async with self._http.post(
            TOKEN_URL,
            json={"appId": self.app_id, "clientSecret": self.client_secret},
            headers={"Content-Type": "application/json"},
        ) as resp:
            if resp.status >= 400:
                raise RuntimeError(f"Token request failed {resp.status}")
            data = await resp.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError(f"No access_token: {data}")
        expires_in = int(data.get("expires_in", 7200))
        with self._token_lock:
            self._token_cache = {
                "token": token,
                "expires_at": time.time() + expires_in,
            }
        return token

    def _clear_token_cache(self) -> None:
        with self._token_lock:
            self._token_cache = None

    # ── factory methods ────────────────────────────────────────────

    @classmethod
    def from_env(
        cls,
        process: ProcessHandler,
        on_reply_sent: OnReplySent = None,
    ) -> "QQChannel":
        return cls(
            process=process,
            enabled=os.getenv("QQ_CHANNEL_ENABLED", "1") == "1",
            app_id=os.getenv("QQ_APP_ID", ""),
            client_secret=os.getenv("QQ_CLIENT_SECRET", ""),
            bot_prefix=os.getenv("QQ_BOT_PREFIX", ""),
            on_reply_sent=on_reply_sent,
        )

    @classmethod
    def from_config(
        cls,
        process: ProcessHandler,
        config: Any,
        on_reply_sent: OnReplySent = None,
        show_tool_details: bool = True,
    ) -> "QQChannel":
        return cls(
            process=process,
            enabled=getattr(config, "enabled", False),
            app_id=getattr(config, "app_id", "") or "",
            client_secret=getattr(config, "client_secret", "") or "",
            bot_prefix=getattr(config, "bot_prefix", "") or "",
            on_reply_sent=on_reply_sent,
            show_tool_details=show_tool_details,
        )

    # ── send ───────────────────────────────────────────────────────

    async def send(
        self,
        to_handle: str,
        text: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Route text to the correct QQ API endpoint.

        ``to_handle`` format:
        - ``group:<group_openid>``
        - ``channel:<channel_id>``
        - raw openid → c2c
        ``meta`` may contain ``message_type``, ``message_id``, etc.
        """
        if not self.enabled or not text.strip():
            return
        meta = meta or {}
        message_type = meta.get("message_type")
        msg_id = meta.get("message_id")
        sender_id = meta.get("sender_id") or to_handle
        channel_id = meta.get("channel_id")
        group_openid = meta.get("group_openid")

        # Infer type from to_handle prefix
        if message_type is None:
            if to_handle.startswith("group:"):
                message_type = "group"
                group_openid = to_handle[6:]
            elif to_handle.startswith("channel:"):
                message_type = "guild"
                channel_id = to_handle[8:]
            else:
                message_type = "c2c"

        try:
            token = await self._get_token_async()
        except Exception:
            logger.exception("qq: token fetch failed")
            return
        try:
            if message_type == "c2c":
                await _send_c2c(
                    self._http,
                    token,
                    sender_id,
                    text.strip(),
                    msg_id,
                )
            elif message_type == "group" and group_openid:
                await _send_group(
                    self._http,
                    token,
                    group_openid,
                    text.strip(),
                    msg_id,
                )
            elif channel_id:
                await _send_channel(
                    self._http,
                    token,
                    channel_id,
                    text.strip(),
                    msg_id,
                )
            else:
                await _send_c2c(
                    self._http,
                    token,
                    sender_id,
                    text.strip(),
                    msg_id,
                )
        except Exception:
            logger.exception("qq: send failed")

    async def _on_consume_error(
        self,
        request: Any,
        to_handle: str,
        err_text: str,
    ) -> None:
        await self.send(to_handle, err_text)

    # ── WebSocket loop (runs in thread) ────────────────────────────

    def _run_ws_forever(self) -> None:  # noqa: C901
        try:
            import websocket
        except ImportError:
            logger.error(
                "websocket-client required. pip install websocket-client",
            )
            return

        reconnect_attempts = 0
        last_connect_time = 0.0
        quick_disconnect_count = 0
        session_id: Optional[str] = None
        last_seq: Optional[int] = None
        identify_fail_count = 0
        should_refresh_token = False

        def _connect() -> bool:  # noqa: C901
            nonlocal session_id, last_seq, reconnect_attempts
            nonlocal last_connect_time, quick_disconnect_count
            nonlocal should_refresh_token, identify_fail_count
            if self._stop_event.is_set():
                return False

            if should_refresh_token:
                self._clear_token_cache()
                should_refresh_token = False

            try:
                token = self._get_token_sync()
                ws_url = _get_gateway_url_sync(token)
            except Exception as exc:
                logger.warning("qq: token/gateway error: %s", exc)
                return True

            logger.info("qq: connecting to %s", ws_url)
            try:
                ws = websocket.create_connection(ws_url)
            except Exception as exc:
                logger.warning("qq: ws connect error: %s", exc)
                return True

            heartbeat_interval: Optional[float] = None
            heartbeat_timer: Optional[threading.Timer] = None

            def _stop_heartbeat() -> None:
                nonlocal heartbeat_timer
                if heartbeat_timer:
                    heartbeat_timer.cancel()
                    heartbeat_timer = None

            def _schedule_heartbeat() -> None:
                nonlocal heartbeat_timer
                if heartbeat_interval is None or self._stop_event.is_set():
                    return

                def _ping() -> None:
                    if self._stop_event.is_set():
                        return
                    try:
                        if ws.connected:
                            ws.send(
                                json.dumps(
                                    {"op": OP_HEARTBEAT, "d": last_seq},
                                ),
                            )
                    except Exception:
                        pass
                    _schedule_heartbeat()

                heartbeat_timer = threading.Timer(
                    heartbeat_interval / 1000.0,
                    _ping,
                )
                heartbeat_timer.daemon = True
                heartbeat_timer.start()

            try:
                while not self._stop_event.is_set():
                    raw = ws.recv()
                    if not raw:
                        break
                    payload = json.loads(raw)
                    op = payload.get("op")
                    d = payload.get("d")
                    s = payload.get("s")
                    t = payload.get("t")
                    if s is not None:
                        last_seq = s

                    if op == OP_HELLO:
                        heartbeat_interval = (d or {}).get(
                            "heartbeat_interval",
                            45000,
                        )
                        if session_id and last_seq is not None:
                            ws.send(
                                json.dumps(
                                    {
                                        "op": OP_RESUME,
                                        "d": {
                                            "token": f"QQBot {token}",
                                            "session_id": session_id,
                                            "seq": last_seq,
                                        },
                                    },
                                ),
                            )
                        else:
                            intents = (
                                INTENT_PUBLIC_GUILD_MESSAGES
                                | INTENT_GUILD_MEMBERS
                            )
                            if identify_fail_count < 3:
                                intents |= (
                                    INTENT_DIRECT_MESSAGE
                                    | INTENT_GROUP_AND_C2C
                                )
                            ws.send(
                                json.dumps(
                                    {
                                        "op": OP_IDENTIFY,
                                        "d": {
                                            "token": f"QQBot {token}",
                                            "intents": intents,
                                            "shard": [0, 1],
                                        },
                                    },
                                ),
                            )
                        _schedule_heartbeat()

                    elif op == OP_DISPATCH:
                        self._handle_dispatch(t, d or {})

                    elif op == OP_HEARTBEAT_ACK:
                        pass

                    elif op == OP_RECONNECT:
                        logger.info("qq: server requested reconnect")
                        break

                    elif op == OP_INVALID_SESSION:
                        can_resume = d
                        logger.warning(
                            "qq: invalid session (resume=%s)",
                            can_resume,
                        )
                        if not can_resume:
                            session_id = None
                            last_seq = None
                            identify_fail_count += 1
                            should_refresh_token = True
                        break

                    # READY / RESUMED in DISPATCH
                    if op == OP_DISPATCH and t == "READY":
                        session_id = (d or {}).get("session_id")
                        identify_fail_count = 0
                        reconnect_attempts = 0
                        last_connect_time = time.time()
                        logger.info("qq: ready session=%s", session_id)
                    elif op == OP_DISPATCH and t == "RESUMED":
                        logger.info("qq: session resumed")

            except Exception:
                logger.exception("qq: ws loop error")
            finally:
                _stop_heartbeat()
                try:
                    ws.close()
                except Exception:
                    pass

            # ── reconnect delay logic ──────────────────────────────
            elapsed = (
                time.time() - last_connect_time if last_connect_time else 999
            )
            if elapsed < QUICK_DISCONNECT_THRESHOLD:
                quick_disconnect_count += 1
                if quick_disconnect_count >= MAX_QUICK_DISCONNECT_COUNT:
                    session_id = None
                    last_seq = None
                    should_refresh_token = True
                    quick_disconnect_count = 0
                    delay = RATE_LIMIT_DELAY
                else:
                    delay = RECONNECT_DELAYS[
                        min(reconnect_attempts, len(RECONNECT_DELAYS) - 1)
                    ]
            else:
                quick_disconnect_count = 0
                delay = RECONNECT_DELAYS[
                    min(reconnect_attempts, len(RECONNECT_DELAYS) - 1)
                ]

            reconnect_attempts += 1
            if reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
                logger.error("qq: max reconnect attempts reached")
                return False

            logger.info(
                "qq: reconnect in %ss (attempt %s)",
                delay,
                reconnect_attempts,
            )
            self._stop_event.wait(timeout=delay)
            return not self._stop_event.is_set()

        # main loop
        while _connect():
            pass
        logger.info("qq: ws thread exited")

    # ── dispatch handler ───────────────────────────────────────────

    def _handle_dispatch(
        self,
        event_type: Optional[str],
        d: Dict[str, Any],
    ) -> None:
        """Parse a DISPATCH event and enqueue if it's a message."""
        if event_type in (
            "C2C_MESSAGE_CREATE",
            "AT_MESSAGE_CREATE",
            "DIRECT_MESSAGE_CREATE",
            "GROUP_AT_MESSAGE_CREATE",
        ):
            self._handle_message_event(event_type, d)

    def _handle_message_event(
        self,
        event_type: str,
        d: Dict[str, Any],
    ) -> None:
        author = d.get("author") or {}
        text = (d.get("content") or "").strip()
        attachments = d.get("attachments") or []

        if not text and not attachments:
            return
        if self.bot_prefix and text.startswith(self.bot_prefix):
            return

        # ── Resolve sender / routing IDs per event type ────────────
        if event_type == "C2C_MESSAGE_CREATE":
            sender = author.get("user_openid") or author.get("id") or ""
            message_type = "c2c"
            extra_meta: Dict[str, Any] = {}
        elif event_type == "AT_MESSAGE_CREATE":
            sender = author.get("id") or author.get("username") or ""
            message_type = "guild"
            extra_meta = {
                "channel_id": d.get("channel_id", ""),
                "guild_id": d.get("guild_id", ""),
            }
        elif event_type == "DIRECT_MESSAGE_CREATE":
            sender = author.get("id") or author.get("username") or ""
            message_type = "dm"
            extra_meta = {
                "channel_id": d.get("channel_id", ""),
                "guild_id": d.get("guild_id", ""),
            }
        elif event_type == "GROUP_AT_MESSAGE_CREATE":
            sender = author.get("member_openid") or author.get("id") or ""
            message_type = "group"
            extra_meta = {"group_openid": d.get("group_openid", "")}
        else:
            return

        if not sender:
            return

        msg_id = d.get("id", "")
        meta: Dict[str, Any] = {
            "message_type": message_type,
            "message_id": msg_id,
            "sender_id": sender,
            "incoming_raw": d,
            "attachments": attachments,
            **extra_meta,
        }
        content_parts = [TextContent(text=text)]
        native = {
            "channel_id": self.channel,
            "sender_id": sender,
            "content_parts": content_parts,
            "meta": meta,
        }

        if self._enqueue is not None and self._loop is not None:
            self._loop.call_soon_threadsafe(self._enqueue, native)

        logger.info(
            "qq: recv %s from=%s text=%r",
            event_type,
            sender,
            text[:100],
        )

    # ── lifecycle ──────────────────────────────────────────────────

    async def start(self) -> None:
        if not self.enabled:
            logger.debug("qq channel disabled")
            return
        if not self.app_id or not self.client_secret:
            raise RuntimeError(
                "QQ_APP_ID and QQ_CLIENT_SECRET are required.",
            )
        self._loop = asyncio.get_running_loop()
        self._stop_event.clear()
        if self._http is None:
            self._http = aiohttp.ClientSession()
        self._ws_thread = threading.Thread(
            target=self._run_ws_forever,
            daemon=True,
            name="qq_ws",
        )
        self._ws_thread.start()
        logger.info("QQ channel started")

    async def stop(self) -> None:
        if not self.enabled:
            return
        self._stop_event.set()
        if self._ws_thread:
            self._ws_thread.join(timeout=8)
        if self._http:
            await self._http.close()
            self._http = None
        logger.info("QQ channel stopped")
