from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass(slots=True)
class InstructionSignature:
    """Digitale Signatur für eine MCP-Anweisung."""

    algorithm: str
    key_id: str
    value: str

    def verify(self, payload: bytes, secret: bytes) -> bool:
        import hmac
        import hashlib

        if self.algorithm.lower() not in {"hs256", "hmac-sha256"}:
            raise ValueError(f"Nicht unterstützter Algorithmus: {self.algorithm}")
        digest = hmac.new(secret, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, self.value)


@dataclass(slots=True)
class MCPInstruction:
    """Repräsentiert eine MCP-konforme Steueranweisung."""

    id: str
    action: str
    payload: Dict[str, Any]
    issued_at: datetime
    source: Optional[str] = None
    role: str = "system"
    correlation_id: Optional[str] = None
    dry_run: bool = False
    timeout: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    signature: Optional[InstructionSignature] = None

    @classmethod
    def from_payload(cls, data: Dict[str, Any]) -> "MCPInstruction":
        signature: Optional[InstructionSignature] = None
        signature_data = data.get("signature")
        if signature_data:
            signature = InstructionSignature(
                algorithm=signature_data["algorithm"],
                key_id=signature_data["key_id"],
                value=signature_data["value"],
            )
        issued_raw = data.get("issued_at")
        issued_at = (
            datetime.fromisoformat(issued_raw)
            if isinstance(issued_raw, str)
            else datetime.now(tz=timezone.utc)
        )
        return cls(
            id=data["id"],
            action=data["action"],
            payload=data.get("payload", {}),
            issued_at=issued_at,
            source=data.get("source"),
            role=data.get("role", "system"),
            correlation_id=data.get("correlation_id"),
            dry_run=bool(data.get("dry_run", False)),
            timeout=data.get("timeout"),
            metadata=data.get("metadata", {}),
            signature=signature,
        )

    def canonical_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "payload": self.payload,
            "issued_at": self.issued_at.replace(tzinfo=timezone.utc).isoformat(),
            "source": self.source,
            "role": self.role,
            "correlation_id": self.correlation_id,
            "dry_run": self.dry_run,
            "timeout": self.timeout,
            "metadata": self.metadata,
        }

    def canonical_bytes(self) -> bytes:
        return json.dumps(self.canonical_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass(slots=True)
class InstructionResult:
    instruction_id: str
    status: str
    detail: str
    produced_at: datetime
    duration_ms: Optional[int] = None
    audit_reference: Optional[str] = None


@dataclass(slots=True)
class MCPMessage:
    """Generische Status- oder Ereignisnachricht."""

    id: str
    kind: str
    payload: Dict[str, Any]
    occurred_at: datetime
    correlation_id: Optional[str] = None
    role: Optional[str] = None
    level: str = "info"


@dataclass(slots=True)
class CommandReceipt:
    """Quittung über den Eingang einer Instruktion."""

    instruction_id: str
    received_at: datetime
    status: str
    detail: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AuditRecord:
    """Audit-Datensatz für Nachvollziehbarkeit."""

    instruction_id: str
    action: str
    role: str
    issued_at: datetime
    started_at: datetime
    completed_at: datetime
    status: str
    detail: str
    dry_run: bool
    signature_valid: bool
    receipt_status: str
