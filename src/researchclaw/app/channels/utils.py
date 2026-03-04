"""Channel utilities – helpers shared across channel implementations.

Key improvements over CoPaw:
- ``file_url_to_local_path``: handles file:// URLs, Windows quirks,
  and plain paths uniformly.
- ``make_process_from_runner``: factory that binds a runner's
  ``stream_query`` as the channel's process handler.
- ``download_media_file``: generic async media downloader with
  configurable directory, dedup, and extension guessing.
- ``split_long_message``: splits text at word/line boundaries for
  platforms with message length limits.
"""
from __future__ import annotations

import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Optional
from urllib.parse import unquote, urlparse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# File URL conversion
# ---------------------------------------------------------------------------


def file_url_to_local_path(url: str) -> Optional[str]:
    """Convert a ``file://`` URL or plain path to a local filesystem path.

    Handles:
    - ``file:///path/to/file``
    - ``file://localhost/path``
    - Plain absolute / relative paths
    - Windows drive-letter paths (``C:\\...``)

    Returns ``None`` if the URL cannot be resolved.
    """
    if not url:
        return None

    url = url.strip()

    # Plain paths (absolute or relative)
    if not url.startswith("file://"):
        if os.path.exists(url):
            return os.path.abspath(url)
        # Still return it – caller may create the file later
        return url

    # file:// URL
    parsed = urlparse(url)
    path = unquote(parsed.path)

    if sys.platform == "win32" and path.startswith("/") and len(path) > 2:
        # /C:/Users/... → C:/Users/...
        if path[2] == ":":
            path = path[1:]

    if not path:
        return None

    return os.path.normpath(path)


# ---------------------------------------------------------------------------
# Process handler factory
# ---------------------------------------------------------------------------


def make_process_from_runner(runner: Any) -> Callable[[Any], AsyncIterator]:
    """Return ``runner.stream_query`` as a channel process handler.

    This bridges the runner's streaming interface to the channel's
    expected ``ProcessHandler`` signature.
    """
    return runner.stream_query


# ---------------------------------------------------------------------------
# Media download helper
# ---------------------------------------------------------------------------


async def download_media_file(
    url: str,
    *,
    media_dir: str | Path = "~/.researchclaw/media",
    filename_hint: str = "",
    http_session: Optional[Any] = None,
) -> Optional[str]:
    """Download a media file to local disk.

    Args:
        url: Remote URL to download.
        media_dir: Directory to save files (expanded with ``~``).
        filename_hint: Suggested filename for extension guessing.
        http_session: Optional ``aiohttp.ClientSession`` to reuse.

    Returns:
        Local filesystem path, or ``None`` on failure.
    """
    try:
        import aiohttp
    except ImportError:
        logger.warning("aiohttp not installed; cannot download media")
        return None

    media_path = Path(media_dir).expanduser()
    media_path.mkdir(parents=True, exist_ok=True)

    # Determine extension
    suffix = ""
    parsed = urlparse(url)
    if parsed.path:
        suffix = Path(parsed.path).suffix
    if not suffix and filename_hint:
        suffix = Path(filename_hint).suffix
    if not suffix:
        suffix = ".bin"

    local_name = f"{uuid.uuid4().hex[:12]}{suffix}"
    local_path = media_path / local_name

    own_session = http_session is None
    session = http_session or aiohttp.ClientSession()
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as resp:
            if resp.status != 200:
                logger.warning(
                    "download_media_file: HTTP %s for %s",
                    resp.status,
                    url,
                )
                return None
            data = await resp.read()
            local_path.write_bytes(data)
            return str(local_path)
    except Exception:
        logger.exception("download_media_file failed: %s", url)
        return None
    finally:
        if own_session:
            await session.close()


# ---------------------------------------------------------------------------
# Text splitting for platform limits
# ---------------------------------------------------------------------------


def split_long_message(
    text: str,
    max_length: int = 4000,
    *,
    split_on: str = "\n",
) -> list[str]:
    """Split text into chunks respecting ``max_length``.

    Tries to split on ``split_on`` boundaries (default: newlines).
    Falls back to hard cut if a single line exceeds ``max_length``.
    """
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in text.split(split_on):
        line_with_sep = line + split_on
        if current_len + len(line_with_sep) > max_length and current:
            chunks.append(split_on.join(current))
            current = []
            current_len = 0

        if len(line_with_sep) > max_length:
            # Hard-split very long lines
            while line:
                chunk = line[:max_length]
                line = line[max_length:]
                if current:
                    combined = split_on.join(current) + split_on + chunk
                    chunks.append(combined)
                    current = []
                    current_len = 0
                else:
                    chunks.append(chunk)
        else:
            current.append(line)
            current_len += len(line_with_sep)

    if current:
        chunks.append(split_on.join(current))

    return [c for c in chunks if c.strip()]


# ---------------------------------------------------------------------------
# Markdown sanitisation
# ---------------------------------------------------------------------------


def sanitize_markdown_for_channel(
    text: str,
    *,
    strip_html: bool = True,
    max_heading_level: int = 3,
) -> str:
    """Light sanitisation of markdown for chat platforms.

    - Caps heading depth (``####`` → ``###`` etc.)
    - Optionally strips HTML tags
    - Normalises excessive blank lines
    """
    import re

    lines = text.split("\n")
    out: list[str] = []
    blank_count = 0

    for line in lines:
        # Cap heading level
        m = re.match(r"^(#{1,6})\s", line)
        if m:
            level = min(len(m.group(1)), max_heading_level)
            line = "#" * level + line[len(m.group(1)) :]

        # Strip HTML
        if strip_html:
            line = re.sub(r"<[^>]+>", "", line)

        # Collapse blank lines
        if not line.strip():
            blank_count += 1
            if blank_count <= 2:
                out.append(line)
        else:
            blank_count = 0
            out.append(line)

    return "\n".join(out)
