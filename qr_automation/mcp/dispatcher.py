from __future__ import annotations

import abc
import asyncio
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Optional

from .models import InstructionResult, MCPInstruction
from .security import RolePolicy


class SandboxViolation(RuntimeError):
    """Signalisiert einen Verstoß gegen die Sandboxing-Regeln."""


class AuthorizationError(RuntimeError):
    """Unzureichende Berechtigung für eine Aktion."""


class UnknownActionError(RuntimeError):
    """Die Aktion ist nicht registriert."""


class ActionHandler(abc.ABC):
    """Basisklasse für ausführbare MCP-Aktionen."""

    name: str

    def __init__(
        self,
        name: str,
        allowed_roles: Iterable[str],
        *,
        default_timeout: float = 30.0,
        supports_dry_run: bool = True,
    ) -> None:
        self.name = name
        self.allowed_roles = set(allowed_roles)
        self.default_timeout = default_timeout
        self.supports_dry_run = supports_dry_run

    def authorize(self, role: str) -> bool:
        return "*" in self.allowed_roles or role in self.allowed_roles

    async def execute(self, instruction: MCPInstruction, *, dry_run: bool = False) -> InstructionResult:
        if dry_run:
            if not self.supports_dry_run:
                raise SandboxViolation(f"{self.name} unterstützt keinen Dry-Run")
            detail = self.describe_dry_run(instruction)
            return InstructionResult(
                instruction_id=instruction.id,
                status="dry-run",
                detail=detail,
                produced_at=datetime.now(tz=timezone.utc),
            )
        return await self.run(instruction)

    def describe_dry_run(self, instruction: MCPInstruction) -> str:
        return f"Würde Aktion '{instruction.action}' mit Payload {instruction.payload} ausführen"

    @abc.abstractmethod
    async def run(self, instruction: MCPInstruction) -> InstructionResult:
        raise NotImplementedError


class LoggingHandler(ActionHandler):
    def __init__(self, name: str, *, allowed_roles: Iterable[str] = ("*",)) -> None:
        super().__init__(name, allowed_roles, supports_dry_run=True, default_timeout=5.0)

    async def run(self, instruction: MCPInstruction) -> InstructionResult:
        return InstructionResult(
            instruction_id=instruction.id,
            status="logged",
            detail=f"{self.name} hat die Anweisung entgegengenommen",
            produced_at=datetime.now(tz=timezone.utc),
        )


class PowerShellHandler(ActionHandler):
    """Führt PowerShell-Skripte aus, sofern verfügbar."""

    def __init__(self, name: str, *, allowed_roles: Iterable[str], sandbox_blocklist: Optional[Iterable[str]] = None) -> None:
        super().__init__(name, allowed_roles, default_timeout=60.0, supports_dry_run=True)
        self.sandbox_blocklist = set(sandbox_blocklist or {"Remove-Item", "Format-Drive"})

    def describe_dry_run(self, instruction: MCPInstruction) -> str:
        script = instruction.payload.get("script", "<leer>")
        return f"PowerShell Dry-Run für Rolle {instruction.role}: {script}"

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
        for blocked in self.sandbox_blocklist:
            if blocked.lower() in script.lower():
                raise SandboxViolation(f"PowerShell-Befehl blockiert: {blocked}")
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
    """Playwright-gestützte Browser-Automation."""

    def __init__(
        self,
        name: str,
        *,
        allowed_roles: Iterable[str],
        headless: bool = True,
        download_dir: Optional[Path] = None,
    ) -> None:
        super().__init__(name, allowed_roles, default_timeout=120.0, supports_dry_run=True)
        self.headless = headless
        self.download_dir = download_dir

    def describe_dry_run(self, instruction: MCPInstruction) -> str:
        url = instruction.payload.get("url", "<keine>")
        steps = instruction.payload.get("steps", [])
        return f"Browser Dry-Run: {url} mit {len(steps)} Schritt(en)"

    async def run(self, instruction: MCPInstruction) -> InstructionResult:
        url = instruction.payload.get("url")
        if not url:
            return InstructionResult(
                instruction_id=instruction.id,
                status="failed",
                detail="Keine URL in Browser-Anweisung",
                produced_at=datetime.now(tz=timezone.utc),
            )
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return InstructionResult(
                instruction_id=instruction.id,
                status="skipped",
                detail="Playwright nicht installiert",
                produced_at=datetime.now(tz=timezone.utc),
            )

        steps = instruction.payload.get("steps", [])

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                accept_downloads=self.download_dir is not None,
                downloads_path=str(self.download_dir) if self.download_dir else None,
            )
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle")
            for step in steps:
                action = step.get("action")
                target = step.get("target")
                if action == "click" and target:
                    await page.click(target)
                elif action == "fill" and target:
                    value = step.get("value", "")
                    await page.fill(target, value)
            current_url = page.url
            await browser.close()
        return InstructionResult(
            instruction_id=instruction.id,
            status="ok",
            detail=f"Browser abgeschlossen, letzte URL: {current_url}",
            produced_at=datetime.now(tz=timezone.utc),
        )


