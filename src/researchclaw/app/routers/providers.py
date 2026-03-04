"""LLM provider management routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class ProviderConfig(BaseModel):
    """Provider configuration schema."""

    name: str
    provider_type: str  # openai | anthropic | ollama | dashscope
    api_key: str | None = None
    base_url: str | None = None
    model_name: str | None = None
    extra: dict[str, Any] = {}


@router.get("/")
async def list_providers(req):
    """List configured LLM providers."""
    try:
        from researchclaw.providers.store import ProviderStore

        store = ProviderStore()
        providers = store.list_providers()
        # Mask API keys
        for p in providers:
            if p.get("api_key"):
                p["api_key"] = (
                    p["api_key"][:8] + "..."
                    if len(p["api_key"]) > 8
                    else "***"
                )
        return {"providers": providers}
    except ImportError:
        return {"providers": [], "note": "Provider store not yet initialized"}


@router.post("/")
async def add_provider(config: ProviderConfig):
    """Add or update a provider configuration."""
    try:
        from researchclaw.providers.store import ProviderStore

        store = ProviderStore()
        store.save_provider(config.model_dump())
        return {"status": "ok", "provider": config.name}
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Provider store not available",
        )


@router.delete("/{name}")
async def remove_provider(name: str):
    """Remove a provider."""
    try:
        from researchclaw.providers.store import ProviderStore

        store = ProviderStore()
        store.remove_provider(name)
        return {"status": "deleted", "provider": name}
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Provider store not available",
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Provider {name} not found",
        )


@router.get("/models")
async def list_available_models():
    """List available models across all providers."""
    try:
        from researchclaw.providers.registry import ModelRegistry

        registry = ModelRegistry()
        return {"models": registry.list_models()}
    except ImportError:
        return {
            "models": [
                {"name": "gpt-4o", "provider": "openai"},
                {"name": "gpt-4o-mini", "provider": "openai"},
                {"name": "claude-sonnet-4-20250514", "provider": "anthropic"},
                {"name": "deepseek-chat", "provider": "deepseek"},
                {"name": "qwen-max", "provider": "dashscope"},
            ],
            "note": "Default model list (provider store not initialized)",
        }
