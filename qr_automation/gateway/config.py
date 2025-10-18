from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import json

from pydantic import BaseModel, Field, ValidationError, model_validator

try:  # pragma: no cover - optional Abhängigkeit
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    yaml = None


class RateLimitConfig(BaseModel):
    """Token-Bucket-Rate-Limit-Konfiguration pro Adapter."""

    capacity: int = Field(gt=0, description="Maximale Anzahl Tokens im Bucket")
    refill_rate: float = Field(gt=0, description="Tokens pro Sekunde")


class CacheConfig(BaseModel):
    """TTL-basierte Cache-Konfiguration."""

    enabled: bool = True
    ttl_seconds: float = Field(default=60.0, ge=0.0)
    max_entries: int = Field(default=512, gt=0)


class AuthConfig(BaseModel):
    """Definiert, wie ein Adapter auf Zugangsdaten zugreift."""

    type: str = Field(default="none", description="bspw. bearer, api_key")
    environment_variable: Optional[str] = Field(
        default=None,
        description="Name der Umgebungsvariable, die den Token hält",
    )


class AdapterConfig(BaseModel):
    """Deklarative Beschreibung eines Adapters in der Gateway-Konfiguration."""

    name: str
    implementation: str = Field(
        description="Python-Pfad zur Adapterklasse, z. B. qr_automation.gateway.adapters.openai:OpenAIAdapter"
    )
    protocols: List[str] = Field(default_factory=list)
    priority: int = Field(default=0, description="Höhere Werte bedeuten bevorzugte Verarbeitung")
    options: Dict[str, Any] = Field(default_factory=dict)
    rate_limit: Optional[RateLimitConfig] = None
    cache: Optional[CacheConfig] = None
    auth: Optional[AuthConfig] = None

    model_config = {
        "extra": "allow",
    }


class GatewayConfig(BaseModel):
    """Komplette Gateway-Beschreibung inklusive Service-Parametern."""

    adapters: List[AdapterConfig] = Field(default_factory=list)
    queue_size: int = Field(default=128, gt=0)
    concurrency: int = Field(default=4, gt=0)
    telemetry_interval: float = Field(default=30.0, gt=0)

    @model_validator(mode="after")
    def _validate_unique_names(cls, values: "GatewayConfig") -> "GatewayConfig":
        names = [adapter.name for adapter in values.adapters]
        duplicates = {name for name in names if names.count(name) > 1}
        if duplicates:
            raise ValueError(f"Adapter-Namen müssen eindeutig sein: {', '.join(sorted(duplicates))}")
        return values


def _read_file(path: Path) -> str:
    with path.open("r", encoding="utf-8") as handle:
        return handle.read()


def load_gateway_config(source: str | Path) -> GatewayConfig:
    """Lädt eine Gateway-Konfiguration aus YAML- oder JSON-Dateien."""

    path = Path(source)
    raw = _read_file(path)
    if path.suffix.lower() in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("PyYAML ist nicht installiert, YAML-Konfigurationen können nicht geladen werden")
        data = yaml.safe_load(raw)
    elif path.suffix.lower() == ".json":
        data = json.loads(raw)
    else:
        raise ValueError("Unterstützte Formate sind .yaml, .yml und .json")
    try:
        return GatewayConfig.model_validate(data)
    except ValidationError as exc:  # pragma: no cover - pydantic liefert detailreiche Meldung
        raise ValueError(str(exc)) from exc


def dump_gateway_config(config: GatewayConfig, target: str | Path) -> None:
    """Schreibt eine Gateway-Konfiguration als YAML-Datei."""

    path = Path(target)
    payload = config.model_dump(mode="json", exclude_none=True)
    if path.suffix.lower() == ".json":
        text = json.dumps(payload, indent=2)
    else:
        if yaml is None:
            raise RuntimeError("PyYAML ist nicht installiert, YAML-Konfigurationen können nicht geschrieben werden")
        text = yaml.safe_dump(payload, sort_keys=False)
    path.write_text(text, encoding="utf-8")


__all__ = [
    "AdapterConfig",
    "GatewayConfig",
    "RateLimitConfig",
    "CacheConfig",
    "AuthConfig",
    "load_gateway_config",
    "dump_gateway_config",
]
