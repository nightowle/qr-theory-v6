from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator, Dict, Optional

from .dispatcher import (
    AuthorizationError,
    InstructionDispatcher,
    SandboxViolation,
    UnknownActionError,
    create_default_dispatcher,
)
from .models import AuditRecord, CommandReceipt, InstructionResult, MCPInstruction
from .security import RolePolicy, SignatureValidationError, SignatureValidator


class InstructionQueue:
    async def get(self) -> MCPInstruction:  # pragma: no cover - interface
        raise NotImplementedError

    async def put(self, instruction: MCPInstruction) -> None:  # pragma: no cover
        raise NotImplementedError


class MemoryInstructionQueue(InstructionQueue):
    def __init__(self) -> None:
        self._queue: asyncio.Queue[MCPInstruction] = asyncio.Queue()

    async def get(self) -> MCPInstruction:
        return await self._queue.get()

    async def put(self, instruction: MCPInstruction) -> None:
        await self._queue.put(instruction)


class MCPService:
    """Eventloop-basierte Implementierung eines MCP-Befehlsempfängers mit Sicherheitsfunktionen."""

    def __init__(
        self,
        dispatcher: Optional[InstructionDispatcher] = None,
        queue: Optional[InstructionQueue] = None,
        result_path: Optional[Path] = None,
        audit_path: Optional[Path] = None,
        signature_validator: Optional[SignatureValidator] = None,
        role_policy: Optional[RolePolicy] = None,
        *,
        dry_run: bool = False,
        default_timeout: float = 30.0,
    ) -> None:
        role_policy = role_policy or (dispatcher.role_policy if dispatcher else None)
        self.dispatcher = dispatcher or create_default_dispatcher(role_policy=role_policy)
        self.queue = queue or MemoryInstructionQueue()
        self.result_path = result_path or Path("./logs/mcp-results.jsonl")
        self.audit_path = audit_path or Path("./logs/mcp-audit.jsonl")
        self.result_path.parent.mkdir(parents=True, exist_ok=True)
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self.signature_validator = signature_validator
        self.dry_run = dry_run
        self.default_timeout = default_timeout
        self._stop = asyncio.Event()
        self._write_lock = asyncio.Lock()

    async def submit(self, instruction: MCPInstruction) -> None:
        await self.queue.put(instruction)

    async def shutdown(self) -> None:
        self._stop.set()

    async def _write_json(self, path: Path, payload: Dict[str, object]) -> None:
        async with self._write_lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._append_json, path, payload)

    @staticmethod
    def _append_json(path: Path, payload: Dict[str, object]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")

    async def _write_result(self, result: InstructionResult) -> None:
        payload = {
            "instruction_id": result.instruction_id,
            "status": result.status,
            "detail": result.detail,
            "produced_at": result.produced_at.isoformat(),
            "duration_ms": result.duration_ms,
            "audit_reference": result.audit_reference,
        }
        await self._write_json(self.result_path, payload)

    async def _write_audit(self, audit: AuditRecord, receipt: CommandReceipt) -> None:
        payload = {
            "instruction_id": audit.instruction_id,
            "action": audit.action,
            "role": audit.role,
            "issued_at": audit.issued_at.isoformat(),
            "started_at": audit.started_at.isoformat(),
            "completed_at": audit.completed_at.isoformat(),
            "status": audit.status,
            "detail": audit.detail,
            "dry_run": audit.dry_run,
            "signature_valid": audit.signature_valid,
            "receipt": {
                "status": receipt.status,
                "received_at": receipt.received_at.isoformat(),
                "detail": receipt.detail,
            },
        }
        await self._write_json(self.audit_path, payload)

    async def run(self) -> None:
        while not self._stop.is_set():
            instruction = await self.queue.get()
            received_at = datetime.now(tz=timezone.utc)
            signature_valid = False
            if self.signature_validator:
                try:
                    signature_valid = self.signature_validator.verify(instruction)
                except SignatureValidationError as exc:
                    now = datetime.now(tz=timezone.utc)
                    result = InstructionResult(
                        instruction_id=instruction.id,
                        status="invalid-signature",
                        detail=str(exc),
                        produced_at=now,
                    )
                    receipt = CommandReceipt(
                        instruction_id=instruction.id,
                        received_at=received_at,
                        status="rejected",
                        detail={"reason": "signature"},
                    )
                    audit = AuditRecord(
                        instruction_id=instruction.id,
                        action=instruction.action,
                        role=instruction.role,
                        issued_at=instruction.issued_at,
                        started_at=received_at,
                        completed_at=now,
                        status=result.status,
                        detail=result.detail,
                        dry_run=False,
                        signature_valid=False,
                        receipt_status=receipt.status,
                    )
                    await self._write_result(result)
                    await self._write_audit(audit, receipt)
                    continue
            else:
                signature_valid = instruction.signature is None

            try:
                handler = self.dispatcher.authorize(instruction)
            except UnknownActionError:
                now = datetime.now(tz=timezone.utc)
                result = InstructionResult(
                    instruction_id=instruction.id,
                    status="unhandled",
                    detail=f"Keine Aktion für '{instruction.action}' registriert",
                    produced_at=now,
                )
            except AuthorizationError as exc:
                now = datetime.now(tz=timezone.utc)
                result = InstructionResult(
                    instruction_id=instruction.id,
                    status="forbidden",
                    detail=str(exc),
                    produced_at=now,
                )
            else:
                start = datetime.now(tz=timezone.utc)
                timeout = instruction.timeout or handler.default_timeout or self.default_timeout
                try:
                    result = await asyncio.wait_for(
                        handler.execute(instruction, dry_run=self.dry_run or instruction.dry_run),
                        timeout=timeout,
                    )
                    duration = datetime.now(tz=timezone.utc) - start
                    result.duration_ms = int(duration.total_seconds() * 1000)
                except asyncio.TimeoutError:
                    now = datetime.now(tz=timezone.utc)
                    result = InstructionResult(
                        instruction_id=instruction.id,
                        status="timeout",
                        detail=f"Timeout nach {timeout} Sekunden",
                        produced_at=now,
                    )
                except SandboxViolation as exc:
                    now = datetime.now(tz=timezone.utc)
                    result = InstructionResult(
                        instruction_id=instruction.id,
                        status="rejected",
                        detail=str(exc),
                        produced_at=now,
                    )
                except Exception as exc:  # pragma: no cover - defensive
                    now = datetime.now(tz=timezone.utc)
                    result = InstructionResult(
                        instruction_id=instruction.id,
                        status="error",
                        detail=str(exc),
                        produced_at=now,
                    )

            receipt_status = "accepted" if result.status not in {"invalid-signature", "forbidden"} else "rejected"
            receipt = CommandReceipt(
                instruction_id=instruction.id,
                received_at=received_at,
                status=receipt_status,
                detail={"role": instruction.role},
            )
            audit = AuditRecord(
                instruction_id=instruction.id,
                action=instruction.action,
                role=instruction.role,
                issued_at=instruction.issued_at,
                started_at=received_at,
                completed_at=result.produced_at,
                status=result.status,
                detail=result.detail,
                dry_run=self.dry_run or instruction.dry_run,
                signature_valid=signature_valid,
                receipt_status=receipt.status,
            )
            await self._write_result(result)
            await self._write_audit(audit, receipt)

    def register_handler(self, action: str, handler) -> None:
        self.dispatcher.register(action, handler)


async def iter_json_instructions(path: Path) -> AsyncIterator[MCPInstruction]:
    loop = asyncio.get_running_loop()
    handle = await loop.run_in_executor(None, path.open, "r", encoding="utf-8")
    try:
        while True:
            line = await loop.run_in_executor(None, handle.readline)
            if not line:
                break
            data = json.loads(line)
            yield MCPInstruction.from_payload(data)
    finally:
        await loop.run_in_executor(None, handle.close)
