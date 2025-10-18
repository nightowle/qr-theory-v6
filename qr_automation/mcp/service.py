from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import AsyncIterator, Dict, Optional

from .dispatcher import ActionHandler, InstructionDispatcher, create_default_dispatcher
from .models import InstructionResult, MCPInstruction


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
    """Einfache Eventloop-basierte Implementierung eines MCP-Befehlsempfängers."""

    def __init__(
        self,
        dispatcher: Optional[InstructionDispatcher] = None,
        queue: Optional[InstructionQueue] = None,
        result_path: Optional[Path] = None,
    ) -> None:
        self.dispatcher = dispatcher or create_default_dispatcher()
        self.queue = queue or MemoryInstructionQueue()
        self.result_path = result_path or Path("./logs/mcp-results.jsonl")
        self.result_path.parent.mkdir(parents=True, exist_ok=True)
        self._stop = asyncio.Event()
        self._write_lock = asyncio.Lock()

    async def submit(self, instruction: MCPInstruction) -> None:
        await self.queue.put(instruction)

    async def shutdown(self) -> None:
        self._stop.set()

    async def _write_result(self, result: InstructionResult) -> None:
        payload = {
            "instruction_id": result.instruction_id,
            "status": result.status,
            "detail": result.detail,
            "produced_at": result.produced_at.isoformat(),
        }
        async with self._write_lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                self._append_json,
                payload,
            )

    def _append_json(self, payload: Dict[str, str]) -> None:
        with self.result_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")

    async def run(self) -> None:
        while not self._stop.is_set():
            instruction = await self.queue.get()
            result = await self.dispatcher.dispatch(instruction)
            await self._write_result(result)

    def register_handler(self, action: str, handler: ActionHandler) -> None:
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
