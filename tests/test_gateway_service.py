from __future__ import annotations

from typing import Dict

import pytest

from qr_automation.chat.models import ChatMessage
from qr_automation.chat.storage import utcnow
from qr_automation.gateway.base import AgentAdapter
from qr_automation.gateway.config import AdapterConfig, CacheConfig, GatewayConfig
from qr_automation.gateway.manager import GatewayManager
from qr_automation.gateway.service import GatewayService


class EchoRecorderAdapter(AgentAdapter):
    def __init__(self, name: str, config=None) -> None:
        super().__init__(name, config=config)
        self.calls = 0

    def cache_key(self, message: ChatMessage) -> str:
        return message.content

    async def dispatch(self, message: ChatMessage) -> Dict[str, str]:
        self.calls += 1
        return {"content": f"Echo {message.content}"}


@pytest.mark.asyncio
async def test_gateway_service_processes_queue() -> None:
    config = GatewayConfig(
        queue_size=4,
        concurrency=1,
        adapters=[
            AdapterConfig(
                name="queue",
                implementation="tests.test_gateway_service:EchoRecorderAdapter",
            )
        ],
    )
    manager = GatewayManager()
    service = GatewayService(manager, config)
    await service.start()
    message = ChatMessage(
        id="42",
        room="lab",
        sender_id="blue",
        sender_type="human",
        content="Queue",
        metadata={},
        created_at=utcnow(),
    )
    response = await service.submit("queue", message)
    assert response == {"content": "Echo Queue"}
    await service.stop()


@pytest.mark.asyncio
async def test_gateway_service_reuses_cache() -> None:
    config = GatewayConfig(
        queue_size=4,
        concurrency=1,
        adapters=[
            AdapterConfig(
                name="cached",
                implementation="tests.test_gateway_service:EchoRecorderAdapter",
                cache=CacheConfig(enabled=True, ttl_seconds=30, max_entries=10),
            )
        ],
    )
    manager = GatewayManager()
    service = GatewayService(manager, config)
    await service.start()
    message = ChatMessage(
        id="99",
        room="lab",
        sender_id="blue",
        sender_type="human",
        content="Cache",
        metadata={},
        created_at=utcnow(),
    )
    await service.submit("cached", message)
    await service.submit("cached", message)
    context = manager._adapters["cached"]
    adapter = context.adapter
    assert getattr(adapter, "calls", None) == 1
    await service.stop()
