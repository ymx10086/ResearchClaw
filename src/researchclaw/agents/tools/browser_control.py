"""Browser control tool for web browsing and information gathering."""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def browse_url(
    url: str,
    extract_text: bool = True,
    screenshot: bool = False,
    wait_seconds: int = 3,
) -> dict[str, Any]:
    """Open a URL and extract content.

    Parameters
    ----------
    url:
        The URL to visit.
    extract_text:
        Whether to extract page text content.
    screenshot:
        Whether to take a screenshot.
    wait_seconds:
        Seconds to wait for page load.

    Returns
    -------
    dict
        Result with ``title``, ``text``, ``url``, and optionally ``screenshot_base64``.
    """
    try:
        import httpx

        # Simple HTTP fetch for text extraction
        resp = httpx.get(
            url,
            timeout=30,
            follow_redirects=True,
            headers={
                "User-Agent": "ResearchClaw/1.0 (Academic Research Assistant)",
            },
        )
        resp.raise_for_status()

        result: dict[str, Any] = {
            "url": str(resp.url),
            "status_code": resp.status_code,
        }

        if extract_text:
            content_type = resp.headers.get("content-type", "")
            if "html" in content_type:
                result["text"] = _extract_text_from_html(resp.text)
                result["title"] = _extract_title_from_html(resp.text)
            else:
                text = resp.text
                if len(text) > 200_000:
                    text = text[:200_000] + "\n... [truncated]"
                result["text"] = text
                result["title"] = ""

        return result

    except ImportError:
        return {"error": "httpx not installed. Run: pip install httpx"}
    except Exception as e:
        logger.exception("Browse failed")
        return {"error": f"Failed to browse URL: {e}"}


def _extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML."""
    import re

    # Remove scripts and styles
    text = re.sub(
        r"<script[^>]*>.*?</script>",
        "",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    text = re.sub(
        r"<style[^>]*>.*?</style>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Clean up whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Truncate
    if len(text) > 200_000:
        text = text[:200_000] + "\n... [truncated]"
    return text


def _extract_title_from_html(html: str) -> str:
    """Extract the page title from HTML."""
    import re

    match = re.search(
        r"<title[^>]*>(.*?)</title>",
        html,
        re.DOTALL | re.IGNORECASE,
    )
    return match.group(1).strip() if match else ""
