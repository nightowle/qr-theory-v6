from __future__ import annotations

import pytest

from qr_automation.chat.models import ChatMessage
from qr_automation.chat.storage import utcnow
from qr_automation.gateway.base import AgentAdapter
from qr_automation.gateway.manager import GatewayManager


class RecorderAdapter(AgentAdapter):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.messages: list[ChatMessage] = []

    async def dispatch(self, message: ChatMessage):
        self.messages.append(message)
        return {"status": "received"}


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
