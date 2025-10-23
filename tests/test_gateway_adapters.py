from __future__ import annotations

import json
from typing import Dict

import pytest
from httpx import MockTransport, Request, Response

from qr_automation.chat.models import ChatMessage
from qr_automation.chat.storage import utcnow
from qr_automation.gateway.adapters.chatgpt import ChatGPTAdapter
from qr_automation.gateway.adapters.zapier import ZapierAdapter
from qr_automation.gateway.base import AdapterDispatchError, AgentAdapter
from qr_automation.gateway.config import AdapterConfig
from qr_automation.gateway.manager import GatewayManager


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


@pytest.mark.asyncio
async def test_zapier_adapter_reads_webhook_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: Dict[str, object] = {}

    def handler(request: Request) -> Response:
        captured["url"] = str(request.url)
        return Response(200, json={"status": "env-ok"})

    transport = MockTransport(handler)
    monkeypatch.setenv("ZAPIER_WEBHOOK_URL", "https://hooks.zapier.com/hooks/catch/456/def/")
    config = AdapterConfig(
        name="zapier-env",
        implementation="qr_automation.gateway.adapters.zapier:ZapierAdapter",
        options={
            "webhook_url_env": "ZAPIER_WEBHOOK_URL",
            "client_options": {"transport": transport},
        },
    )
    adapter = ZapierAdapter("zapier-env", config=config)
    await adapter.start()
    message = ChatMessage(
        id="11",
        room="lab",
        sender_id="blue",
        sender_type="human",
        content="Ping",
        metadata={},
        created_at=utcnow(),
    )
    response = await adapter.dispatch(message)
    await adapter.stop()

    assert captured["url"] == "https://hooks.zapier.com/hooks/catch/456/def/"
    assert response == {
        "type": "zapier_webhook",
        "adapter": "zapier-env",
        "status_code": 200,
        "response": {"status": "env-ok"},
    }


def test_chatgpt_adapter_declares_protocol() -> None:
    config = AdapterConfig(
        name="chatgpt",
        implementation="qr_automation.gateway.adapters.chatgpt:ChatGPTAdapter",
        options={},
    )
    adapter = ChatGPTAdapter("chatgpt", config=config)
    assert "ChatGPT" in adapter.protocols
    assert adapter.model == "gpt-4o-mini"


class _DummyAdapter(AgentAdapter):
    def __init__(self) -> None:
        super().__init__("dummy")
        self.started = False
        self.stopped = False

    async def start(self) -> None:  # pragma: no cover - trivial
        await super().start()
        self.started = True

    async def stop(self) -> None:  # pragma: no cover - trivial
        await super().stop()
        self.stopped = True

    async def dispatch(self, message: ChatMessage) -> Dict[str, object] | None:
        return {"ok": True, "content": message.content}


@pytest.mark.asyncio
async def test_gateway_manager_shutdown_stops_adapters() -> None:
    manager = GatewayManager()
    adapter = _DummyAdapter()
    await manager.register_adapter(adapter)
    assert adapter.started is True
    await manager.shutdown()
    assert adapter.stopped is True
