from __future__ import annotations

import abc
from typing import Any, Dict, Optional, Set, TYPE_CHECKING

from ..chat.models import ChatMessage


if TYPE_CHECKING:  # pragma: no cover - nur für Typprüfung relevant
    from .config import AdapterConfig


class AdapterDispatchError(RuntimeError):
    """Laufzeitfehler bei der Kommunikation mit einem Adapter."""


class AdapterLifecycleError(RuntimeError):
    """Fehler während Start- oder Stop-Prozeduren eines Adapters."""


class AgentAdapter(abc.ABC):
    """Abstrakte Basis für KI-Konnektoren mit definierter Lebensdauer."""

    name: str

    def __init__(self, name: str, config: "AdapterConfig | None" = None) -> None:
        self.name = name
        self.config = config
        self._started = False

    @property
    def protocols(self) -> Set[str]:
        """Protokolle, die der Adapter unterstützt (z. B. REST, WebSocket, gRPC)."""

        if self.config and self.config.protocols:
            return set(self.config.protocols)
        return {"REST"}

    def supports_protocol(self, protocol: str) -> bool:
        return protocol.upper() in {p.upper() for p in self.protocols}

    async def start(self) -> None:
        """Initialisiert Ressourcen des Adapters."""

        self._started = True

    async def stop(self) -> None:
        """Gibt Ressourcen wieder frei."""

        self._started = False

    async def health_check(self) -> bool:
        """Validiert den aktuellen Adapterzustand."""

        return self._started

    def cache_key(self, message: ChatMessage) -> Optional[str]:
        """Optionaler Schlüssel zur Wiederverwendung von Antworten."""

        return None

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
