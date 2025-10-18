from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from qr_automation.mcp.dispatcher import ActionHandler, InstructionDispatcher, SandboxViolation
from qr_automation.mcp.models import InstructionResult, InstructionSignature, MCPInstruction
from qr_automation.mcp.security import SignatureValidator
from qr_automation.mcp.service import MCPService, MemoryInstructionQueue


class RecordingHandler(ActionHandler):
    def __init__(self) -> None:
        super().__init__("recorder", allowed_roles={"system"}, supports_dry_run=True)
        self.run_called = asyncio.Event()

    async def run(self, instruction: MCPInstruction) -> InstructionResult:
        self.run_called.set()
        return InstructionResult(
            instruction_id=instruction.id,
            status="executed",
            detail="run",
            produced_at=datetime.now(tz=timezone.utc),
        )  # pragma: no cover - sollte im Test nicht erreicht werden


class SlowHandler(ActionHandler):
    def __init__(self) -> None:
        super().__init__("slow", allowed_roles={"system"}, supports_dry_run=False, default_timeout=0.1)

    async def run(self, instruction: MCPInstruction) -> InstructionResult:  # pragma: no cover - invoked in timeout branch
        await asyncio.sleep(1)
        return InstructionResult(
            instruction_id=instruction.id,
            status="ok",
            detail="done",
            produced_at=datetime.now(tz=timezone.utc),
        )


class FailingHandler(ActionHandler):
    def __init__(self) -> None:
        super().__init__("fail", allowed_roles={"system"}, supports_dry_run=True)

    async def run(self, instruction: MCPInstruction):  # pragma: no cover - invoked in rejection test
        raise SandboxViolation("forbidden")


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return []
    return [json.loads(line) for line in content.splitlines()]


@pytest.mark.asyncio
async def test_service_writes_results(tmp_path: Path) -> None:
    queue = MemoryInstructionQueue()
    service = MCPService(queue=queue, result_path=tmp_path / "results.jsonl", audit_path=tmp_path / "audit.jsonl")
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

    results = _read_jsonl(tmp_path / "results.jsonl")
    audits = _read_jsonl(tmp_path / "audit.jsonl")
    assert results[0]["instruction_id"] == "1"
    assert audits[0]["status"] == results[0]["status"]


@pytest.mark.asyncio
async def test_service_rejects_invalid_signature(tmp_path: Path) -> None:
    queue = MemoryInstructionQueue()
    validator = SignatureValidator({"key1": b"secret"})
    service = MCPService(
        queue=queue,
        signature_validator=validator,
        result_path=tmp_path / "results.jsonl",
        audit_path=tmp_path / "audit.jsonl",
    )
    task = asyncio.create_task(service.run())

    instruction = MCPInstruction(
        id="sig",
        action="log",
        payload={},
        issued_at=datetime.now(tz=timezone.utc),
        signature=InstructionSignature(algorithm="hs256", key_id="key1", value="deadbeef"),
    )
    await service.submit(instruction)
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    results = _read_jsonl(tmp_path / "results.jsonl")
    assert results[0]["status"] == "invalid-signature"


@pytest.mark.asyncio
async def test_dry_run_skips_handler_execution(tmp_path: Path) -> None:
    dispatcher = InstructionDispatcher()
    handler = RecordingHandler()
    dispatcher.register("log", handler)
    queue = MemoryInstructionQueue()
    service = MCPService(
        dispatcher=dispatcher,
        queue=queue,
        dry_run=True,
        result_path=tmp_path / "results.jsonl",
        audit_path=tmp_path / "audit.jsonl",
    )
    task = asyncio.create_task(service.run())

    instruction = MCPInstruction(
        id="dry",
        action="log",
        payload={},
        issued_at=datetime.now(tz=timezone.utc),
    )
    await service.submit(instruction)
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert not handler.run_called.is_set()
    results = _read_jsonl(tmp_path / "results.jsonl")
    assert results[0]["status"] == "dry-run"


@pytest.mark.asyncio
async def test_timeout_produces_timeout_status(tmp_path: Path) -> None:
    dispatcher = InstructionDispatcher()
    dispatcher.register("slow", SlowHandler())
    queue = MemoryInstructionQueue()
    service = MCPService(
        dispatcher=dispatcher,
        queue=queue,
        result_path=tmp_path / "results.jsonl",
        audit_path=tmp_path / "audit.jsonl",
        default_timeout=0.2,
    )
    task = asyncio.create_task(service.run())

    instruction = MCPInstruction(
        id="slow",
        action="slow",
        payload={},
        issued_at=datetime.now(tz=timezone.utc),
    )
    await service.submit(instruction)
    await asyncio.sleep(0.3)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    results = _read_jsonl(tmp_path / "results.jsonl")
    assert results[0]["status"] == "timeout"


@pytest.mark.asyncio
async def test_sandbox_violation_results_in_rejection(tmp_path: Path) -> None:
    dispatcher = InstructionDispatcher()
    dispatcher.register("fail", FailingHandler())
    queue = MemoryInstructionQueue()
    service = MCPService(
        dispatcher=dispatcher,
        queue=queue,
        result_path=tmp_path / "results.jsonl",
        audit_path=tmp_path / "audit.jsonl",
    )
    task = asyncio.create_task(service.run())

    instruction = MCPInstruction(
        id="fail",
        action="fail",
        payload={},
        issued_at=datetime.now(tz=timezone.utc),
    )
    await service.submit(instruction)
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    results = _read_jsonl(tmp_path / "results.jsonl")
    assert results[0]["status"] == "rejected"
