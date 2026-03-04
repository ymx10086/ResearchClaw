"""Paper digest cron – periodically checks for new papers in tracked areas."""

from __future__ import annotations

import logging
from pathlib import Path

from researchclaw.constant import WORKING_DIR

logger = logging.getLogger(__name__)


async def paper_digest():
    """Check for new papers in user's research areas.

    Reads research areas from the user's RESEARCH_AREAS.md profile,
    searches ArXiv for recent papers, and stores digest summaries.
    """
    import json

    profile_path = Path(WORKING_DIR) / "md_files" / "RESEARCH_AREAS.md"
    digest_path = Path(WORKING_DIR) / "digests"
    digest_path.mkdir(parents=True, exist_ok=True)

    if not profile_path.exists():
        logger.debug("No RESEARCH_AREAS.md found, skipping paper digest")
        return

    # Read research areas
    content = profile_path.read_text(encoding="utf-8")
    areas = []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("- ") or line.startswith("* "):
            areas.append(line[2:].strip())

    if not areas:
        logger.debug("No research areas defined, skipping digest")
        return

    # Search for recent papers in each area
    try:
        from researchclaw.agents.tools.arxiv_search import arxiv_search

        results = []
        for area in areas[:5]:  # Limit to 5 areas
            try:
                papers = arxiv_search(query=area, max_results=5)
                if isinstance(papers, str):
                    papers = json.loads(papers)
                results.extend(papers if isinstance(papers, list) else [])
            except Exception:
                logger.debug("Failed to search for area: %s", area)

        if results:
            import time

            digest_file = digest_path / f"digest_{int(time.time())}.json"
            digest_file.write_text(
                json.dumps(
                    {
                        "timestamp": time.time(),
                        "areas": areas,
                        "papers": results,
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            logger.info("Paper digest saved with %d papers", len(results))

    except ImportError:
        logger.debug("arxiv package not available, skipping digest")
