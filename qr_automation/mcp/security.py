from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional

from .models import InstructionSignature, MCPInstruction


class SignatureValidationError(Exception):
    """Ausnahme bei ungültiger Signatur."""


@dataclass(slots=True)
class SignatureValidator:
    """Validiert HMAC-Signaturen eingehender Instruktionen."""

    secrets: Dict[str, bytes]
    require_signature: bool = True

    def resolve_secret(self, key_id: str) -> Optional[bytes]:
        return self.secrets.get(key_id)

    def verify(self, instruction: MCPInstruction) -> bool:
        signature = instruction.signature
        if not signature:
            if self.require_signature:
                raise SignatureValidationError("Anweisung ohne Signatur")
            return False
        secret = self.resolve_secret(signature.key_id)
        if not secret:
            raise SignatureValidationError(f"Unbekannter Schlüssel: {signature.key_id}")
        try:
            valid = signature.verify(instruction.canonical_bytes(), secret)
        except ValueError as exc:  # Unsupported algorithm
            raise SignatureValidationError(str(exc)) from exc
        if not valid:
            raise SignatureValidationError("Signaturprüfung fehlgeschlagen")
        return True


@dataclass(slots=True)
class RolePolicy:
    """Definiert erlaubte Aktionen für Rollen."""

    allow_map: Dict[str, set[str]]

    def is_allowed(self, role: str, action: str) -> bool:
        allowed = self.allow_map.get(role)
        if not allowed:
            return False
        return "*" in allowed or action in allowed

    @classmethod
    def from_mapping(cls, mapping: Dict[str, Callable[[], set[str]] | set[str] | list[str]]) -> "RolePolicy":
        normalized: Dict[str, set[str]] = {}
        for role, actions in mapping.items():
            if callable(actions):
                allowed = set(actions())
            else:
                allowed = set(actions)
            normalized[role] = allowed
        return cls(allow_map=normalized)
