"""Request/response schemas for config API endpoints.

Provides Pydantic models used by the config router for structured
request/response validation.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ActiveHoursConfig(BaseModel):
    """Active hours window for heartbeat scheduling."""

    start: str = "08:00"
    end: str = "22:00"


class HeartbeatBody(BaseModel):
    """Request body for PUT /config/heartbeat."""

    enabled: bool = False
    every: str = "6h"
    target: str = "main"
    active_hours: Optional[ActiveHoursConfig] = Field(
        default=None,
        alias="activeHours",
    )

    model_config = {"populate_by_name": True, "extra": "allow"}


class ModelConfigBody(BaseModel):
    """Request body for PUT /config/model — research-specific extension."""

    provider: str = "openai_chat"
    model_name: str = "gpt-4o"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None

    model_config = {"extra": "allow"}


class ResearchConfigBody(BaseModel):
    """Request body for PUT /config/research — ResearchClaw-specific settings."""

    default_search_engine: str = "arxiv"
    max_papers_per_search: int = 10
    enable_citation_tracking: bool = True
    bibtex_style: str = "plain"
    digest_schedule: Optional[str] = None

    model_config = {"extra": "allow"}
