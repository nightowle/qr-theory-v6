from __future__ import annotations

import abc
from typing import Any, Dict

from ..chat.models import ChatMessage


class AgentAdapter(abc.ABC):
    """Abstrakte Basis für KI-Konnektoren."""

    name: str

    def __init__(self, name: str) -> None:
        self.name = name

    @abc.abstractmethod
    async def dispatch(self, message: ChatMessage) -> Dict[str, Any] | None:
        """Verarbeitet eine Chat-Nachricht und gibt optional eine Antwort zurück."""


class EchoAdapter(AgentAdapter):
    """Triviale Referenz-Implementierung zur Systemvalidierung."""

    async def dispatch(self, message: ChatMessage) -> Dict[str, Any] | None:
        return {
            "type": "echo",
            "original_message_id": message.id,
            "content": f"Echo: {message.content}",
        }
