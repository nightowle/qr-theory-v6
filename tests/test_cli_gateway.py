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
