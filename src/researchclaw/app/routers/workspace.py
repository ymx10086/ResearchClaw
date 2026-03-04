"""Workspace routes for profile and directory introspection."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from researchclaw.constant import (
    EXAMPLES_DIR,
    EXPERIMENTS_DIR,
    MD_FILES_DIR,
    PAPERS_DIR,
    REFERENCES_DIR,
    WORKING_DIR,
)

router = APIRouter()


@router.get("")
async def workspace_info():
    wd = Path(WORKING_DIR)
    return {
        "working_dir": str(wd),
        "exists": wd.exists(),
        "directories": {
            "papers": str(wd / PAPERS_DIR),
            "references": str(wd / REFERENCES_DIR),
            "experiments": str(wd / EXPERIMENTS_DIR),
            "md_files": str(wd / MD_FILES_DIR),
            "examples": str(wd / EXAMPLES_DIR),
        },
    }


@router.get("/profile")
async def profile_md():
    profile_path = Path(WORKING_DIR) / "PROFILE.md"
    if not profile_path.exists():
        return {"exists": False, "content": ""}
    return {
        "exists": True,
        "path": str(profile_path),
        "content": profile_path.read_text(encoding="utf-8"),
    }
