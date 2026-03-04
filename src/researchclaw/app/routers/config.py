"""Configuration API routes."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from researchclaw.constant import WORKING_DIR

logger = logging.getLogger(__name__)

router = APIRouter()


class ConfigUpdateRequest(BaseModel):
    """Configuration update request."""

    key: str
    value: Any


@router.get("/")
async def get_config():
    """Get current configuration."""
    config_path = Path(WORKING_DIR) / "config.json"
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


@router.put("/")
async def update_config(updates: dict[str, Any]):
    """Update configuration values."""
    config_path = Path(WORKING_DIR) / "config.json"
    config = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    config.update(updates)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {"status": "ok", "config": config}


@router.get("/working-dir")
async def get_working_dir():
    """Get current working directory info."""
    wd = Path(WORKING_DIR)
    return {
        "path": str(wd),
        "exists": wd.exists(),
        "papers_dir": str(wd / "papers"),
        "references_dir": str(wd / "references"),
        "experiments_dir": str(wd / "experiments"),
    }


@router.get("/model")
async def get_model_config():
    """Get current model configuration."""
    config_path = Path(WORKING_DIR) / "config.json"
    if not config_path.exists():
        return {"model": None}
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        return {
            "model": config.get("model_name"),
            "provider": config.get("provider"),
            "api_key_set": bool(config.get("api_key")),
        }
    except Exception:
        return {"model": None}
