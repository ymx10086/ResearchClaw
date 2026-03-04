"""Paper management API routes – search, download, library."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from researchclaw.constant import (
    WORKING_DIR,
    PAPERS_DIR,
    REFERENCES_DIR,
    DEFAULT_BIB_FILE,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class PaperSearchRequest(BaseModel):
    """Paper search query."""

    query: str
    source: str = "arxiv"  # arxiv | semantic_scholar
    max_results: int = 10
    year_from: int | None = None
    year_to: int | None = None
    categories: list[str] | None = None


class PaperDownloadRequest(BaseModel):
    """Request to download a paper PDF."""

    arxiv_id: str | None = None
    url: str | None = None
    filename: str | None = None


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


@router.post("/search")
async def search_papers(request: PaperSearchRequest):
    """Search papers from external sources."""
    if request.source == "arxiv":
        try:
            from researchclaw.agents.tools.arxiv_search import arxiv_search

            results = arxiv_search(
                query=request.query,
                max_results=request.max_results,
                categories=request.categories,
            )
            return {"source": "arxiv", "results": results}
        except Exception as e:
            logger.exception("ArXiv search failed")
            raise HTTPException(status_code=500, detail=str(e))

    elif request.source == "semantic_scholar":
        try:
            from researchclaw.agents.tools.semantic_scholar import (
                semantic_scholar_search,
            )

            results = semantic_scholar_search(
                query=request.query,
                max_results=request.max_results,
                year_range=f"{request.year_from}-{request.year_to}"
                if request.year_from
                else "",
            )
            return {"source": "semantic_scholar", "results": results}
        except Exception as e:
            logger.exception("Semantic Scholar search failed")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown source: {request.source}",
        )


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


@router.post("/download")
async def download_paper(request: PaperDownloadRequest):
    """Download a paper PDF to the papers directory."""
    if not request.arxiv_id and not request.url:
        raise HTTPException(status_code=400, detail="Provide arxiv_id or url")

    try:
        from researchclaw.agents.tools.arxiv_search import arxiv_download

        result = arxiv_download(
            arxiv_id=request.arxiv_id or "",
            output_dir=str(Path(WORKING_DIR) / PAPERS_DIR),
        )
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.exception("Paper download failed")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Library
# ---------------------------------------------------------------------------


@router.get("/library")
async def list_papers():
    """List papers in the local library."""
    papers_path = Path(WORKING_DIR) / PAPERS_DIR
    if not papers_path.exists():
        return {"papers": []}

    papers = []
    for f in sorted(papers_path.iterdir()):
        if f.suffix.lower() == ".pdf":
            papers.append(
                {
                    "filename": f.name,
                    "path": str(f),
                    "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                },
            )
    return {"papers": papers}


@router.delete("/library/{filename}")
async def delete_paper(filename: str):
    """Delete a paper from the library."""
    paper_path = Path(WORKING_DIR) / PAPERS_DIR / filename
    if not paper_path.exists():
        raise HTTPException(status_code=404, detail="Paper not found")
    paper_path.unlink()
    return {"status": "deleted", "filename": filename}


# ---------------------------------------------------------------------------
# References (BibTeX)
# ---------------------------------------------------------------------------


@router.get("/references")
async def list_references():
    """List references in the BibTeX library."""
    bib_path = Path(WORKING_DIR) / REFERENCES_DIR / DEFAULT_BIB_FILE
    if not bib_path.exists():
        return {"references": [], "total": 0}

    try:
        from researchclaw.agents.tools.bibtex_manager import bibtex_search

        results = bibtex_search(query="", bib_file=str(bib_path))
        return {
            "references": results,
            "total": len(results) if isinstance(results, list) else 0,
        }
    except Exception as e:
        logger.exception("Failed to list references")
        return {"references": [], "total": 0, "error": str(e)}


@router.post("/references/add")
async def add_reference(entry: dict[str, Any]):
    """Add a reference to the BibTeX library."""
    try:
        from researchclaw.agents.tools.bibtex_manager import bibtex_add_entry

        bib_path = str(Path(WORKING_DIR) / REFERENCES_DIR / DEFAULT_BIB_FILE)
        result = bibtex_add_entry(
            entry_type=entry.get("type", "article"),
            cite_key=entry.get("cite_key", ""),
            title=entry.get("title", ""),
            authors=entry.get("authors", ""),
            year=entry.get("year", ""),
            bib_file=bib_path,
            journal=entry.get("journal", ""),
            booktitle=entry.get("booktitle", ""),
            doi=entry.get("doi", ""),
            url=entry.get("url", ""),
            abstract=entry.get("abstract", ""),
        )
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.exception("Failed to add reference")
        raise HTTPException(status_code=500, detail=str(e))
