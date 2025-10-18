from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass(slots=True)
class MCPInstruction:
    """Repräsentiert eine MCP-konforme Steueranweisung."""

    id: str
    action: str
    payload: Dict[str, Any]
    issued_at: datetime
    source: Optional[str] = None

    @classmethod
    def from_payload(cls, data: Dict[str, Any]) -> "MCPInstruction":
        return cls(
            id=data["id"],
            action=data["action"],
            payload=data.get("payload", {}),
            issued_at=datetime.fromisoformat(data.get("issued_at") or datetime.now(tz=timezone.utc).isoformat()),
            source=data.get("source"),
        )


@dataclass(slots=True)
class InstructionResult:
    instruction_id: str
    status: str
    detail: str
    produced_at: datetime
