"""Send file tool for returning files to the user.

Improvements over CoPaw:
- MIME type dispatch: image/audio/video/generic file blocks
- Dual mode: file:// URL (default) or base64 fallback
- Size limit check
- Research-specific file type hints (.bib, .tex, .csv, .pdf)
"""

from __future__ import annotations

import logging
import mimetypes
import os
from pathlib import Path
from typing import Any, Union

from ..schema import FileBlock

logger = logging.getLogger(__name__)

# Research-specific MIME type additions
mimetypes.add_type("application/x-bibtex", ".bib")
mimetypes.add_type("application/x-latex", ".tex")
mimetypes.add_type("text/x-ris", ".ris")
mimetypes.add_type("application/citeproc+json", ".csl")

# Maximum file size for base64 encoding (50 MB)
_MAX_FILE_SIZE = 50 * 1024 * 1024


def _auto_as_type(mime_type: str) -> str:
    """Determine block type from MIME type."""
    if mime_type.startswith("image/"):
        return "image"
    if mime_type.startswith("audio/"):
        return "audio"
    if mime_type.startswith("video/"):
        return "video"
    return "file"


def send_file(
    file_path: str,
    use_url: bool = True,
) -> Union[dict[str, Any], FileBlock]:
    """Send a file to the user.

    Parameters
    ----------
    file_path:
        Path to the file to send.
    use_url:
        If True, use ``file://`` URL (faster, local only).
        If False, use base64 encoding (portable).

    Returns
    -------
    FileBlock or dict
        File block for the channel to render, or error dict.
    """
    try:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            return {"error": f"File not found: {file_path}"}
        if not path.is_file():
            return {"error": f"Not a file: {file_path}"}

        file_size = path.stat().st_size
        if file_size > _MAX_FILE_SIZE:
            return {
                "error": f"File too large ({file_size / 1024 / 1024:.1f} MB). "
                f"Maximum is {_MAX_FILE_SIZE / 1024 / 1024:.0f} MB.",
            }

        mime_type = (
            mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        )
        as_type = _auto_as_type(mime_type)

        if use_url:
            absolute_path = str(path)
            source: dict[str, str] = {
                "type": "url",
                "url": f"file://{absolute_path}",
            }
        else:
            import base64

            data = base64.b64encode(path.read_bytes()).decode("utf-8")
            source = {"type": "base64", "media_type": mime_type, "data": data}

        # Build response block based on type
        block_data: dict[str, Any] = {
            "type": as_type,
            "source": source,
        }
        if as_type == "file":
            block_data["filename"] = path.name

        return FileBlock(
            type=as_type,
            source=source,
            filename=path.name,
        )

    except Exception as e:
        logger.exception("Failed to send file")
        return {"error": f"Failed to send file: {e}"}
