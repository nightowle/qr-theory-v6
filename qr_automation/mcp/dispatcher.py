from __future__ import annotations

import abc
import asyncio
import platform
import subprocess
from datetime import datetime, timezone
from typing import Dict

from .models import InstructionResult, MCPInstruction


class ActionHandler(abc.ABC):
    """Basisklasse für ausführbare MCP-Aktionen."""

    name: str

    def __init__(self, name: str) -> None:
        self.name = name

    @abc.abstractmethod
    async def run(self, instruction: MCPInstruction) -> InstructionResult:
        raise NotImplementedError


class LoggingHandler(ActionHandler):
    def __init__(self, name: str) -> None:
        super().__init__(name)

    async def run(self, instruction: MCPInstruction) -> InstructionResult:
        return InstructionResult(
            instruction_id=instruction.id,
            status="logged",
            detail=f"{self.name} hat die Anweisung entgegengenommen",
            produced_at=datetime.now(tz=timezone.utc),
        )


class PowerShellHandler(ActionHandler):
    """Führt PowerShell-Skripte aus, sofern verfügbar."""

    async def run(self, instruction: MCPInstruction) -> InstructionResult:
        if platform.system() != "Windows":
            return InstructionResult(
                instruction_id=instruction.id,
                status="skipped",
                detail="PowerShell nur auf Windows verfügbar",
                produced_at=datetime.now(tz=timezone.utc),
            )
        script = instruction.payload.get("script")
        if not script:
            return InstructionResult(
                instruction_id=instruction.id,
                status="failed",
                detail="PowerShell-Anweisung ohne Skript",
                produced_at=datetime.now(tz=timezone.utc),
            )
        completed = await asyncio.to_thread(
            subprocess.run,
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
        )
        status = "ok" if completed.returncode == 0 else "failed"
        detail = completed.stdout if completed.stdout else completed.stderr
        return InstructionResult(
            instruction_id=instruction.id,
            status=status,
            detail=detail.strip(),
            produced_at=datetime.now(tz=timezone.utc),
        )


class BrowserAutomationHandler(ActionHandler):
    """Stub für Browser-Automation; protokolliert Ziel-URL."""

    async def run(self, instruction: MCPInstruction) -> InstructionResult:
        url = instruction.payload.get("url")
        if not url:
            detail = "Keine URL in Browser-Anweisung"
            status = "failed"
        else:
            detail = f"Würde Browser öffnen: {url}"
            status = "ok"
        return InstructionResult(
            instruction_id=instruction.id,
            status=status,
            detail=detail,
            produced_at=datetime.now(tz=timezone.utc),
        )


class InstructionDispatcher:
    """Zentrale Registrierungs- und Ausführungsschicht."""

    def __init__(self) -> None:
        self._handlers: Dict[str, ActionHandler] = {}

    def register(self, action: str, handler: ActionHandler) -> None:
        self._handlers[action] = handler

    def unregister(self, action: str) -> None:
        self._handlers.pop(action, None)

    async def dispatch(self, instruction: MCPInstruction) -> InstructionResult:
        handler = self._handlers.get(instruction.action)
        if not handler:
            return InstructionResult(
                instruction_id=instruction.id,
                status="unhandled",
                detail=f"Keine Aktion für '{instruction.action}' registriert",
                produced_at=datetime.now(tz=timezone.utc),
            )
        return await handler.run(instruction)


def create_default_dispatcher() -> InstructionDispatcher:
    dispatcher = InstructionDispatcher()
    dispatcher.register("log", LoggingHandler("logger"))
    dispatcher.register("browser.open", BrowserAutomationHandler("browser"))
    dispatcher.register("powershell.run", PowerShellHandler("powershell"))
    return dispatcher
