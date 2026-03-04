"""BibTeX reference management tool.

Provides functions to parse, search, add, and export BibTeX references.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

from ...constant import DEFAULT_BIB_FILE, REFERENCES_DIR

logger = logging.getLogger(__name__)


def _ensure_refs_dir() -> Path:
    """Ensure the references directory exists."""
    refs_dir = Path(REFERENCES_DIR)
    refs_dir.mkdir(parents=True, exist_ok=True)
    return refs_dir


def _get_bib_path(bib_file: Optional[str] = None) -> Path:
    """Get the path to the BibTeX file."""
    refs_dir = _ensure_refs_dir()
    return refs_dir / (bib_file or DEFAULT_BIB_FILE)


def bibtex_add_entry(
    entry_type: str,
    cite_key: str,
    title: str,
    authors: list[str],
    year: int,
    bib_file: Optional[str] = None,
    **fields: str,
) -> dict[str, str]:
    """Add a BibTeX entry to the reference library.

    Parameters
    ----------
    entry_type:
        BibTeX entry type (e.g. ``"article"``, ``"inproceedings"``,
        ``"book"``, ``"misc"``).
    cite_key:
        Citation key (e.g. ``"vaswani2017attention"``).
    title:
        Paper title.
    authors:
        List of author names.
    year:
        Publication year.
    bib_file:
        BibTeX filename (default: ``references.bib``).
    **fields:
        Additional BibTeX fields (e.g. ``journal``, ``booktitle``,
        ``volume``, ``pages``, ``doi``, ``url``, ``abstract``).

    Returns
    -------
    dict
        Result with ``status`` and generated ``bibtex`` string.
    """
    try:
        # Build BibTeX entry manually for reliability
        author_str = " and ".join(authors)

        bib_lines = [f"@{entry_type}{{{cite_key},"]
        bib_lines.append(f"  title = {{{title}}},")
        bib_lines.append(f"  author = {{{author_str}}},")
        bib_lines.append(f"  year = {{{year}}},")

        for key, value in fields.items():
            if value:
                bib_lines.append(f"  {key} = {{{value}}},")

        bib_lines.append("}")
        entry_str = "\n".join(bib_lines)

        # Append to file
        bib_path = _get_bib_path(bib_file)
        with open(bib_path, "a", encoding="utf-8") as f:
            f.write("\n" + entry_str + "\n")

        return {
            "status": "success",
            "cite_key": cite_key,
            "bibtex": entry_str,
            "file": str(bib_path),
        }

    except Exception as e:
        logger.exception("Failed to add BibTeX entry")
        return {"status": "error", "error": str(e)}


def bibtex_search(
    query: str,
    bib_file: Optional[str] = None,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    """Search the local BibTeX library.

    Parameters
    ----------
    query:
        Search query (matches against title, author, year, cite_key).
    bib_file:
        BibTeX filename to search in (default: all ``.bib`` files).
    max_results:
        Maximum results to return.

    Returns
    -------
    list[dict]
        Matching BibTeX entries with parsed fields.
    """
    try:
        refs_dir = _ensure_refs_dir()

        if bib_file:
            bib_files = [refs_dir / bib_file]
        else:
            bib_files = list(refs_dir.glob("*.bib"))

        results: list[dict[str, Any]] = []
        query_lower = query.lower()

        for bf in bib_files:
            if not bf.exists():
                continue

            entries = _parse_bib_file(bf)
            for entry in entries:
                # Search in title, authors, year, cite_key
                searchable = " ".join(
                    [
                        entry.get("title", ""),
                        entry.get("author", ""),
                        str(entry.get("year", "")),
                        entry.get("cite_key", ""),
                    ],
                ).lower()

                if query_lower in searchable:
                    entry["source_file"] = bf.name
                    results.append(entry)

                    if len(results) >= max_results:
                        return results

        return results

    except Exception as e:
        logger.exception("BibTeX search failed")
        return [{"error": f"Search failed: {e}"}]


def bibtex_export(
    cite_keys: Optional[list[str]] = None,
    bib_file: Optional[str] = None,
    output_format: str = "bibtex",
) -> str:
    """Export references from the library.

    Parameters
    ----------
    cite_keys:
        Optional list of cite keys to export. If None, exports all.
    bib_file:
        Source BibTeX file. If None, searches all files.
    output_format:
        Output format: ``"bibtex"`` (default) or ``"plain"`` (human readable).

    Returns
    -------
    str
        Formatted reference entries.
    """
    try:
        refs_dir = _ensure_refs_dir()

        if bib_file:
            bib_files = [refs_dir / bib_file]
        else:
            bib_files = list(refs_dir.glob("*.bib"))

        all_entries: list[dict[str, Any]] = []
        for bf in bib_files:
            if bf.exists():
                all_entries.extend(_parse_bib_file(bf))

        if cite_keys:
            all_entries = [
                e for e in all_entries if e.get("cite_key") in cite_keys
            ]

        if output_format == "plain":
            lines = []
            for entry in all_entries:
                authors = entry.get("author", "Unknown")
                title = entry.get("title", "Untitled")
                year = entry.get("year", "n.d.")
                venue = entry.get("journal") or entry.get("booktitle", "")
                line = f"[{entry.get('cite_key', '?')}] {authors}. ({year}). {title}."
                if venue:
                    line += f" {venue}."
                lines.append(line)
            return "\n\n".join(lines)

        else:  # bibtex
            # Return raw BibTeX
            parts = []
            for entry in all_entries:
                parts.append(entry.get("raw", str(entry)))
            return "\n\n".join(parts)

    except Exception as e:
        logger.exception("BibTeX export failed")
        return f"Export failed: {e}"


def _parse_bib_file(path: Path) -> list[dict[str, Any]]:
    """Parse a BibTeX file into a list of entry dicts.

    Uses a simple regex-based parser as a fallback when bibtexparser
    is not available.
    """
    import re

    content = path.read_text(encoding="utf-8", errors="replace")
    entries: list[dict[str, Any]] = []

    # Match BibTeX entries
    pattern = r"@(\w+)\{([^,]+),\s*(.*?)\n\}"
    for match in re.finditer(pattern, content, re.DOTALL):
        entry_type = match.group(1).lower()
        cite_key = match.group(2).strip()
        body = match.group(3)

        entry: dict[str, Any] = {
            "entry_type": entry_type,
            "cite_key": cite_key,
            "raw": match.group(0),
        }

        # Parse individual fields
        field_pattern = r"(\w+)\s*=\s*\{([^}]*)\}"
        for field_match in re.finditer(field_pattern, body):
            field_name = field_match.group(1).lower()
            field_value = field_match.group(2).strip()
            entry[field_name] = field_value

        entries.append(entry)

    return entries


def bibtex_from_paper_info(paper: dict[str, Any]) -> str:
    """Generate a BibTeX entry from a paper metadata dict.

    Parameters
    ----------
    paper:
        Paper metadata dict (as returned by search tools).

    Returns
    -------
    str
        BibTeX entry string.
    """
    authors = paper.get("authors", [])
    if not authors:
        authors = ["Unknown"]

    year = paper.get("year", "")
    title = paper.get("title", "Untitled")

    # Generate cite key: first_author_last_name + year + first_word_of_title
    first_author = authors[0].split()[-1].lower() if authors else "unknown"
    first_word = title.split()[0].lower() if title else "untitled"
    cite_key = f"{first_author}{year}{first_word}"

    # Determine entry type
    venue = paper.get("venue", "")
    arxiv_id = paper.get("arxiv_id", "")

    if arxiv_id and not venue:
        entry_type = "misc"
    elif "conference" in venue.lower() or "proceedings" in venue.lower():
        entry_type = "inproceedings"
    else:
        entry_type = "article"

    lines = [f"@{entry_type}{{{cite_key},"]
    lines.append(f"  title = {{{title}}},")
    lines.append(f"  author = {{{' and '.join(authors)}}},")
    if year:
        lines.append(f"  year = {{{year}}},")
    if venue:
        field = "booktitle" if entry_type == "inproceedings" else "journal"
        lines.append(f"  {field} = {{{venue}}},")
    if arxiv_id:
        lines.append(f"  eprint = {{{arxiv_id}}},")
        lines.append("  archiveprefix = {arXiv},")
    doi = paper.get("doi", "")
    if doi:
        lines.append(f"  doi = {{{doi}}},")
    url = paper.get("url", "") or paper.get("pdf_url", "")
    if url:
        lines.append(f"  url = {{{url}}},")
    lines.append("}")

    return "\n".join(lines)
