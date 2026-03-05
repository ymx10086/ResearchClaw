"""LLM provider management routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
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
    enabled: bool = False
    extra: dict[str, Any] = {}


class ProviderSettingsUpdate(BaseModel):
    """Partial settings update for a provider."""

    provider_type: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    model_name: str | None = None
    extra: dict[str, Any] | None = None


class EnabledUpdate(BaseModel):
    enabled: bool


def _mask(providers: list[dict]) -> list[dict]:
    """Mask API keys for display."""
    for p in providers:
        key = p.get("api_key") or ""
        if key:
            p["api_key"] = key[:8] + "..." if len(key) > 8 else "***"
    return providers


@router.get("/")
async def list_providers():
    """List configured LLM providers (API keys masked)."""
    try:
        from researchclaw.providers.store import ProviderStore

        store = ProviderStore()
        providers = store.list_providers()
        return {"providers": _mask(providers)}
    except ImportError:
        return {"providers": [], "note": "Provider store not yet initialized"}


@router.post("/")
async def add_provider(config: ProviderConfig):
    """Add a new provider configuration."""
    try:
        from researchclaw.providers.store import ProviderStore

        store = ProviderStore()
        store.save_provider(config.model_dump())
        return {"status": "ok", "provider": config.name}
    except ImportError:
        raise HTTPException(status_code=500, detail="Provider store not available")


@router.post("/{name}/enable")
async def enable_provider(name: str, req: Request):
    """Set this provider as the active one; disable all others."""
    try:
        from researchclaw.providers.store import ProviderStore

        store = ProviderStore()
        store.set_enabled(name)
        return {"status": "ok", "name": name, "enabled": True}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Provider '{name}' not found")
    except ImportError:
        raise HTTPException(status_code=500, detail="Provider store not available")


@router.post("/{name}/disable")
async def disable_provider(name: str, req: Request):
    """Disable this provider without affecting others."""
    try:
        from researchclaw.providers.store import ProviderStore

        store = ProviderStore()
        store.set_disabled(name)
        return {"status": "ok", "name": name, "enabled": False}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Provider '{name}' not found")
    except ImportError:
        raise HTTPException(status_code=500, detail="Provider store not available")


@router.put("/{name}/enabled")
async def set_provider_enabled(name: str, body: EnabledUpdate, req: Request):
    """Enable or disable a provider (kept for backward compat)."""
    try:
        from researchclaw.providers.store import ProviderStore

        store = ProviderStore()
        if body.enabled:
            store.set_enabled(name)
        else:
            store.set_disabled(name)
        return {"status": "ok", "name": name, "enabled": body.enabled}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Provider '{name}' not found")
    except ImportError:
        raise HTTPException(status_code=500, detail="Provider store not available")


@router.put("/{name}")
async def update_provider_settings(name: str, update: ProviderSettingsUpdate):
    """Update settings of an existing provider (partial update)."""
    try:
        from researchclaw.providers.store import ProviderStore

        store = ProviderStore()
        # Only include non-None fields; skip api_key if empty string (keep existing)
        fields = update.model_dump(exclude_none=True)
        if fields.get("api_key") == "":
            fields.pop("api_key")
        updated = store.update_provider_settings(name, fields)
        result = updated.to_dict()
        if result.get("api_key"):
            result["api_key"] = (
                result["api_key"][:8] + "..." if len(result["api_key"]) > 8 else "***"
            )
        return {"status": "ok", "provider": result}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Provider '{name}' not found")
    except ImportError:
        raise HTTPException(status_code=500, detail="Provider store not available")


@router.post("/{name}/apply")
async def apply_provider(name: str, req: Request):
    """Apply the provider to the running agent (hot-reload).

    Reads the full config (with real API key) from store and restarts the agent.
    """
    try:
        from researchclaw.providers.store import ProviderStore

        store = ProviderStore()
        provider = store.get_provider(name)
        if provider is None:
            raise HTTPException(
                status_code=404, detail=f"Provider '{name}' not found"
            )

        runner = getattr(req.app.state, "runner", None)
        if runner is None:
            raise HTTPException(status_code=503, detail="Agent runner not available")

        model_config = {
            "provider": provider.provider_type,
            "model_name": provider.model_name or "",
            "api_key": provider.api_key or "",
            "base_url": provider.base_url or "",
        }
        await runner.apply_provider(model_config)
        # Also set enabled flag in store
        store.set_enabled(name)
        return {"status": "ok", "applied": name}
    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(status_code=500, detail="Provider store not available")
    except Exception as e:
        logger.exception("Failed to apply provider")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{name}")
async def remove_provider(name: str):
    """Remove a provider."""
    try:
        from researchclaw.providers.store import ProviderStore

        store = ProviderStore()
        store.remove_provider(name)
        return {"status": "deleted", "provider": name}
    except ImportError:
        raise HTTPException(status_code=500, detail="Provider store not available")
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Provider {name} not found")


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

