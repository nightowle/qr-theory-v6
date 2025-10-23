from __future__ import annotations

import argparse
import json

import pytest

from qr_automation.cli import handle_gateway_command


@pytest.mark.asyncio
async def test_handle_gateway_dispatch_sends_message(tmp_path, capsys) -> None:
    config_path = tmp_path / "gateway.json"
    config_path.write_text(
        json.dumps(
            {
                "queue_size": 4,
                "concurrency": 1,
                "adapters": [
                    {
                        "name": "echo-test",
                        "implementation": "qr_automation.gateway.base:EchoAdapter",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    args = argparse.Namespace(
        command="gateway",
        gateway_command="dispatch",
        config=str(config_path),
        adapter="echo-test",
        content="Hallo Zapier",
        room="cli-lab",
        sender_id="blue",
        sender_type="human",
        metadata=None,
        message_id="cli-1",
    )

    await handle_gateway_command(args)

    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())
    assert payload["type"] == "echo"
    assert payload["original_message_id"] == "cli-1"
    assert payload["content"] == "Echo: Hallo Zapier"


@pytest.mark.asyncio
async def test_handle_gateway_shutdown_on_reload_error(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "gateway.json"
    config_path.write_text(
        json.dumps(
            {
                "queue_size": 4,
                "concurrency": 1,
                "adapters": [],
            }
        ),
        encoding="utf-8",
    )

    class _FailingManager:
        def __init__(self) -> None:
            self.shutdown_called = False

        async def reload_from_config(self, config) -> None:  # pragma: no cover - Fehlerpfad
            raise RuntimeError("Konfiguration fehlerhaft")

        async def shutdown(self) -> None:
            self.shutdown_called = True

    failing_manager = _FailingManager()
    monkeypatch.setattr("qr_automation.cli.GatewayManager", lambda: failing_manager)

    args = argparse.Namespace(
        command="gateway",
        gateway_command="list",
        config=str(config_path),
    )

    with pytest.raises(RuntimeError):
        await handle_gateway_command(args)

    assert failing_manager.shutdown_called is True
