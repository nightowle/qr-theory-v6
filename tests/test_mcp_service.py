from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import pytest

from qr_automation.mcp.models import MCPInstruction
from qr_automation.mcp.service import MCPService, MemoryInstructionQueue


@pytest.mark.asyncio
async def test_service_writes_results(tmp_path: Path) -> None:
    queue = MemoryInstructionQueue()
    service = MCPService(queue=queue, result_path=tmp_path / "results.jsonl")
    task = asyncio.create_task(service.run())

    instruction = MCPInstruction(
        id="1",
        action="log",
        payload={},
        issued_at=datetime.now(tz=timezone.utc),
    )
    await service.submit(instruction)
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    content = (tmp_path / "results.jsonl").read_text(encoding="utf-8")
    assert "instruction_id" in content
