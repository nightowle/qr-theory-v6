from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional, TYPE_CHECKING

import httpx

from ...chat.models import ChatMessage
from ..base import AgentAdapter, AdapterDispatchError

if TYPE_CHECKING:  # pragma: no cover
    from ..config import AdapterConfig


class LlamaCppAdapter(AgentAdapter):
    """Adapter für lokale llama.cpp HTTP-Server."""

    def __init__(self, name: str, config: Optional["AdapterConfig"] = None) -> None:
        super().__init__(name, config=config)
        options = config.options if config else {}
        self.base_url = options.get("base_url", "http://127.0.0.1:8080")
        self.endpoint = options.get("endpoint", "/completion")
        self.context_size = options.get("context_size", 4096)
        self.temperature = options.get("temperature", 0.1)
        self.top_p = options.get("top_p", 0.95)
        self.max_tokens = options.get("max_tokens", 512)
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def protocols(self) -> set[str]:
        return {"REST"}

    async def start(self) -> None:
        await super().start()
        self._client = httpx.AsyncClient(timeout=60.0)

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
        await super().stop()

    def cache_key(self, message: ChatMessage) -> Optional[str]:
        payload = {
            "content": message.content,
            "metadata": message.metadata,
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        return f"llama:{digest}"

    async def dispatch(self, message: ChatMessage) -> Dict[str, Any] | None:
        if self._client is None:
            raise AdapterDispatchError("LlamaCppAdapter wurde nicht gestartet")
        url = f"{self.base_url.rstrip('/')}{self.endpoint}"
        request_payload = {
            "prompt": message.content,
            "n_predict": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }
        response = await self._client.post(url, json=request_payload)
        if response.status_code >= 400:
            raise AdapterDispatchError(
                f"llama.cpp-API-Fehler {response.status_code}: {response.text}"
            )
        data = response.json()
        text = data.get("content") or data.get("choices", [{}])[0].get("text")
        if not text:
            return None
        return {
            "type": "llamacpp_completion",
            "adapter": self.name,
            "content": text,
        }


__all__ = ["LlamaCppAdapter"]
