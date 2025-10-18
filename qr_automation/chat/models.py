from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(slots=True)
class Agent:
    """Repräsentiert einen menschlichen oder KI-Agenten innerhalb eines Chat-Raumes."""

    id: str
    name: str
    type: str
    metadata: Dict[str, Any]
    created_at: datetime


@dataclass(slots=True)
class ChatMessage:
    """Persistenter Nachrichten-Datensatz inklusive Audit-Metadaten."""

    id: str
    room: str
    sender_id: str
    sender_type: str
    content: str
    metadata: Dict[str, Any]
    created_at: datetime
    target_adapter: Optional[str] = None