class RegistryHandler(ActionHandler):
    """Greift kontrolliert auf die Windows-Registry zu."""

    def __init__(self, name: str, *, allowed_roles: Iterable[str], allowed_roots: Optional[Iterable[str]] = None) -> None:
        super().__init__(name, allowed_roles, default_timeout=10.0, supports_dry_run=True)
        self.allowed_roots = {root.upper() for root in (allowed_roots or ("HKCU", "HKLM"))}

    def describe_dry_run(self, instruction: MCPInstruction) -> str:
        return f"Registry Dry-Run: {instruction.payload.get('operation', 'query')} auf {instruction.payload.get('path')}"

    async def run(self, instruction: MCPInstruction) -> InstructionResult:
        if platform.system() != "Windows":
            return InstructionResult(
                instruction_id=instruction.id,
                status="skipped",
                detail="Registry-Zugriff nur auf Windows",
                produced_at=datetime.now(tz=timezone.utc),
            )
        operation = instruction.payload.get("operation", "query")
        path = instruction.payload.get("path")
        if not path:
            return InstructionResult(
                instruction_id=instruction.id,
                status="failed",
                detail="Registry-Pfad fehlt",
                produced_at=datetime.now(tz=timezone.utc),
            )
        root, _, subpath = path.partition("\\")
        if root.upper() not in self.allowed_roots:
            raise SandboxViolation(f"Registry-Root {root} nicht erlaubt")
        try:
            import winreg  # type: ignore
        except ImportError:
            return InstructionResult(
                instruction_id=instruction.id,
                status="skipped",
                detail="winreg nicht verfügbar",
                produced_at=datetime.now(tz=timezone.utc),
            )
        root_key = getattr(winreg, root.upper())
        if operation == "query":
            try:
                with winreg.OpenKey(root_key, subpath) as key:
                    values: Dict[str, str] = {}
                    index = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, index)
                        except OSError:
                            break
                        values[name] = str(value)
                        index += 1
            except FileNotFoundError:
                return InstructionResult(
                    instruction_id=instruction.id,
                    status="failed",
                    detail="Registry-Pfad nicht gefunden",
                    produced_at=datetime.now(tz=timezone.utc),
                )
            return InstructionResult(
                instruction_id=instruction.id,
                status="ok",
                detail=json.dumps(values, ensure_ascii=False),
                produced_at=datetime.now(tz=timezone.utc),
            )
        elif operation == "set":
            value_name = instruction.payload.get("value_name")
            value = instruction.payload.get("value")
            if value_name is None:
                raise SandboxViolation("value_name erforderlich für Registry set")
            with winreg.OpenKey(root_key, subpath, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, str(value))
            return InstructionResult(
                instruction_id=instruction.id,
                status="ok",
                detail=f"Registry {path} aktualisiert",
                produced_at=datetime.now(tz=timezone.utc),
            )
        else:
            raise SandboxViolation(f"Unsupported registry operation: {operation}")


class InstructionDispatcher:
    """Zentrale Registrierungs- und Ausführungsschicht."""

    def __init__(self, role_policy: Optional[RolePolicy] = None) -> None:
        self._handlers: Dict[str, ActionHandler] = {}
        self.role_policy = role_policy

    def register(self, action: str, handler: ActionHandler) -> None:
        self._handlers[action] = handler

    def unregister(self, action: str) -> None:
        self._handlers.pop(action, None)

    def get_handler(self, action: str) -> Optional[ActionHandler]:
        return self._handlers.get(action)

    def authorize(self, instruction: MCPInstruction) -> ActionHandler:
        handler = self.get_handler(instruction.action)
        if not handler:
            raise UnknownActionError(instruction.action)
        if self.role_policy and not self.role_policy.is_allowed(instruction.role, instruction.action):
            raise AuthorizationError(f"Rolle {instruction.role} darf Aktion {instruction.action} nicht ausführen")
        if not handler.authorize(instruction.role):
            raise AuthorizationError(f"Handler verweigert Rolle {instruction.role}")
        return handler


def create_default_dispatcher(role_policy: Optional[RolePolicy] = None) -> InstructionDispatcher:
    dispatcher = InstructionDispatcher(role_policy=role_policy)
    dispatcher.register("log", LoggingHandler("logger"))
    dispatcher.register("browser.open", BrowserAutomationHandler("browser", allowed_roles={"automation", "admin"}))
    dispatcher.register("powershell.run", PowerShellHandler("powershell", allowed_roles={"ops", "admin"}))
    dispatcher.register(
        "system.registry",
        RegistryHandler("registry", allowed_roles={"ops", "admin"}, allowed_roots=("HKCU", "HKLM")),
    )
    return dispatcher
