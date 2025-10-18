from __future__ import annotations

import asyncio
from typing import Dict, Optional

from ..chat.models import ChatMessage
from .base import AgentAdapter


class GatewayManager:
    """Verwaltet registrierte KI-Adapter und orchestriert Dispatch-Aufrufe."""

    def __init__(self) -> None:
        self._adapters: Dict[str, AgentAdapter] = {}
        self._lock = asyncio.Lock()

    async def register_adapter(self, adapter: AgentAdapter) -> None:
        async with self._lock:
            self._adapters[adapter.name] = adapter

    async def unregister_adapter(self, name: str) -> None:
        async with self._lock:
            self._adapters.pop(name, None)

    async def dispatch(self, adapter_name: str, message: ChatMessage) -> Optional[dict]:
        async with self._lock:
            adapter = self._adapters.get(adapter_name)
        if adapter is None:
            raise ValueError(f"Kein Adapter für Kennung '{adapter_name}' registriert")
        return await adapter.dispatch(message)

    async def list_adapters(self) -> Dict[str, str]:
        async with self._lock:
            return {name: adapter.__class__.__name__ for name, adapter in self._adapters.items()}


def create_default_gateway() -> GatewayManager:
    return GatewayManager()
