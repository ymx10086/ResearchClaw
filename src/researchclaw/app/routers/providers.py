"""LLM provider management routes."""

from __future__ import annotations

import logging
from typing import Any
from urllib.error import URLError
from urllib.request import Request as UrlRequest, urlopen

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


class ProviderConfig(BaseModel):
    """Provider configuration schema."""

    name: str
    provider_type: str  # openai | anthropic | ollama | dashscope
    api_key: str | None = None
    base_url: str | None = None
    model_name: str | None = None
    model_names: list[str] = Field(default_factory=list)
    enabled: bool = False
    extra: dict[str, Any] = Field(default_factory=dict)


class ProviderSettingsUpdate(BaseModel):
    """Partial settings update for a provider."""

    provider_type: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    model_name: str | None = None
    model_names: list[str] | None = None
    extra: dict[str, Any] | None = None


class ProviderTestResponse(BaseModel):
    success: bool
    message: str


class DiscoverModelsResponse(BaseModel):
    success: bool
    message: str
    models: list[dict[str, str]] = Field(default_factory=list)


def _provider_store_unavailable() -> HTTPException:
    return HTTPException(
        status_code=500,
        detail="Provider store not available",
    )


def _get_provider_store():
    try:
        from researchclaw.providers.store import ProviderStore
    except ImportError as exc:  # pragma: no cover - import guard
        raise _provider_store_unavailable() from exc
    return ProviderStore()


def _mask_api_key(value: str | None) -> str | None:
    key = (value or "").strip()
    if not key:
        return None
    return key[:8] + "..." if len(key) > 8 else "***"


def _masked_provider_dict(provider: dict[str, Any]) -> dict[str, Any]:
    result = dict(provider)
    masked = _mask_api_key(result.get("api_key"))
    if masked:
        result["api_key"] = masked
    return result


def _mask(providers: list[dict]) -> list[dict]:
    """Mask API keys for display."""
    return [_masked_provider_dict(provider) for provider in providers]


def _get_provider_or_404(store: Any, name: str):
    provider = store.get_provider(name)
    if provider is None:
        raise HTTPException(
            status_code=404,
            detail=f"Provider '{name}' not found",
        )
    return provider


@router.get("")
async def list_providers():
    """List configured LLM providers (API keys masked)."""
    try:
        store = _get_provider_store()
        providers = store.list_providers()
        return {"providers": _mask(providers)}
    except HTTPException:
        return {"providers": [], "note": "Provider store not yet initialized"}
    except Exception:
        return {"providers": [], "note": "Provider store not yet initialized"}


@router.post("")
async def add_provider(config: ProviderConfig):
    """Add a new provider configuration."""
    store = _get_provider_store()
    store.save_provider(config.model_dump())
    return {"status": "ok", "provider": config.name}


@router.post("/{name:path}/enable")
async def enable_provider(name: str, req: Request):
    """Set this provider as the active one; disable all others."""
    del req
    store = _get_provider_store()
    try:
        store.set_enabled(name)
        return {"status": "ok", "name": name, "enabled": True}
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Provider '{name}' not found",
        )


@router.post("/{name:path}/disable")
async def disable_provider(name: str, req: Request):
    """Disable this provider without affecting others."""
    del req
    store = _get_provider_store()
    try:
        store.set_disabled(name)
        return {"status": "ok", "name": name, "enabled": False}
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Provider '{name}' not found",
        )


@router.post("/{name:path}/settings")
async def update_provider_settings(name: str, update: ProviderSettingsUpdate):
    """Update settings of an existing provider (partial update)."""
    store = _get_provider_store()
    try:
        fields = update.model_dump(exclude_none=True)
        if fields.get("api_key") == "":
            fields.pop("api_key")
        updated = store.update_provider_settings(name, fields)
        result = _masked_provider_dict(updated.to_dict())
        return {"status": "ok", "provider": result}
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Provider '{name}' not found",
        )


@router.put("/{name:path}")
async def update_provider_put(name: str, update: ProviderSettingsUpdate):
    """Update settings via PUT (alias for POST /{name}/settings)."""
    return await update_provider_settings(name, update)


