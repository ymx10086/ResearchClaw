"""Message renderer – converts agent events into sendable content parts.

Framework-independent: works with plain dicts and lightweight dataclasses.
Also handles ``agentscope_runtime`` types transparently when available.

Key improvements over CoPaw:
- No hard dependency on ``agentscope_runtime`` schemas.
- Configurable rendering style (emoji, tool detail verbosity, truncation).
- Research-specific formatting: paper citations, search results, etc.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import (
    ContentType,
    TextContent,
    ImageContent,
    VideoContent,
    AudioContent,
    FileContent,
    RefusalContent,
    OutgoingContentPart,
)

logger = logging.getLogger(__name__)


@dataclass
class RenderStyle:
    """Controls how messages are rendered for channel delivery."""

    show_tool_details: bool = True
    filter_tool_messages: bool = False
    show_emoji: bool = True
    max_tool_output_len: int = 300
    # Research-specific: render paper citations as structured blocks
    render_citations: bool = True
    # Markdown format control
    use_markdown: bool = True


class MessageRenderer:
    """Converts agent message events into a flat list of
    :class:`OutgoingContentPart`.

    Handles:
    - Plain text messages
    - Tool call / tool output formatting with emoji indicators
    - Media content (image, video, audio, file)
    - Thinking / reasoning blocks
    - Refusal content
    - Research-specific: paper citation blocks, search summary tables
    """

    def __init__(self, style: Optional[RenderStyle] = None) -> None:
        self.style = style or RenderStyle()

    # ── public API ─────────────────────────────────────────────────

    def message_to_parts(self, message: Any) -> List[OutgoingContentPart]:
        """Convert one message event to a list of sendable parts.

        ``message`` can be:
        - An agentscope_runtime ``Event`` (has ``.data`` with ``Message``).
        - A plain dict ``{"type": "message", "content": [...]}``.
        - Any object with a ``.content`` attribute (list of content parts).
        """
        content = self._extract_content(message)
        if not content:
            return []

        parts: List[OutgoingContentPart] = []
        for item in content:
            rendered = self._render_content_item(item)
            parts.extend(rendered)
        return parts

    def parts_to_text(
        self,
        parts: List[OutgoingContentPart],
        *,
        prefix: str = "",
    ) -> str:
        """Merge multiple parts into a single text body (fallback render)."""
        text_parts: List[str] = []
        for p in parts:
            t = getattr(p, "type", None)
            t_val = (
                t.value if isinstance(t, ContentType) else str(t) if t else ""
            )
            if t_val == ContentType.TEXT.value and getattr(p, "text", None):
                text_parts.append(p.text)
            elif t_val == ContentType.REFUSAL.value and getattr(
                p,
                "refusal",
                None,
            ):
                text_parts.append(p.refusal)
            elif t_val == ContentType.IMAGE.value and getattr(
                p,
                "image_url",
                None,
            ):
                text_parts.append(f"[Image: {p.image_url}]")
            elif t_val == ContentType.VIDEO.value and getattr(
                p,
                "video_url",
                None,
            ):
                text_parts.append(f"[Video: {p.video_url}]")
            elif t_val == ContentType.AUDIO.value:
                text_parts.append("[Audio]")
            elif t_val == ContentType.FILE.value:
                url = getattr(p, "file_url", "") or getattr(p, "file_id", "")
                text_parts.append(f"[File: {url}]")
        body = "\n".join(text_parts) if text_parts else ""
        if prefix and body:
            body = prefix + body
        return body

    # ── content extraction ─────────────────────────────────────────

    def _extract_content(self, message: Any) -> List[Any]:
        """Pull the content list from various message shapes."""
        # agentscope_runtime Event: event.data.content
        data = getattr(message, "data", None)
        if data is not None:
            content = getattr(data, "content", None)
            if content is not None:
                return (
                    list(content)
                    if isinstance(content, (list, tuple))
                    else [content]
                )

        # Object with .content (Message-like)
        content = getattr(message, "content", None)
        if content is not None:
            return (
                list(content)
                if isinstance(content, (list, tuple))
                else [content]
            )

        # dict with "content" key
        if isinstance(message, dict):
            content = message.get("content")
            if content is not None:
                return (
                    list(content)
                    if isinstance(content, (list, tuple))
                    else [content]
                )

        return []

    # ── per-item rendering ─────────────────────────────────────────

    def _render_content_item(self, item: Any) -> List[OutgoingContentPart]:
        """Render one content item into part(s)."""
        t = getattr(item, "type", None)
        if t is None and isinstance(item, dict):
            t = item.get("type")

        t_val = t.value if isinstance(t, ContentType) else str(t) if t else ""

        # Text
        if t_val in (ContentType.TEXT.value, "text"):
            text = (
                getattr(item, "text", None)
                or (item.get("text") if isinstance(item, dict) else None)
                or ""
            )
            if not text.strip():
                return []
            return [TextContent(text=text)]

        # Refusal
        if t_val in (ContentType.REFUSAL.value, "refusal"):
            refusal = (
                getattr(item, "refusal", None)
                or (item.get("refusal") if isinstance(item, dict) else None)
                or ""
            )
            if not refusal.strip():
                return []
            return [RefusalContent(refusal=refusal)]

        # Image
        if t_val in (ContentType.IMAGE.value, "image"):
            url = (
                getattr(item, "image_url", None)
                or (item.get("image_url") if isinstance(item, dict) else None)
                or ""
            )
            if url:
                return [ImageContent(image_url=url)]
            return []

        # Video
        if t_val in (ContentType.VIDEO.value, "video"):
            url = (
                getattr(item, "video_url", None)
                or (item.get("video_url") if isinstance(item, dict) else None)
                or ""
            )
            if url:
                return [VideoContent(video_url=url)]
            return []

        # Audio
        if t_val in (ContentType.AUDIO.value, "audio"):
            data = (
                getattr(item, "data", None)
                or (item.get("data") if isinstance(item, dict) else None)
                or ""
            )
            return [AudioContent(data=data)]

        # File
        if t_val in (ContentType.FILE.value, "file"):
            file_url = (
                getattr(item, "file_url", None)
                or (item.get("file_url") if isinstance(item, dict) else None)
                or ""
            )
            file_id = (
                getattr(item, "file_id", None)
                or (item.get("file_id") if isinstance(item, dict) else None)
                or ""
            )
            if file_url or file_id:
                return [FileContent(file_url=file_url, file_id=file_id)]
            return []

        # Tool call
        if t_val in ("tool_call", "function_call"):
            return self._render_tool_call(item)

        # Tool output / function result
        if t_val in ("tool_output", "tool_result", "function_result"):
            return self._render_tool_output(item)

        # Thinking / reasoning block
        if t_val in ("thinking", "reasoning"):
            return self._render_thinking(item)

        # Unknown: try to extract text
        text = getattr(item, "text", None) or (
            item.get("text") if isinstance(item, dict) else None
        )
        if text and str(text).strip():
            return [TextContent(text=str(text))]

        return []

    # ── tool call rendering ────────────────────────────────────────

    def _render_tool_call(self, item: Any) -> List[OutgoingContentPart]:
        """Format a tool call as a styled text block."""
        if self.style.filter_tool_messages or not self.style.show_tool_details:
            return []

        name = (
            getattr(item, "name", None)
            or getattr(item, "function_name", None)
            or (item.get("name") if isinstance(item, dict) else None)
            or (
                item.get("function", {}).get("name")
                if isinstance(item, dict)
                else None
            )
            or "unknown"
        )
        args = (
            getattr(item, "arguments", None)
            or (item.get("arguments") if isinstance(item, dict) else None)
            or (
                item.get("function", {}).get("arguments")
                if isinstance(item, dict)
                else None
            )
        )

        emoji = "🔧 " if self.style.show_emoji else ""
        label = f"{emoji}Tool Call: **{name}**"

        if args:
            args_str = self._fmt_args(args)
            if args_str:
                label += f"\n```json\n{args_str}\n```"

        return [TextContent(text=label)]

    def _render_tool_output(self, item: Any) -> List[OutgoingContentPart]:
        """Format a tool output as a styled text block."""
        if self.style.filter_tool_messages or not self.style.show_tool_details:
            return []

        name = (
            getattr(item, "name", None)
            or (item.get("name") if isinstance(item, dict) else None)
            or ""
        )
        output = (
            getattr(item, "output", None)
            or getattr(item, "content", None)
            or (item.get("output") if isinstance(item, dict) else None)
            or (item.get("content") if isinstance(item, dict) else None)
            or ""
        )

        emoji = "✅ " if self.style.show_emoji else ""
        label = f"{emoji}Tool Result"
        if name:
            label += f": **{name}**"

        output_str = str(output)
        max_len = self.style.max_tool_output_len
        if len(output_str) > max_len:
            output_str = output_str[:max_len] + "…"

        if output_str.strip():
            label += f"\n```\n{output_str}\n```"

        return [TextContent(text=label)]

    def _render_thinking(self, item: Any) -> List[OutgoingContentPart]:
        """Format a thinking/reasoning block."""
        text = (
            getattr(item, "text", None)
            or getattr(item, "thinking", None)
            or (item.get("text") if isinstance(item, dict) else None)
            or (item.get("thinking") if isinstance(item, dict) else None)
            or ""
        )
        if not str(text).strip():
            return []
        emoji = "💭 " if self.style.show_emoji else ""
        return [TextContent(text=f"{emoji}*{text}*")]

    # ── helpers ────────────────────────────────────────────────────

    def _fmt_args(self, args: Any) -> str:
        """Format tool call arguments to a compact JSON string."""
        if isinstance(args, str):
            try:
                parsed = json.loads(args)
                return json.dumps(parsed, ensure_ascii=False, indent=2)
            except (json.JSONDecodeError, TypeError):
                return args
        if isinstance(args, dict):
            return json.dumps(args, ensure_ascii=False, indent=2)
        return str(args) if args else ""

    # ── research-specific rendering ────────────────────────────────

    def render_paper_citation(
        self,
        title: str,
        authors: List[str],
        year: Optional[int] = None,
        url: Optional[str] = None,
        abstract: Optional[str] = None,
    ) -> TextContent:
        """Render a structured paper citation block.

        This is a ResearchClaw enhancement not present in CoPaw.
        """
        parts = []
        emoji = "📄 " if self.style.show_emoji else ""
        parts.append(f"{emoji}**{title}**")

        if authors:
            auth_str = ", ".join(authors[:5])
            if len(authors) > 5:
                auth_str += f" et al. ({len(authors)} authors)"
            parts.append(f"  Authors: {auth_str}")

        if year:
            parts.append(f"  Year: {year}")

        if url:
            parts.append(f"  URL: {url}")

        if abstract and self.style.render_citations:
            max_len = 200
            abs_text = (
                abstract[:max_len] + "…"
                if len(abstract) > max_len
                else abstract
            )
            parts.append(f"  Abstract: {abs_text}")

        return TextContent(text="\n".join(parts))

    def render_search_summary(
        self,
        query: str,
        results_count: int,
        top_results: Optional[List[Dict[str, Any]]] = None,
    ) -> TextContent:
        """Render a search results summary block.

        ResearchClaw enhancement for academic search results.
        """
        emoji = "🔍 " if self.style.show_emoji else ""
        lines = [f"{emoji}Search: **{query}** — {results_count} results"]

        if top_results:
            for i, r in enumerate(top_results[:5], 1):
                title = r.get("title", "Untitled")
                year = r.get("year", "")
                year_str = f" ({year})" if year else ""
                lines.append(f"  {i}. {title}{year_str}")

        return TextContent(text="\n".join(lines))
