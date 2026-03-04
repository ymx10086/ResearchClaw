"""PDF paper reader tool.

Extracts text, metadata, and structure from academic paper PDFs.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

from ...constant import PAPERS_DIR

logger = logging.getLogger(__name__)


def read_paper(
    source: str,
    extract_references: bool = False,
    max_pages: Optional[int] = None,
    sections: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Read and extract content from a PDF paper.

    Parameters
    ----------
    source:
        Path to a local PDF file, ArXiv ID (e.g. ``"2301.07041"``),
        or URL to a PDF.
    extract_references:
        Whether to attempt extracting the reference list.
    max_pages:
        Maximum number of pages to extract (None = all).
    sections:
        Optional list of section names to extract specifically
        (e.g. ``["Abstract", "Introduction", "Conclusion"]``).

    Returns
    -------
    dict
        Extracted paper content with keys: ``text``, ``metadata``,
        ``page_count``, ``sections`` (if identifiable), ``references``
        (if requested).
    """
    filepath = _resolve_source(source)
    if filepath is None:
        return {"error": f"Could not resolve paper source: {source}"}

    if not Path(filepath).exists():
        return {"error": f"File not found: {filepath}"}

    # Try pdfplumber first (better table/layout extraction)
    try:
        return _extract_with_pdfplumber(
            filepath,
            extract_references,
            max_pages,
            sections,
        )
    except ImportError:
        pass

    # Fallback to PyPDF2
    try:
        return _extract_with_pypdf2(
            filepath,
            extract_references,
            max_pages,
            sections,
        )
    except ImportError:
        return {
            "error": "No PDF library available. Install: pip install pdfplumber PyPDF2",
        }


def _resolve_source(source: str) -> Optional[str]:
    """Resolve a source string to a local file path."""
    # Already a local file
    if os.path.isfile(source):
        return source

    # Check papers directory
    papers_path = Path(PAPERS_DIR) / source
    if papers_path.exists():
        return str(papers_path)

    # ArXiv ID pattern
    import re

    if re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", source):
        # Try to find already downloaded
        pdf_name = f"{source.replace('/', '_')}.pdf"
        cached = Path(PAPERS_DIR) / pdf_name
        if cached.exists():
            return str(cached)

        # Download from ArXiv
        try:
            from .arxiv_search import arxiv_download

            result = arxiv_download(source)
            if "path" in result:
                return result["path"]
        except Exception:
            logger.debug("Could not download ArXiv paper %s", source)

    # URL
    if source.startswith("http://") or source.startswith("https://"):
        try:
            import httpx

            os.makedirs(PAPERS_DIR, exist_ok=True)
            filename = source.split("/")[-1]
            if not filename.endswith(".pdf"):
                filename += ".pdf"
            filepath = Path(PAPERS_DIR) / filename

            with httpx.stream(
                "GET",
                source,
                timeout=60,
                follow_redirects=True,
            ) as resp:
                resp.raise_for_status()
                with open(filepath, "wb") as f:
                    for chunk in resp.iter_bytes():
                        f.write(chunk)
            return str(filepath)
        except Exception as e:
            logger.debug("Could not download PDF from URL: %s", e)

    return None


def _extract_with_pdfplumber(
    filepath: str,
    extract_references: bool,
    max_pages: Optional[int],
    sections: Optional[list[str]],
) -> dict[str, Any]:
    """Extract using pdfplumber (better quality)."""
    import pdfplumber

    result: dict[str, Any] = {
        "text": "",
        "metadata": {},
        "page_count": 0,
        "tables": [],
    }

    with pdfplumber.open(filepath) as pdf:
        result["page_count"] = len(pdf.pages)
        result["metadata"] = pdf.metadata or {}

        pages_to_read = pdf.pages[:max_pages] if max_pages else pdf.pages
        all_text_parts: list[str] = []

        for i, page in enumerate(pages_to_read):
            text = page.extract_text() or ""
            all_text_parts.append(f"--- Page {i + 1} ---\n{text}")

            # Extract tables
            tables = page.extract_tables()
            for table in tables:
                if table:
                    result["tables"].append(
                        {"page": i + 1, "data": table},
                    )

        result["text"] = "\n\n".join(all_text_parts)

    # Extract sections if requested
    if sections:
        result["sections"] = _extract_sections(result["text"], sections)

    # Extract references if requested
    if extract_references:
        result["references"] = _extract_references(result["text"])

    return result


def _extract_with_pypdf2(
    filepath: str,
    extract_references: bool,
    max_pages: Optional[int],
    sections: Optional[list[str]],
) -> dict[str, Any]:
    """Extract using PyPDF2 (fallback)."""
    from PyPDF2 import PdfReader

    reader = PdfReader(filepath)
    result: dict[str, Any] = {
        "text": "",
        "metadata": {},
        "page_count": len(reader.pages),
        "tables": [],
    }

    if reader.metadata:
        result["metadata"] = {
            "title": reader.metadata.title or "",
            "author": reader.metadata.author or "",
            "subject": reader.metadata.subject or "",
            "creator": reader.metadata.creator or "",
        }

    pages_to_read = reader.pages[:max_pages] if max_pages else reader.pages
    all_text_parts: list[str] = []

    for i, page in enumerate(pages_to_read):
        text = page.extract_text() or ""
        all_text_parts.append(f"--- Page {i + 1} ---\n{text}")

    result["text"] = "\n\n".join(all_text_parts)

    if sections:
        result["sections"] = _extract_sections(result["text"], sections)

    if extract_references:
        result["references"] = _extract_references(result["text"])

    return result


def _extract_sections(
    full_text: str,
    section_names: list[str],
) -> dict[str, str]:
    """Attempt to extract named sections from paper text."""
    import re

    sections: dict[str, str] = {}

    for name in section_names:
        # Try to find section headers (common patterns)
        patterns = [
            rf"(?:^|\n)\s*(?:\d+\.?\s+)?{re.escape(name)}\s*\n(.*?)(?=\n\s*(?:\d+\.?\s+)?[A-Z][a-z]+|\Z)",
            rf"(?:^|\n)\s*{re.escape(name.upper())}\s*\n(.*?)(?=\n\s*[A-Z][A-Z]+|\Z)",
        ]
        for pattern in patterns:
            match = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)
            if match:
                sections[name] = match.group(1).strip()[
                    :5000
                ]  # Cap at 5000 chars
                break

    return sections


def _extract_references(full_text: str) -> list[str]:
    """Attempt to extract reference entries from paper text."""
    import re

    # Find "References" section
    ref_match = re.search(
        r"(?:^|\n)\s*(?:References|Bibliography|REFERENCES)\s*\n(.*)$",
        full_text,
        re.DOTALL | re.IGNORECASE,
    )
    if not ref_match:
        return []

    ref_text = ref_match.group(1)

    # Split by reference numbering patterns
    refs = re.split(r"\n\s*\[?\d+\]?\s+", ref_text)
    refs = [r.strip() for r in refs if r.strip() and len(r.strip()) > 20]

    return refs[:100]  # Cap at 100 references
