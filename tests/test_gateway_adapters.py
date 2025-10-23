from __future__ import annotations

import json
from typing import Dict

import pytest
from httpx import MockTransport, Request, Response

from qr_automation.chat.models import ChatMessage
from qr_automation.chat.storage import utcnow
from qr_automation.gateway.adapters.chatgpt import ChatGPTAdapter
from qr_automation.gateway.adapters.zapier import ZapierAdapter
from qr_automation.gateway.base import AdapterDispatchError
from qr_automation.gateway.config import AdapterConfig


@pytest.mark.asyncio
async def test_zapier_adapter_dispatch_sends_payload() -> None:
    captured: Dict[str, object] = {}

    def handler(request: Request) -> Response:
        captured["url"] = str(request.url)
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return Response(200, json={"status": "ok"})

    transport = MockTransport(handler)
    config = AdapterConfig(
        name="zapier",
        implementation="qr_automation.gateway.adapters.zapier:ZapierAdapter",
        options={
            "webhook_url": "https://hooks.zapier.com/hooks/catch/123/abc/",
            "client_options": {"transport": transport},
        },
    )
    adapter = ZapierAdapter("zapier", config=config)
    await adapter.start()
    message = ChatMessage(
        id="42",
        room="lab",
        sender_id="blue",
        sender_type="human",
        content="Ping",
        metadata={"origin": "test"},
        created_at=utcnow(),
    )
    response = await adapter.dispatch(message)
    await adapter.stop()

    assert captured["url"] == "https://hooks.zapier.com/hooks/catch/123/abc/"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["content"] == "Ping"
    assert response == {
        "type": "zapier_webhook",
        "adapter": "zapier",
        "status_code": 200,
        "response": {"status": "ok"},
    }


@pytest.mark.asyncio
async def test_zapier_adapter_requires_webhook_url() -> None:
    config = AdapterConfig(
        name="zapier-missing",
        implementation="qr_automation.gateway.adapters.zapier:ZapierAdapter",
        options={},
    )
    adapter = ZapierAdapter("zapier-missing", config=config)
    await adapter.start()
    message = ChatMessage(
        id="99",
        room="lab",
        sender_id="blue",
        sender_type="human",
        content="Ping",
        metadata={},
        created_at=utcnow(),
    )
    with pytest.raises(AdapterDispatchError):
        await adapter.dispatch(message)
    await adapter.stop()


def test_chatgpt_adapter_declares_protocol() -> None:
    config = AdapterConfig(
        name="chatgpt",
        implementation="qr_automation.gateway.adapters.chatgpt:ChatGPTAdapter",
        options={},
    )
    adapter = ChatGPTAdapter("chatgpt", config=config)
    assert "ChatGPT" in adapter.protocols
    assert adapter.model == "gpt-4o-mini"
