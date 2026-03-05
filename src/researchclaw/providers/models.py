"""Provider data models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ProviderConfig:
    name: str
    provider_type: str
    model_name: str = ""
    api_key: str = ""
    base_url: str = ""
    enabled: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProviderConfig":
        return cls(
            name=data.get("name", ""),
            provider_type=data.get("provider_type", ""),
            model_name=data.get("model_name", ""),
            api_key=data.get("api_key", ""),
            base_url=data.get("base_url", ""),
            enabled=bool(data.get("enabled", False)),
            extra=data.get("extra", {}),
        )
