"""Channel manager – queue-based coordinator for multiple channels.

Key improvements over CoPaw:
- **Queue architecture**: per-channel async queues with configurable parallel
  consumer workers for concurrent session processing.
- **Session-based batching**: same-session messages are drained and merged
  before processing, avoiding duplicate replies.
- **In-progress tracking**: payloads arriving while a session is being
  processed are held in pending buffers and flushed when done.
- **Hot-swap**: :meth:`replace_channel` starts a new channel, swaps, and
  stops the old one – useful for live config updates.
- **Thread-safe enqueue**: channels running in sync threads (e.g. DingTalk
  Stream, iMessage polling) can safely enqueue via ``enqueue()``.
- **send_text / send_event**: proactive send helpers for cron jobs.
"""
from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Set

from .base import BaseChannel, TextContent, ContentType

logger = logging.getLogger(__name__)

# Tunable constants
_CHANNEL_QUEUE_MAXSIZE = 500
_CONSUMER_WORKERS_PER_CHANNEL = 4


def _to_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        return dict(obj)
    if obj is None:
        return {}
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in vars(obj).items() if not k.startswith("_")}
    return {}


def _to_namespace(value: Any) -> Any:
    if isinstance(value, dict):
        return SimpleNamespace(
            **{k: _to_namespace(v) for k, v in value.items()},
        )
    if isinstance(value, list):
        return [_to_namespace(v) for v in value]
    return value


def _drain_same_key(
    q: asyncio.Queue,
    ch: BaseChannel,
    key: str,
    first: Any,
) -> List[Any]:
    """Pop all items from *q* that share the same debounce key as *first*.

    Returns a batch list starting with *first*. Non-matching items are
    immediately re-queued.
    """
    batch = [first]
    requeue: List[Any] = []
    while not q.empty():
        try:
            item = q.get_nowait()
        except asyncio.QueueEmpty:
            break
        if ch.get_debounce_key(item) == key:
            batch.append(item)
        else:
            requeue.append(item)
    for item in requeue:
        q.put_nowait(item)
    return batch


async def _process_batch(ch: BaseChannel, batch: List[Any]) -> None:
    """Merge *batch* into one payload and call ``ch.consume_one()``."""
    if not batch:
        return
    if len(batch) == 1:
        await ch.consume_one(batch[0])
        return
    # Separate native dicts from request objects
    natives = [b for b in batch if ch._is_native_payload(b)]
    requests = [b for b in batch if not ch._is_native_payload(b)]
    if natives:
        merged = ch.merge_native_items(natives)
        if merged:
            await ch.consume_one(merged)
    if requests:
        merged = ch.merge_requests(requests)
        if merged:
            await ch.consume_one(merged)


def _put_pending_merged(
    ch: BaseChannel,
    q: asyncio.Queue,
    pending: List[Any],
) -> None:
    """Merge pending payloads (if any) and re-queue."""
    if not pending:
        return
    natives = [p for p in pending if ch._is_native_payload(p)]
    others = [p for p in pending if not ch._is_native_payload(p)]
    if natives:
        merged = ch.merge_native_items(natives)
        if merged:
            q.put_nowait(merged)
    for o in others:
        q.put_nowait(o)


