"""Persistent store for model providers with legacy migration support."""

from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlsplit, urlunsplit

from .models import ProviderConfig

logger = logging.getLogger(__name__)

_BOOTSTRAP_WORKING_DIR = (
    Path(os.environ.get("RESEARCHCLAW_WORKING_DIR", "~/.researchclaw"))
    .expanduser()
    .resolve()
)
_BOOTSTRAP_SECRET_DIR = (
    Path(
        os.environ.get(
            "RESEARCHCLAW_SECRET_DIR",
            f"{_BOOTSTRAP_WORKING_DIR}.secret",
        ),
    )
    .expanduser()
    .resolve()
)

_PROVIDERS_JSON = _BOOTSTRAP_SECRET_DIR / "providers.json"
_LEGACY_PROVIDERS_JSON_CANDIDATES = (
    Path(__file__).resolve().parent / "providers.json",
    _BOOTSTRAP_WORKING_DIR / "providers.json",
)

_ALLOWED_PROVIDER_TYPES = {
    "openai",
    "anthropic",
    "gemini",
    "ollama",
    "dashscope",
    "deepseek",
    "minimax",
    "other",
    "custom",
}


def _same_path(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve()
    except OSError:
        return False


def _chmod_best_effort(path: Path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def _prepare_secret_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _chmod_best_effort(path.parent, 0o700)


def _resolve_store_path(
    file_path: str | None,
    *,
    default_path: Path,
) -> Path:
    return (
        Path(file_path).expanduser().resolve() if file_path else default_path
    )


def _ensure_store_parent(path: Path, *, secure: bool) -> None:
    if secure:
        _prepare_secret_parent(path)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)


def _load_store_json(path: Path) -> Any:
    if path.exists() and not path.is_file():
        logger.error(
            "providers.json path exists but is not a regular file: %s",
            path,
        )
        return None
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return None


def _migrate_legacy_providers_json(path: Path) -> None:
    """Copy old providers.json into secret dir once (best effort)."""
    if path.is_file():
        return
    if path.exists() and not path.is_file():
        logger.error(
            "providers.json path exists but is not a regular file: %s",
            path,
        )
        return

    for legacy in _LEGACY_PROVIDERS_JSON_CANDIDATES:
        if not legacy.is_file() or _same_path(legacy, path):
            continue
        try:
            _prepare_secret_parent(path)
            shutil.copy2(legacy, path)
            _chmod_best_effort(path, 0o600)
            return
        except OSError as exc:
            logger.warning(
                "Failed to migrate legacy providers.json from %s: %s",
                legacy,
                exc,
            )


def get_providers_json_path() -> Path:
    """Return canonical providers.json path under SECRET_DIR."""
    return _PROVIDERS_JSON


def _normalize_ollama_base_url(base_url: str) -> str:
    value = (base_url or "").strip()
    if not value:
        return value

    try:
        parts = urlsplit(value)
    except ValueError:
        return value

    path = parts.path or ""
    if path in ("", "/"):
        path = "/v1"
    elif path == "/v1/":
        path = "/v1"

    return urlunsplit(
        (parts.scheme, parts.netloc, path, parts.query, parts.fragment),
    )


def _base_url_to_ollama_host(base_url: str) -> Optional[str]:
    value = (base_url or "").strip().rstrip("/")
    if not value:
        return None
    if value.endswith("/v1"):
        value = value[:-3]
    return value or None


def get_ollama_host() -> Optional[str]:
    """Return configured Ollama host URL (without /v1), or ``None``."""
    store = ProviderStore()
    # Prefer active provider if it is ollama.
    active = store.get_active_provider()
    if active and active.provider_type == "ollama":
        return _base_url_to_ollama_host(active.base_url)

    # Fallback to first configured ollama provider.
    for item in store._load():
        if item.provider_type == "ollama":
            return _base_url_to_ollama_host(item.base_url)
    return None


def _normalize_provider_dict(data: dict[str, Any]) -> dict[str, Any]:
    name = str(data.get("name", "")).strip()
    if not name:
        raise ValueError("provider name cannot be empty")

    provider_type = (
        str(data.get("provider_type", "other") or "other").strip().lower()
    )
    if provider_type not in _ALLOWED_PROVIDER_TYPES:
        provider_type = "other"

    raw_model_names = data.get("model_names")
    model_names = (
        [str(item).strip() for item in raw_model_names if str(item).strip()]
        if isinstance(raw_model_names, list)
        else []
    )
    model_name = str(data.get("model_name", "") or "").strip()
    if model_name and model_name not in model_names:
        model_names.insert(0, model_name)
    if not model_name and model_names:
        model_name = model_names[0]
    api_key = str(data.get("api_key", "") or "").strip()
    base_url = str(data.get("base_url", "") or "").strip()
    if provider_type == "ollama" and base_url:
        base_url = _normalize_ollama_base_url(base_url)

    enabled = bool(data.get("enabled", False))
    extra = data.get("extra") if isinstance(data.get("extra"), dict) else {}

    return {
        "name": name,
        "provider_type": provider_type,
        "model_name": model_name,
        "model_names": model_names,
        "api_key": api_key,
        "base_url": base_url,
        "enabled": enabled,
        "extra": extra,
    }


def _normalize_raw(raw: Any) -> list[dict[str, Any]]:
    """Normalize persisted payload to list[provider-dict]."""
    if isinstance(raw, list):
        out: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                out.append(_normalize_provider_dict(item))
            except ValueError:
                continue
        return out

    # Legacy format: {"providers": [...]}.
    if isinstance(raw, dict) and isinstance(raw.get("providers"), list):
        return _normalize_raw(raw.get("providers"))

    return []


class ProviderStore:
    """Stores provider configurations in JSON."""

    def __init__(self, file_path: str | None = None):
        default_path = get_providers_json_path()
        self.file_path = _resolve_store_path(
            file_path,
            default_path=default_path,
        )
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def list_providers(self) -> list[dict]:
        return [item.to_dict() for item in self._load()]

    def get_provider(self, name: str) -> ProviderConfig | None:
        for item in self._load():
            if item.name == name:
                return item
        return None

    def save_provider(self, provider: dict) -> None:
        items = self._load()
        data = _normalize_provider_dict(provider)
        config = ProviderConfig.from_dict(data)
        explicit_enabled = "enabled" in provider
        replaced_idx: int | None = None

        replaced = False
        for idx, item in enumerate(items):
            if item.name == config.name:
                if "enabled" not in provider:
                    config.enabled = item.enabled
                items[idx] = config
                replaced = True
                replaced_idx = idx
                break

        if not explicit_enabled and not any(item.enabled for item in items):
            # Keep the first saved provider immediately usable so
            # README/quickstart commands work without an extra enable step.
            # This also repairs legacy single-provider entries when users save
            # them again after upgrading.
            config.enabled = True
            if replaced and replaced_idx is not None:
                items[replaced_idx] = config

        if not replaced:
            items.append(config)

        # If new provider explicitly enabled, disable others.
        if config.enabled:
            for item in items:
                item.enabled = item.name == config.name

        self._save(items)

    def update_provider_settings(
        self,
        name: str,
        settings: dict,
    ) -> ProviderConfig:
        items = self._load()
        for idx, item in enumerate(items):
            if item.name != name:
                continue

            data = item.to_dict()
            merged = dict(data)
            merged.update(settings)
            merged["name"] = name
            normalized = _normalize_provider_dict(merged)
            normalized["enabled"] = bool(merged.get("enabled", item.enabled))

            updated = ProviderConfig.from_dict(normalized)
            items[idx] = updated

            if updated.enabled:
                for other in items:
                    if other.name != name:
                        other.enabled = False

            self._save(items)
            return updated

        raise KeyError(name)

    def set_enabled(self, name: str) -> ProviderConfig:
        items = self._load()
        found = False
        for item in items:
            item.enabled = item.name == name
            if item.name == name:
                found = True
        if not found:
            raise KeyError(name)
        self._save(items)
        return next(i for i in items if i.name == name)

    def set_disabled(self, name: str) -> ProviderConfig:
        items = self._load()
        for item in items:
            if item.name == name:
                item.enabled = False
                self._save(items)
                return item
        raise KeyError(name)

    def get_active_provider(self) -> ProviderConfig | None:
        for item in self._load():
            if item.enabled:
                return item
        return None

    def remove_provider(self, name: str) -> None:
        items = self._load()
        new_items = [item for item in items if item.name != name]
        if len(new_items) == len(items):
            raise KeyError(name)
        self._save(new_items)

    def _load(self) -> list[ProviderConfig]:
        if self.file_path == get_providers_json_path():
            _migrate_legacy_providers_json(self.file_path)
        raw = _load_store_json(self.file_path)
        if raw is None:
            return []
        return [ProviderConfig.from_dict(p) for p in _normalize_raw(raw)]

    def _save(self, items: list[ProviderConfig]) -> None:
        if self.file_path.exists() and not self.file_path.is_file():
            raise IsADirectoryError(
                f"providers.json path exists but is not a regular file: {self.file_path}",
            )

        is_secure_path = self.file_path == get_providers_json_path()
        _ensure_store_parent(self.file_path, secure=is_secure_path)

        self.file_path.write_text(
            json.dumps(
                [item.to_dict() for item in items],
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        if is_secure_path:
            _chmod_best_effort(self.file_path, 0o600)
