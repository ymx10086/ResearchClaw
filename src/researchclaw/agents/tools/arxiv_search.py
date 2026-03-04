"""ArXiv paper search and download tool.

Provides functions to search ArXiv for papers, retrieve metadata, and
download PDFs for offline reading.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

from ...constant import PAPERS_DIR

logger = logging.getLogger(__name__)


def arxiv_search(
    query: str,
    max_results: int = 10,
    sort_by: str = "relevance",
    categories: Optional[list[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Search ArXiv for academic papers.

    Parameters
    ----------
    query:
        Search query string. Supports ArXiv query syntax
        (e.g., ``"ti:transformer AND cat:cs.CL"``).
    max_results:
        Maximum number of results to return (default 10, max 50).
    sort_by:
        Sort order: ``"relevance"`` (default), ``"lastUpdatedDate"``,
        or ``"submittedDate"``.
    categories:
        Optional list of ArXiv categories to filter (e.g., ``["cs.CL", "cs.AI"]``).
    date_from:
        Optional start date in ``YYYY-MM-DD`` format.
    date_to:
        Optional end date in ``YYYY-MM-DD`` format.

    Returns
    -------
    list[dict]
        List of paper metadata dicts with keys: ``title``, ``authors``,
        ``abstract``, ``arxiv_id``, ``pdf_url``, ``published``,
        ``updated``, ``categories``, ``doi``.
    """
    try:
        import arxiv

        max_results = min(max_results, 50)

        sort_mapping = {
            "relevance": arxiv.SortCriterion.Relevance,
            "lastUpdatedDate": arxiv.SortCriterion.LastUpdatedDate,
            "submittedDate": arxiv.SortCriterion.SubmittedDate,
        }
        sort_criterion = sort_mapping.get(
            sort_by,
            arxiv.SortCriterion.Relevance,
        )

        # Build the query with optional category filters
        full_query = query
        if categories:
            cat_filter = " OR ".join(f"cat:{c}" for c in categories)
            full_query = f"({query}) AND ({cat_filter})"

        client = arxiv.Client()
        search = arxiv.Search(
            query=full_query,
            max_results=max_results,
            sort_by=sort_criterion,
        )

        results = []
        for paper in client.results(search):
            # Apply date filtering if specified
            if date_from and paper.published.strftime("%Y-%m-%d") < date_from:
                continue
            if date_to and paper.published.strftime("%Y-%m-%d") > date_to:
                continue

            results.append(
                {
                    "title": paper.title,
                    "authors": [a.name for a in paper.authors],
                    "abstract": paper.summary,
                    "arxiv_id": paper.entry_id.split("/")[-1],
                    "pdf_url": paper.pdf_url,
                    "published": paper.published.isoformat(),
                    "updated": paper.updated.isoformat(),
                    "categories": paper.categories,
                    "doi": paper.doi or "",
                    "comment": paper.comment or "",
                    "primary_category": paper.primary_category,
                },
            )

        return results

    except ImportError:
        return [
            {"error": "arxiv package not installed. Run: pip install arxiv"},
        ]
    except Exception as e:
        logger.exception("ArXiv search failed")
        return [{"error": f"ArXiv search failed: {e}"}]


def arxiv_download(
    arxiv_id: str,
    output_dir: Optional[str] = None,
) -> dict[str, str]:
    """Download a paper PDF from ArXiv.

    Parameters
    ----------
    arxiv_id:
        The ArXiv paper ID (e.g., ``"2301.07041"``).
    output_dir:
        Directory to save the PDF. Defaults to ``~/.researchclaw/papers/``.

    Returns
    -------
    dict
        Result with ``path`` (file path) or ``error`` message.
    """
    try:
        import arxiv

        output_dir = output_dir or PAPERS_DIR
        os.makedirs(output_dir, exist_ok=True)

        client = arxiv.Client()
        search = arxiv.Search(id_list=[arxiv_id])
        paper = next(client.results(search))

        # Download PDF
        filename = f"{arxiv_id.replace('/', '_')}.pdf"
        filepath = Path(output_dir) / filename
        paper.download_pdf(dirpath=output_dir, filename=filename)

        return {
            "path": str(filepath),
            "title": paper.title,
            "arxiv_id": arxiv_id,
        }

    except ImportError:
        return {"error": "arxiv package not installed. Run: pip install arxiv"}
    except StopIteration:
        return {"error": f"Paper not found: {arxiv_id}"}
    except Exception as e:
        logger.exception("ArXiv download failed")
        return {"error": f"Download failed: {e}"}


def arxiv_get_paper(arxiv_id: str) -> dict[str, Any]:
    """Get detailed metadata for a specific ArXiv paper.

    Parameters
    ----------
    arxiv_id:
        The ArXiv paper ID.

    Returns
    -------
    dict
        Full paper metadata including abstract, authors, dates, etc.
    """
    try:
        import arxiv

        client = arxiv.Client()
        search = arxiv.Search(id_list=[arxiv_id])
        paper = next(client.results(search))

        return {
            "title": paper.title,
            "authors": [a.name for a in paper.authors],
            "abstract": paper.summary,
            "arxiv_id": arxiv_id,
            "pdf_url": paper.pdf_url,
            "published": paper.published.isoformat(),
            "updated": paper.updated.isoformat(),
            "categories": paper.categories,
            "primary_category": paper.primary_category,
            "doi": paper.doi or "",
            "comment": paper.comment or "",
            "journal_ref": paper.journal_ref or "",
            "links": [link.href for link in paper.links],
        }

    except ImportError:
        return {"error": "arxiv package not installed. Run: pip install arxiv"}
    except StopIteration:
        return {"error": f"Paper not found: {arxiv_id}"}
    except Exception as e:
        return {"error": f"Failed to get paper info: {e}"}
