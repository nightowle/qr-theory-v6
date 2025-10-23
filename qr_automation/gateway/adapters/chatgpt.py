from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from .openai import OpenAIAdapter

if TYPE_CHECKING:  # pragma: no cover - nur für Typprüfungen relevant
    from ..config import AdapterConfig


class ChatGPTAdapter(OpenAIAdapter):
    """Spezialisierter Adapter für die ChatGPT-API (OpenAI Chat Completions)."""

    def __init__(self, name: str, config: Optional["AdapterConfig"] = None) -> None:
        super().__init__(name, config=config)
        if not getattr(self, "model", None):
            self.model = "gpt-4o-mini"

    @property
    def protocols(self) -> set[str]:
        return super().protocols | {"ChatGPT"}


__all__ = ["ChatGPTAdapter"]
