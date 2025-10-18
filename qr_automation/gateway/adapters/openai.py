from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, Optional, TYPE_CHECKING

import httpx

from ...chat.models import ChatMessage
from ..base import AgentAdapter, AdapterDispatchError

if TYPE_CHECKING:  # pragma: no cover
    from ..config import AdapterConfig


class OpenAIAdapter(AgentAdapter):
    """Adapter für das OpenAI Chat Completions API."""

    def __init__(self, name: str, config: Optional["AdapterConfig"] = None) -> None:
        super().__init__(name, config=config)
        options = config.options if config else {}
        self.model = options.get("model", "gpt-4o-mini")
        self.base_url = options.get("base_url", "https://api.openai.com/v1/chat/completions")
        self.timeout = float(options.get("timeout", 30.0))
        self.max_tokens = options.get("max_tokens")
        self.temperature = options.get("temperature", 0.2)
        self.api_key_env = (
            (config.auth.environment_variable if config and config.auth else None)
            or options.get("api_key_env")
            or "OPENAI_API_KEY"
        )
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def protocols(self) -> set[str]:
        return {"REST", "OpenAI"}

    async def start(self) -> None:
        await super().start()
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
        await super().stop()

    def cache_key(self, message: ChatMessage) -> Optional[str]:
        payload = {
            "model": self.model,
            "content": message.content,
            "metadata": message.metadata,
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        return f"openai:{digest}"

    async def dispatch(self, message: ChatMessage) -> Dict[str, Any] | None:
        if self._client is None:
            raise AdapterDispatchError("OpenAIAdapter wurde nicht gestartet")
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise AdapterDispatchError(
                "OPENAI-API-Schlüssel nicht verfügbar; bitte Umgebungsvariable setzen"
            )
        request_payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": message.content},
            ],
            "temperature": self.temperature,
        }
        if self.max_tokens:
            request_payload["max_tokens"] = self.max_tokens
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        response = await self._client.post(self.base_url, headers=headers, json=request_payload)
        if response.status_code >= 400:
            raise AdapterDispatchError(
                f"OpenAI-API-Fehler {response.status_code}: {response.text}"
            )
        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            return None
        message_payload = choices[0].get("message", {})
        return {
            "type": "openai_chat_completion",
            "adapter": self.name,
            "model": self.model,
            "content": message_payload.get("content", ""),
            "usage": data.get("usage", {}),
        }


__all__ = ["OpenAIAdapter"]
