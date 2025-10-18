from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from qr_automation.chat.server import build_app
from qr_automation.gateway.base import EchoAdapter
from qr_automation.gateway.manager import GatewayManager


@pytest.mark.asyncio
async def test_message_flow(tmp_path: Path) -> None:
    gateway = GatewayManager()
    await gateway.register_adapter(EchoAdapter("echo"))
    app = build_app(
        storage_path=tmp_path / "chat.db",
        audit_path=tmp_path / "audit.jsonl",
        gateway=gateway,
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/agents", json={"name": "Blue", "type": "human", "id": "agent-1"})
        assert res.status_code == 200
        res = await client.post(
            "/messages",
            json={
                "room": "lab",
                "sender_id": "agent-1",
                "content": "Hallo",
                "target_adapter": "echo",
            },
        )
        assert res.status_code == 200
        body = res.json()
        assert body["room"] == "lab"

        history = await client.get("/messages", params={"room": "lab"})
        assert history.status_code == 200
        assert len(history.json()) == 1
