"""Desktop/screen screenshot tool.

Captures screenshots of the entire desktop or individual windows.
Useful for documenting experimental results, GUI applications,
and visual debugging.

Supports: Windows, Linux, macOS.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
import tempfile
import time
from typing import Any

logger = logging.getLogger(__name__)


def _tool_error(msg: str) -> dict[str, Any]:
    """Return an error response dict."""
    return {"ok": False, "error": msg}


def _tool_ok(path: str, message: str) -> dict[str, Any]:
    """Return a success response dict."""
    return {
        "ok": True,
        "path": os.path.abspath(path),
        "message": message,
    }


def _capture_mss(path: str) -> dict[str, Any]:
    """Full-screen capture using mss (Windows, Linux, macOS)."""
    try:
        import mss
    except ImportError:
        return _tool_error(
            "desktop_screenshot requires the 'mss' package. "
            "Install with: pip install mss",
        )
    try:
        with mss.mss() as sct:
            # mon=0: all monitors combined
            sct.shot(mon=0, output=path)
        if not os.path.isfile(path):
            return _tool_error("mss reported success but file was not created")
        return _tool_ok(path, f"Desktop screenshot saved to {path}")
    except Exception as e:
        return _tool_error(f"desktop_screenshot (mss) failed: {e!s}")


def _capture_macos_screencapture(
    path: str,
    capture_window: bool,
) -> dict[str, Any]:
    """macOS: screencapture (supports window selection with -w)."""
    cmd = ["screencapture", "-x", path]
    if capture_window:
        cmd.insert(-1, "-w")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip() or "Unknown error"
            return _tool_error(f"screencapture failed: {stderr}")
        if not os.path.isfile(path):
            return _tool_error(
                "screencapture reported success but file was not created",
            )
        return _tool_ok(path, f"Desktop screenshot saved to {path}")
    except subprocess.TimeoutExpired:
        return _tool_error(
            "screencapture timed out (e.g. window selection cancelled)",
        )
    except Exception as e:
        return _tool_error(f"desktop_screenshot failed: {e!s}")


async def desktop_screenshot(
    path: str = "",
    capture_window: bool = False,
) -> dict[str, Any]:
    """Capture a screenshot of the entire desktop or a single window.

    Supported platforms: Windows, Linux, macOS. Full-screen capture uses
    the mss library. On macOS, capture_window=True uses screencapture.

    Args:
        path: Optional path to save the screenshot. If empty, saves to
            a temp file. Should end in .png.
        capture_window: If True on macOS, lets the user click a window
            to capture. On other platforms this is ignored.

    Returns:
        Dict with "ok", "path", and "message" or "error".
    """
    path = (path or "").strip()
    if not path:
        path = os.path.join(
            tempfile.gettempdir(),
            f"desktop_screenshot_{int(time.time())}.png",
        )
    if not path.lower().endswith(".png"):
        path = path.rstrip("/\\") + ".png"

    system = platform.system()

    # macOS: optional window selection via screencapture -w
    if system == "Darwin" and capture_window:
        return _capture_macos_screencapture(path, capture_window=True)

    # Full-screen on all platforms via mss
    return _capture_mss(path)
