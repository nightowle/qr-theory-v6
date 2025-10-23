from __future__ import annotations

import json
from typing import Any, Dict, Optional, TYPE_CHECKING

import httpx

from ...chat.models import ChatMessage
from ..base import AgentAdapter, AdapterDispatchError

if TYPE_CHECKING:  # pragma: no cover - nur für Typprüfungen relevant
    from ..config import AdapterConfig


class ZapierAdapter(AgentAdapter):
    """Adapter, der Chat-Nachrichten an einen Zapier Webhook sendet."""

    def __init__(self, name: str, config: Optional["AdapterConfig"] = None) -> None:
        super().__init__(name, config=config)
        options: Dict[str, Any] = {}
        if config:
            options = dict(config.options)
        self.webhook_url: Optional[str] = options.get("webhook_url")
        self.timeout: float = float(options.get("timeout", 30.0))
        client_options = options.get("client_options", {})
        if not isinstance(client_options, dict):
            raise TypeError("client_options muss ein Dictionary sein")
        self._client_options = client_options
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def protocols(self) -> set[str]:
        return {"REST", "Zapier"}

    async def start(self) -> None:
        await super().start()
        self._client = httpx.AsyncClient(timeout=self.timeout, **self._client_options)

    async def stop(self) -> None:
        if self._client is not None:
            await self._client.aclose()
        await super().stop()

    async def dispatch(self, message: ChatMessage) -> Dict[str, Any] | None:
        if self._client is None:
            raise AdapterDispatchError("ZapierAdapter wurde nicht gestartet")
        if not self.webhook_url:
            raise AdapterDispatchError("Zapier Webhook-URL nicht konfiguriert")
        payload = {
            "message_id": message.id,
            "room": message.room,
            "sender_id": message.sender_id,
            "sender_type": message.sender_type,
            "content": message.content,
            "metadata": message.metadata,
            "created_at": message.created_at.isoformat(),
        }
        response = await self._client.post(self.webhook_url, json=payload)
        if response.status_code >= 400:
            raise AdapterDispatchError(
                f"Zapier Webhook antwortete mit Status {response.status_code}: {response.text}"
            )
        try:
            data = response.json()
        except json.JSONDecodeError:
            data = {"text": response.text}
        return {
            "type": "zapier_webhook",
            "adapter": self.name,
            "status_code": response.status_code,
            "response": data,
        }


__all__ = ["ZapierAdapter"]