class ChannelManager:
    """Manages registration, lifecycle, and message routing for channels.

    Each channel gets its own ``asyncio.Queue`` and a pool of consumer
    workers. Messages are drained per-session, merged, and processed –
    preventing duplicate replies when the user sends rapid-fire messages.
    """

    def __init__(self, channels: Optional[List[BaseChannel]] = None):
        self.channels: List[BaseChannel] = list(channels or [])
        self._queues: Dict[str, asyncio.Queue] = {}
        self._consumer_tasks: List[asyncio.Task] = []
        self._consumer_tasks_by_channel: Dict[str, List[asyncio.Task]] = {}
        self._in_progress: Set[tuple] = set()
        self._pending: Dict[tuple, List[Any]] = {}
        self._key_locks: Dict[tuple, asyncio.Lock] = {}
        self._lock = asyncio.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # ── registration (simple API for backward compat) ──────────────

    def register(self, channel: BaseChannel) -> None:
        """Register a channel."""
        self.channels.append(channel)
        logger.info("Channel registered: %s", channel.channel)

    def get(self, name: str) -> Optional[BaseChannel]:
        """Get channel by name."""
        for ch in self.channels:
            if ch.channel == name:
                return ch
        return None

    # ── factory methods ────────────────────────────────────────────

    @classmethod
    def from_config(
        cls,
        process: Any,
        config: Any,
        on_last_dispatch: Any = None,
        show_tool_details: bool = True,
    ) -> "ChannelManager":
        """Build ChannelManager from app config.

        Iterates available channels in config, instantiates each via
        ``from_config()``, and returns a manager ready to ``start_all()``.
        """
        from .registry import get_channel_registry

        registry = get_channel_registry()
        available: Optional[Set[str]] = None
        if hasattr(config, "channels"):
            ch_cfg = config.channels
            if hasattr(ch_cfg, "available"):
                raw_available = getattr(ch_cfg, "available")
                available = set(raw_available or [])
            elif isinstance(ch_cfg, dict):
                if "available" in ch_cfg:
                    available = set(ch_cfg.get("available") or [])

        channels: List[BaseChannel] = []
        extra = (
            getattr(config, "extra_channels", {})
            if hasattr(config, "extra_channels")
            else {}
        )
        account_maps = (
            getattr(config, "channel_accounts", {})
            if hasattr(config, "channel_accounts")
            else {}
        )
        if not isinstance(account_maps, dict):
            account_maps = {}

        def _is_enabled_key(base_key: str, account_id: str = "") -> bool:
            if available is None:
                return True
            if account_id:
                return (
                    f"{base_key}:{account_id}" in available
                    or base_key in available
                )
            return base_key in available

        def _build_channel(
            *,
            base_key: str,
            ch_cls: Any,
            ch_config: Any,
            alias_channel: str | None = None,
        ) -> BaseChannel | None:
            if ch_config is None:
                return None
            try:
                if base_key == "console":
                    ch_obj = ch_cls.from_config(
                        process,
                        ch_config,
                        on_reply_sent=on_last_dispatch,
                    )
                else:
                    filter_tool_messages = getattr(
                        ch_config,
                        "filter_tool_messages",
                        False,
                    )
                    try:
                        ch_obj = ch_cls.from_config(
                            process,
                            ch_config,
                            on_reply_sent=on_last_dispatch,
                            show_tool_details=show_tool_details,
                            filter_tool_messages=filter_tool_messages,
                        )
                    except TypeError:
                        ch_obj = ch_cls.from_config(
                            process,
                            ch_config,
                            on_reply_sent=on_last_dispatch,
                            show_tool_details=show_tool_details,
                        )
            except Exception:
                logger.exception(
                    "Failed to create channel from config: %s",
                    alias_channel or base_key,
                )
                return None

            if (
                alias_channel
                and getattr(ch_obj, "channel", "") != alias_channel
            ):
                setattr(ch_obj, "channel", alias_channel)
            return ch_obj

        for key, ch_cls in registry.items():
            if not _is_enabled_key(key):
                continue
            ch_config = getattr(
                config.channels if hasattr(config, "channels") else config,
                key,
                None,
            )
            if ch_config is None and key in extra:
                raw = extra[key]
                ch_config = (
                    SimpleNamespace(**raw) if isinstance(raw, dict) else raw
                )
            if ch_config is None:
                continue

            built = _build_channel(
                base_key=key,
                ch_cls=ch_cls,
                ch_config=ch_config,
            )
            if built is not None:
                channels.append(built)

            per_channel_accounts = account_maps.get(key)
            if not isinstance(per_channel_accounts, dict):
                continue
            base_cfg = _to_dict(ch_config)
            for account_id, account_cfg in per_channel_accounts.items():
                account_id_s = str(account_id or "").strip()
                if not account_id_s or not _is_enabled_key(key, account_id_s):
                    continue
                merged_cfg = dict(base_cfg)
                if isinstance(account_cfg, dict):
                    merged_cfg.update(account_cfg)
                merged_cfg.setdefault("enabled", True)
                if not bool(merged_cfg.get("enabled", True)):
                    continue
                merged_cfg.setdefault(
                    "bot_prefix",
                    base_cfg.get("bot_prefix", ""),
                )
                merged_cfg["account_id"] = account_id_s
                alias_name = f"{key}:{account_id_s}"
                merged_cfg["channel_alias"] = alias_name
                built_account = _build_channel(
                    base_key=key,
                    ch_cls=ch_cls,
                    ch_config=_to_namespace(merged_cfg),
                    alias_channel=alias_name,
                )
                if built_account is None:
                    continue
                channels.append(built_account)

        return cls(channels)

    # ── enqueue mechanics ──────────────────────────────────────────

    def _make_enqueue_cb(self, channel_id: str) -> Callable[[Any], None]:
        """Return a callback that enqueues payload for the given channel."""

        def cb(payload: Any) -> None:
            self.enqueue(channel_id, payload)

        return cb

    def _enqueue_one(self, channel_id: str, payload: Any) -> None:
        """Run on event loop: enqueue or append to pending if session is
        in progress.
        """
        q = self._queues.get(channel_id)
        if not q:
            logger.debug("enqueue: no queue for channel=%s", channel_id)
            return

        ch = next((c for c in self.channels if c.channel == channel_id), None)
        if not ch:
            q.put_nowait(payload)
            return

        key = ch.get_debounce_key(payload)
        if (channel_id, key) in self._in_progress:
            self._pending.setdefault((channel_id, key), []).append(payload)
            return
        q.put_nowait(payload)

    def enqueue(self, channel_id: str, payload: Any) -> None:
        """Enqueue a payload for the channel. Thread-safe.

        If the session is already being processed, payload is held in
        pending and merged when the worker finishes.
        """
        if not self._queues.get(channel_id):
            logger.debug("enqueue: no queue for channel=%s", channel_id)
            return
        if self._loop is None:
            logger.warning("enqueue: loop not set for channel=%s", channel_id)
            return
        self._loop.call_soon_threadsafe(
            self._enqueue_one,
            channel_id,
            payload,
        )

    # ── consumer loop ──────────────────────────────────────────────

    async def _consume_channel_loop(
        self,
        channel_id: str,
        worker_index: int,
    ) -> None:
        """One consumer worker: pop payload, drain queue of same session,
        mark in progress, merge batch, process, flush pending.
        """
        q = self._queues.get(channel_id)
        if not q:
            return
        while True:
            try:
                payload = await q.get()
                ch_obj = self.get(channel_id)
                if not ch_obj:
                    continue
                key = ch_obj.get_debounce_key(payload)
                key_lock = self._key_locks.setdefault(
                    (channel_id, key),
                    asyncio.Lock(),
                )
                async with key_lock:
                    self._in_progress.add((channel_id, key))
                    batch = _drain_same_key(q, ch_obj, key, payload)
                try:
                    await _process_batch(ch_obj, batch)
                finally:
                    self._in_progress.discard((channel_id, key))
                    pending = self._pending.pop((channel_id, key), [])
                    _put_pending_merged(ch_obj, q, pending)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception(
                    "channel consume failed: channel=%s worker=%s",
                    channel_id,
                    worker_index,
                )

    def _spawn_consumers_for_channel(self, channel_id: str) -> None:
        """Spawn consumer workers for a channel queue if not existing."""
        if channel_id not in self._queues:
            return
        if self._consumer_tasks_by_channel.get(channel_id):
            return
        tasks: List[asyncio.Task] = []
        for w in range(_CONSUMER_WORKERS_PER_CHANNEL):
            task = asyncio.create_task(
                self._consume_channel_loop(channel_id, w),
                name=f"channel_consumer_{channel_id}_{w}",
            )
            tasks.append(task)
            self._consumer_tasks.append(task)
        self._consumer_tasks_by_channel[channel_id] = tasks

    async def _cancel_consumers_for_channel(self, channel_id: str) -> None:
        """Cancel all consumer workers for one channel."""
        tasks = self._consumer_tasks_by_channel.pop(channel_id, [])
        if not tasks:
            return
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        task_ids = {id(t) for t in tasks}
        self._consumer_tasks = [
            t for t in self._consumer_tasks if id(t) not in task_ids
        ]

    # ── lifecycle ──────────────────────────────────────────────────

    async def start_all(self) -> None:
        """Start all channels: create queues, consumer workers, then start."""
        self._loop = asyncio.get_running_loop()
        async with self._lock:
            snapshot = list(self.channels)

        # Create queues and set enqueue callbacks
        for ch in snapshot:
            if getattr(ch, "uses_manager_queue", True):
                self._queues[ch.channel] = asyncio.Queue(
                    maxsize=_CHANNEL_QUEUE_MAXSIZE,
                )
                ch.set_enqueue(self._make_enqueue_cb(ch.channel))

        # Spawn consumer workers
        for ch in snapshot:
            if ch.channel in self._queues:
                self._spawn_consumers_for_channel(ch.channel)

        logger.debug(
            "starting channels=%s queues=%s",
            [ch.channel for ch in snapshot],
            list(self._queues.keys()),
        )

        # Start each channel
        for ch in snapshot:
            try:
                await ch.start()
                logger.info("Channel started: %s", ch.channel)
            except Exception:
                logger.exception("Failed to start channel: %s", ch.channel)

    async def stop_all(self) -> None:
        """Stop all channels, cancel consumers, clear queues."""
        self._in_progress.clear()
        self._pending.clear()
        self._key_locks.clear()

        for channel_id in list(self._consumer_tasks_by_channel.keys()):
            await self._cancel_consumers_for_channel(channel_id)
        self._consumer_tasks.clear()
        self._consumer_tasks_by_channel.clear()
        self._queues.clear()

        async with self._lock:
            snapshot = list(self.channels)
        for ch in snapshot:
            ch.set_enqueue(None)

        async def _stop(ch: BaseChannel) -> None:
            try:
                await ch.stop()
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception("Failed to stop channel: %s", ch.channel)

        await asyncio.gather(*[_stop(ch) for ch in reversed(snapshot)])

    # ── channel access ─────────────────────────────────────────────

    async def get_channel(self, channel: str) -> Optional[BaseChannel]:
        """Get channel by name (async, lock-safe)."""
        async with self._lock:
            for ch in self.channels:
                if ch.channel == channel:
                    return ch
            return None

    # ── hot-swap ───────────────────────────────────────────────────

    async def replace_channel(self, new_channel: BaseChannel) -> None:
        """Replace a channel by name: start new → swap → stop old.

        Useful for live config updates (e.g. new bot token).
        """
        name = new_channel.channel

        uses_queue = bool(getattr(new_channel, "uses_manager_queue", True))

        # Ensure queue/workers state matches channel mode.
        if uses_queue:
            if name not in self._queues:
                self._queues[name] = asyncio.Queue(
                    maxsize=_CHANNEL_QUEUE_MAXSIZE,
                )
            self._spawn_consumers_for_channel(name)
            new_channel.set_enqueue(self._make_enqueue_cb(name))
        else:
            await self._cancel_consumers_for_channel(name)
            self._queues.pop(name, None)
            new_channel.set_enqueue(None)

        # Start new channel (may be slow, e.g. WS connection)
        logger.info("Pre-starting new channel: %s", name)
        try:
            await new_channel.start()
        except Exception:
            logger.exception("Failed to start new channel: %s", name)
            try:
                await new_channel.stop()
            except Exception:
                pass
            raise

        # Swap + stop old inside lock
        async with self._lock:
            old_channel = None
            for i, ch in enumerate(self.channels):
                if ch.channel == name:
                    old_channel = ch
                    self.channels[i] = new_channel
                    break
            if old_channel is None:
                self.channels.append(new_channel)
                logger.info("Added new channel: %s", name)
            else:
                logger.info("Stopping old channel: %s", name)
                try:
                    await old_channel.stop()
                except asyncio.CancelledError:
                    pass
                except Exception:
                    logger.exception("Failed to stop old channel: %s", name)

    async def remove_channel(self, name: str) -> bool:
        """Remove a channel by name and stop its runtime resources."""
        async with self._lock:
            old_channel = None
            for i, ch in enumerate(self.channels):
                if ch.channel == name:
                    old_channel = ch
                    self.channels.pop(i)
                    break
        if old_channel is None:
            return False

        old_channel.set_enqueue(None)
        try:
            await old_channel.stop()
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Failed to stop removed channel: %s", name)

        await self._cancel_consumers_for_channel(name)
        self._queues.pop(name, None)

        self._in_progress = {
            item for item in self._in_progress if item[0] != name
        }
        self._pending = {
            k: v for k, v in self._pending.items() if k[0] != name
        }
        self._key_locks = {
            k: v for k, v in self._key_locks.items() if k[0] != name
        }
        logger.info("Removed channel: %s", name)
        return True

    # ── proactive send helpers ─────────────────────────────────────

    async def send_event(
        self,
        *,
        channel: str,
        user_id: str,
        session_id: str,
        event: Any,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send a runner event to a specific channel."""
        requested = str(channel or "").strip().lower()
        base, _, account_id = requested.partition(":")
        ch = await self.get_channel(requested)
        if not ch and base:
            ch = await self.get_channel(base)
        if not ch:
            raise KeyError(f"channel not found: {channel}")
        merged_meta = dict(meta or {})
        if account_id:
            merged_meta.setdefault("account_id", account_id)
        merged_meta["session_id"] = session_id
        merged_meta["user_id"] = user_id
        bot_prefix = getattr(ch, "bot_prefix", None) or getattr(
            ch,
            "_bot_prefix",
            None,
        )
        if bot_prefix and "bot_prefix" not in merged_meta:
            merged_meta["bot_prefix"] = bot_prefix
        await ch.send_event(
            user_id=user_id,
            session_id=session_id,
            event=event,
            meta=merged_meta,
        )

    async def send_text(
        self,
        *,
        channel: str,
        user_id: str,
        session_id: str,
        text: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send plain text to a specific channel (for cron / proactive)."""
        requested = str(channel or "").strip().lower()
        base, _, account_id = requested.partition(":")
        ch = await self.get_channel(requested)
        if not ch and base:
            ch = await self.get_channel(base)
        if not ch:
            raise KeyError(f"channel not found: {channel}")

        to_handle = ch.to_handle_from_target(
            user_id=user_id,
            session_id=session_id,
        )
        logger.info(
            "send_text: channel=%s user=%s session=%s to_handle=%s",
            channel,
            (user_id or "")[:40],
            (session_id or "")[:40],
            (to_handle or "")[:60],
        )

        merged_meta = dict(meta or {})
        if account_id:
            merged_meta.setdefault("account_id", account_id)
        bot_prefix = getattr(ch, "bot_prefix", None) or getattr(
            ch,
            "_bot_prefix",
            None,
        )
        if bot_prefix and "bot_prefix" not in merged_meta:
            merged_meta["bot_prefix"] = bot_prefix
        merged_meta["session_id"] = session_id
        merged_meta["user_id"] = user_id

        await ch.send_content_parts(
            to_handle,
            [TextContent(type=ContentType.TEXT, text=text)],
            merged_meta,
        )

    # ── listing ────────────────────────────────────────────────────

    def list_channels(self) -> list[dict[str, Any]]:
        """List registered channels with basic info."""
        return [
            {
                "name": ch.channel,
                "type": ch.__class__.__name__,
                "has_queue": ch.channel in self._queues,
            }
            for ch in self.channels
        ]

    def get_runtime_stats(self) -> dict[str, Any]:
        """Return lightweight channel runtime observability stats."""
        snapshot = list(self.channels)
        by_channel: list[dict[str, Any]] = []
        total_queue_size = 0
        total_pending_items = 0
        total_in_progress = 0
        total_workers = 0
        alive_workers = 0

        for ch in snapshot:
            name = ch.channel
            q = self._queues.get(name)
            qsize = q.qsize() if q is not None else 0
            qmax = q.maxsize if q is not None else 0
            workers = self._consumer_tasks_by_channel.get(name, [])
            worker_total = len(workers)
            worker_alive = sum(1 for task in workers if not task.done())
            in_progress = sum(
                1
                for (channel_id, _) in self._in_progress
                if channel_id == name
            )
            pending_items = sum(
                len(items)
                for (channel_id, _), items in self._pending.items()
                if channel_id == name
            )

            total_queue_size += qsize
            total_pending_items += pending_items
            total_in_progress += in_progress
            total_workers += worker_total
            alive_workers += worker_alive

            by_channel.append(
                {
                    "name": name,
                    "type": ch.__class__.__name__,
                    "has_queue": q is not None,
                    "queue_size": qsize,
                    "queue_maxsize": qmax,
                    "pending_items": pending_items,
                    "in_progress_keys": in_progress,
                    "consumer_workers": worker_total,
                    "alive_workers": worker_alive,
                },
            )

        return {
            "registered_channels": len(snapshot),
            "queued_messages": total_queue_size,
            "pending_messages": total_pending_items,
            "in_progress_keys": total_in_progress,
            "consumer_workers": {
                "total": total_workers,
                "alive": alive_workers,
            },
            "channels": by_channel,
        }
