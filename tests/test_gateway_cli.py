from __future__ import annotations

import json
from argparse import Namespace

import pytest
from httpx import MockTransport, Request, Response

import qr_automation.cli as cli
from qr_automation.gateway.config import AdapterConfig, GatewayConfig


def build_args(metadata: str) -> Namespace:
    return Namespace(
        command="gateway",
        gateway_command="send",
        config="ignored",
        adapter="zapier-webhook",
        message="CLI-Test",
        room="lab",
        sender_id="tester",
        sender_type="human",
        metadata=metadata,
    )


def stub_config(monkeypatch) -> None:
    config = GatewayConfig(adapters=[], queue_size=4, concurrency=1)
    monkeypatch.setattr(cli, "load_gateway_config", lambda path: config)


@pytest.mark.asyncio
async def test_gateway_send_command(monkeypatch, capsys) -> None:
    captured: dict[str, object] = {}

    def handler(request: Request) -> Response:
        captured["url"] = str(request.url)
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return Response(200, json={"status": "ok"})

    transport = MockTransport(handler)
    config = GatewayConfig(
        adapters=[
            AdapterConfig(
                name="zapier-webhook",
                implementation="qr_automation.gateway.adapters.zapier:ZapierAdapter",
                options={
                    "webhook_url": "https://hooks.zapier.com/hooks/catch/123/abc/",
                    "client_options": {"transport": transport},
                },
            )
        ],
        queue_size=4,
        concurrency=1,
    )

    monkeypatch.setattr(cli, "load_gateway_config", lambda path: config)

    await cli.handle_gateway_command(build_args(json.dumps({"origin": "unit-test"})))

    out = capsys.readouterr().out
    assert "Nachricht an Adapter 'zapier-webhook' gesendet." in out
    assert '"status": "ok"' in out

    assert captured["url"] == "https://hooks.zapier.com/hooks/catch/123/abc/"
    payload = captured["payload"]
    assert payload["content"] == "CLI-Test"
    assert payload["metadata"] == {"origin": "unit-test"}


@pytest.mark.asyncio
async def test_gateway_send_rejects_invalid_metadata_json(monkeypatch, capsys) -> None:
    stub_config(monkeypatch)

    with pytest.raises(SystemExit) as exc_info:
        await cli.handle_gateway_command(build_args("{invalid"))

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Ungültiges JSON in --metadata" in captured.err


@pytest.mark.asyncio
async def test_gateway_send_rejects_non_object_metadata(monkeypatch, capsys) -> None:
    stub_config(monkeypatch)

    with pytest.raises(SystemExit) as exc_info:
        await cli.handle_gateway_command(build_args("[]"))

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--metadata muss ein JSON-Objekt" in captured.err
