from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from importlib import import_module
from typing import Dict, Optional

from ..chat.models import ChatMessage
from .base import AgentAdapter, AdapterDispatchError, AdapterLifecycleError
from .cache import TTLCache
from .config import AdapterConfig, GatewayConfig
from .limits import TokenBucket
from .metrics import MetricsRegistry


logger = logging.getLogger(__name__)


@dataclass
class AdapterContext:
    adapter: AgentAdapter
    config: Optional[AdapterConfig]
    rate_limiter: Optional[TokenBucket]
    cache: Optional[TTLCache]


class GatewayManager:
    """Verwaltet registrierte KI-Adapter und orchestriert Dispatch-Aufrufe."""

    def __init__(self, metrics: Optional[MetricsRegistry] = None) -> None:
        self._adapters: Dict[str, AdapterContext] = {}
        self._lock = asyncio.Lock()
        self._metrics = metrics or MetricsRegistry()
        self._requests_total = None
        self._errors_total = None

    async def _ensure_metrics(self) -> None:
        if self._requests_total is None:
            self._requests_total = await self._metrics.counter(
                "gateway_requests_total",
                "Anzahl der erfolgreichen Dispatch-Aufrufe",
            )
        if self._errors_total is None:
            self._errors_total = await self._metrics.counter(
                "gateway_errors_total",
                "Anzahl der fehlgeschlagenen Dispatch-Aufrufe",
            )

    async def register_adapter(self, adapter: AgentAdapter, config: Optional[AdapterConfig] = None) -> None:
        await self._ensure_metrics()
        config = config or getattr(adapter, "config", None)
        rate_limiter = None
        cache = None
        if config and config.rate_limit:
            rate_limiter = TokenBucket(
                capacity=config.rate_limit.capacity,
                refill_rate=config.rate_limit.refill_rate,
            )
        if config and config.cache and config.cache.enabled:
            cache = TTLCache(
                max_entries=config.cache.max_entries,
                ttl_seconds=config.cache.ttl_seconds,
            )
        try:
            await adapter.start()
        except Exception as exc:  # pragma: no cover - Fehlerpfad
            logger.exception("Adapter %s konnte nicht gestartet werden", adapter.name)
            raise AdapterLifecycleError(str(exc)) from exc
        async with self._lock:
            self._adapters[adapter.name] = AdapterContext(
                adapter=adapter,
                config=config,
                rate_limiter=rate_limiter,
                cache=cache,
            )

    async def unregister_adapter(self, name: str) -> None:
        async with self._lock:
            context = self._adapters.pop(name, None)
        if context:
            try:
                await context.adapter.stop()
            except Exception:  # pragma: no cover - Schutz vor Stop-Fehlern
                logger.warning("Adapter %s konnte nicht sauber gestoppt werden", name)

    async def dispatch(self, adapter_name: str, message: ChatMessage) -> Optional[dict]:
        async with self._lock:
            context = self._adapters.get(adapter_name)
        if context is None:
            raise ValueError(f"Kein Adapter für Kennung '{adapter_name}' registriert")
        adapter = context.adapter
        if context.rate_limiter and not context.rate_limiter.consume():
            if self._errors_total:
                self._errors_total.inc()
            raise AdapterDispatchError(f"Rate-Limit für Adapter '{adapter_name}' erreicht")
        cache_key = adapter.cache_key(message) if context.cache else None
        if cache_key and context.cache:
            cached = context.cache.get(cache_key)
            if cached is not None:
                if self._requests_total:
                    self._requests_total.inc()
                return cached
        try:
            response = await adapter.dispatch(message)
            if context.cache and cache_key and response is not None:
                context.cache.set(cache_key, response)
            if self._requests_total:
                self._requests_total.inc()
            return response
        except AdapterDispatchError:
            if self._errors_total:
                self._errors_total.inc()
            raise
        except Exception as exc:
            if self._errors_total:
                self._errors_total.inc()
            logger.exception("Adapter %s hat einen Fehler ausgelöst", adapter_name)
            raise AdapterDispatchError(str(exc)) from exc

    async def list_adapters(self) -> Dict[str, str]:
        async with self._lock:
            return {
                name: context.adapter.__class__.__name__
                for name, context in self._adapters.items()
            }

    async def snapshot(self) -> Dict[str, Dict[str, object]]:
        return await self._metrics.snapshot()

    async def shutdown(self) -> None:
        """Stoppt alle registrierten Adapter und leert die Registry."""

        async with self._lock:
            items = list(self._adapters.items())
            self._adapters.clear()
        for name, context in items:
            try:
                await context.adapter.stop()
            except Exception:  # pragma: no cover - Schutz vor Stop-Fehlern
                logger.warning("Adapter %s konnte nicht sauber gestoppt werden", name)

    async def reload_from_config(self, config: GatewayConfig) -> None:
        """Lädt Adapter gemäß Konfigurationsdatei nach (Hot-Swap)."""

        new_names = {adapter_config.name for adapter_config in config.adapters}
        async with self._lock:
            current_names = set(self._adapters.keys())
        # Entferne Adapter, die nicht mehr konfiguriert sind
        for name in current_names - new_names:
            await self.unregister_adapter(name)
        # Aktualisiere bestehende oder füge neue hinzu
        for adapter_config in config.adapters:
            context = None
            async with self._lock:
                context = self._adapters.get(adapter_config.name)
            if context and context.config == adapter_config:
                continue
            if context:
                await self.unregister_adapter(adapter_config.name)
            adapter = instantiate_adapter(adapter_config)
            await self.register_adapter(adapter, config=adapter_config)


def create_default_gateway() -> GatewayManager:
    return GatewayManager()


def instantiate_adapter(config: AdapterConfig) -> AgentAdapter:
    module_path, _, class_name = config.implementation.partition(":")
    if not module_path or not class_name:
        raise ValueError(
            f"Ungültige Implementation für Adapter '{config.name}': {config.implementation}"
        )
    module = import_module(module_path)
    adapter_cls = getattr(module, class_name, None)
    if adapter_cls is None:
        raise ValueError(
            f"Adapterklasse '{class_name}' konnte in Modul '{module_path}' nicht gefunden werden"
        )
    if not issubclass(adapter_cls, AgentAdapter):
        raise TypeError(
            f"Klasse '{class_name}' ist kein AgentAdapter-Untertyp"
        )
    return adapter_cls(config.name, config=config)


__all__ = [
    "GatewayManager",
    "create_default_gateway",
    "instantiate_adapter",
]
