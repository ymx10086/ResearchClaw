"""Channel schema: channel type identifiers, routing, and conversion protocol.

Provides ChannelAddress for unified routing, built-in channel type constants,
and the ChannelMessageConverter protocol for channel implementations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@dataclass
class ChannelAddress:
    """Unified routing address for outbound messages.

    Replaces ad-hoc meta keys (channel_id, user_id, session_webhook, etc.)
    with a structured address.
    """

    kind: str  # "dm" | "channel" | "webhook" | "console" | ...
    id: str
    extra: Optional[Dict[str, Any]] = field(default=None)

    def to_handle(self) -> str:
        """String handle for routing (e.g. console:main)."""
        if self.extra and "to_handle" in self.extra:
            return str(self.extra["to_handle"])
        return f"{self.kind}:{self.id}"


# Built-in channel type identifiers — plugin channels use arbitrary str keys.
BUILTIN_CHANNEL_TYPES: tuple[str, ...] = (
    "console",
    "telegram",
    "discord",
    "dingtalk",
    "feishu",
    "qq",
    "imessage",
    "slack",  # planned
    "wechat",  # planned
)

# ChannelType is str to allow plugin channels
ChannelType = str

# Default channel when none is specified
DEFAULT_CHANNEL: ChannelType = "console"


@runtime_checkable
class ChannelMessageConverter(Protocol):
    """Protocol for channel message conversion.

    Channels convert native payloads to agent requests and send responses.
    """

    def build_agent_request_from_native(self, native_payload: Any) -> Any:
        """Convert this channel's native message payload to an agent request."""
        ...

    async def send_response(
        self,
        to_handle: str,
        response: Any,
        meta: Optional[dict] = None,
    ) -> None:
        """Convert agent response to channel reply and send."""
        ...


# ----- Research-specific extensions -----


@dataclass
class ResearchDispatchTarget:
    """Target for dispatching research-related notifications.

    Beyond CoPaw's simple user_id/session_id, supports topic-based routing
    for research alerts (e.g. new paper notifications, deadline reminders).
    """

    user_id: str
    session_id: str
    topics: List[str] = field(default_factory=list)
    priority: str = "normal"  # "low" | "normal" | "high" | "urgent"
