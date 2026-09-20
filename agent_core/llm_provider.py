"""LLMProvider — the interface every LLM backend (Gemini/Claude/Groq) implements.

agent-core's agent loop only ever calls LLMProvider.complete(). It never
imports a provider SDK directly, so swapping providers (or adding a new
one) never touches the agent loop.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .messages import LLMResponse, Message, ToolSpec


class LLMProviderError(Exception):
    """Raised by an adapter when the underlying API call fails.

    Adapters should wrap provider-SDK exceptions in this (via `raise ... from e`)
    so agent-core can catch one exception type regardless of provider.
    """


class LLMProvider(ABC):
    """Provider-abstracted BYOK LLM interface."""

    @abstractmethod
    def complete(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        *,
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Send messages (+ optional tool specs) to the model, get one response back.

        Implementations must:
        - Translate `messages`/`tools`/`system` into their provider's wire format.
        - Translate the provider's response back into an `LLMResponse`.
        - Raise `LLMProviderError` (chained from the original exception) on failure —
          never let a provider-SDK-specific exception escape.
        """
        raise NotImplementedError
