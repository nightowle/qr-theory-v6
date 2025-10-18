from __future__ import annotations

from typing import Dict

import pytest

from qr_automation.chat.models import ChatMessage
from qr_automation.chat.storage import utcnow
from qr_automation.gateway.base import AgentAdapter, AdapterDispatchError
from qr_automation.gateway.config import AdapterConfig, CacheConfig, RateLimitConfig
from qr_automation.gateway.manager import GatewayManager


class RecorderAdapter(AgentAdapter):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.messages: list[ChatMessage] = []

    async def dispatch(self, message: ChatMessage) -> Dict[str, str]:
        self.messages.append(message)
        return {"status": "received"}


class CachedAdapter(AgentAdapter):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.counter = 0

    def cache_key(self, message: ChatMessage) -> str:
        return message.content

    async def dispatch(self, message: ChatMessage) -> Dict[str, int]:
        self.counter += 1
        return {"counter": self.counter}


@pytest.mark.asyncio
async def test_dispatch_to_registered_adapter() -> None:
    manager = GatewayManager()
    adapter = RecorderAdapter("recorder")
    await manager.register_adapter(adapter)
    message = ChatMessage(
        id="1",
        room="lab",
        sender_id="blue",
        sender_type="human",
        content="Hallo",
        metadata={},
        created_at=utcnow(),
    )
    response = await manager.dispatch("recorder", message)
    assert response == {"status": "received"}
    assert adapter.messages[0].content == "Hallo"


@pytest.mark.asyncio
async def test_rate_limit_is_enforced() -> None:
    manager = GatewayManager()
    config = AdapterConfig(
        name="limited",
        implementation="tests.test_gateway_manager:RecorderAdapter",
        rate_limit=RateLimitConfig(capacity=1, refill_rate=0.0001),
    )
    adapter = RecorderAdapter("limited")
    await manager.register_adapter(adapter, config=config)
    message = ChatMessage(
        id="2",
        room="lab",
        sender_id="blue",
        sender_type="human",
        content="Test",
        metadata={},
        created_at=utcnow(),
    )
    await manager.dispatch("limited", message)
    with pytest.raises(AdapterDispatchError):
        await manager.dispatch("limited", message)


@pytest.mark.asyncio
async def test_cache_reduces_adapter_calls() -> None:
    manager = GatewayManager()
    config = AdapterConfig(
        name="cached",
        implementation="tests.test_gateway_manager:CachedAdapter",
        cache=CacheConfig(enabled=True, ttl_seconds=60, max_entries=10),
    )
    adapter = CachedAdapter("cached")
    await manager.register_adapter(adapter, config=config)
    message = ChatMessage(
        id="3",
        room="lab",
        sender_id="blue",
        sender_type="human",
        content="Cache",
        metadata={},
        created_at=utcnow(),
    )
    first = await manager.dispatch("cached", message)
    second = await manager.dispatch("cached", message)
    assert first == second
    assert adapter.counter == 1