@router.post("/{name:path}/apply")
async def apply_provider(name: str, req: Request):
    """Apply the provider to the running agent (hot-reload).

    Reads the full config (with real API key) from store and restarts the agent.
    """
    store = _get_provider_store()
    provider = _get_provider_or_404(store, name)

    runner = getattr(req.app.state, "runner", None)
    if runner is None:
        raise HTTPException(
            status_code=503,
            detail="Agent runner not available",
        )

    model_config = {
        "provider": provider.provider_type,
        "model_name": provider.model_name or "",
        "api_key": provider.api_key or "",
        "base_url": provider.base_url or "",
    }
    try:
        await runner.apply_provider(model_config)
        # Also set enabled flag in store
        store.set_enabled(name)
        return {"status": "ok", "applied": name}
    except Exception as e:
        logger.exception("Failed to apply provider")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{name:path}")
async def remove_provider(name: str):
    """Remove a provider."""
    store = _get_provider_store()
    try:
        store.remove_provider(name)
        return {"status": "deleted", "provider": name}
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
                {"name": "gpt-5", "provider": "openai"},
                {"name": "gpt-5-mini", "provider": "openai"},
                {"name": "gpt-4.1", "provider": "openai"},
                {"name": "claude-sonnet-4-20250514", "provider": "anthropic"},
                {"name": "deepseek-chat", "provider": "deepseek"},
                {"name": "qwen-max", "provider": "dashscope"},
                {"name": "llama3.2", "provider": "ollama"},
            ],
            "note": "Default model list (provider store not initialized)",
        }


def _safe_join_url(base_url: str, suffix: str) -> str:
    value = (base_url or "").rstrip("/")
    return f"{value}{suffix}"


@router.post("/{name:path}/test", response_model=ProviderTestResponse)
async def test_provider(name: str):
    """Lightweight provider connectivity/config test."""
    store = _get_provider_store()
    provider = _get_provider_or_404(store, name)

    ptype = (provider.provider_type or "").lower()
    base_url = provider.base_url or ""

    if ptype != "ollama" and not provider.api_key:
        return ProviderTestResponse(
            success=False,
            message="API key is empty",
        )

    # Quick network probe when base_url is available.
    if base_url:
        probe_url = (
            _safe_join_url(base_url, "/models")
            if ptype != "ollama"
            else _safe_join_url(base_url.replace("/v1", ""), "/api/tags")
        )
        req = UrlRequest(probe_url, method="GET")
        if provider.api_key and ptype != "ollama":
            req.add_header("Authorization", f"Bearer {provider.api_key}")
        try:
            with urlopen(
                req,
                timeout=6,
            ) as resp:  # nosec - user config URL
                if 200 <= resp.status < 500:
                    return ProviderTestResponse(
                        success=True,
                        message=f"Connected ({resp.status})",
                    )
        except URLError as exc:
            return ProviderTestResponse(
                success=False,
                message=f"Connection failed: {exc}",
            )
        except Exception as exc:
            return ProviderTestResponse(
                success=False,
                message=f"Probe error: {exc}",
            )

    return ProviderTestResponse(
        success=True,
        message="Configuration looks valid",
    )


@router.post(
    "/{name:path}/discover-models",
    response_model=DiscoverModelsResponse,
)
async def discover_models(name: str):
    """Discover candidate models for a provider."""
    store = _get_provider_store()
    provider = _get_provider_or_404(store, name)

    ptype = (provider.provider_type or "").lower()
    if ptype == "ollama":
        try:
            from researchclaw.providers.ollama_manager import (
                OllamaModelManager,
            )
            from researchclaw.providers.store import get_ollama_host

            models = [
                {"name": m.name, "provider": "ollama"}
                for m in OllamaModelManager.list_models(
                    host=get_ollama_host(),
                )
            ]
            return DiscoverModelsResponse(
                success=True,
                message=f"Discovered {len(models)} models from Ollama",
                models=models,
            )
        except Exception as exc:
            return DiscoverModelsResponse(
                success=False,
                message=f"Ollama discovery failed: {exc}",
                models=[],
            )

    # Fallback to static registry list for remote providers.
    from researchclaw.providers.registry import ModelRegistry

    models = [
        item
        for item in ModelRegistry().list_models()
        if str(item.get("provider", "")).lower() == ptype
    ]
    return DiscoverModelsResponse(
        success=True,
        message=f"Returned {len(models)} built-in model suggestions",
        models=models,
    )
