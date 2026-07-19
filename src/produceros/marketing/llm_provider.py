"""Optional local-LLM provider interface (spec section 13).

This is intentionally a disabled stub. ProducerOS's marketing workspace is
fully functional using only the deterministic templates in
``produceros.marketing.templates`` -- nothing in the product depends on
this interface. It exists so that, in the future, a user who has their own
local model running (e.g. via a local inference server on localhost) could
plug it in explicitly. It is never enabled by default, never reaches the
network, and this build ships no implementation that calls out anywhere.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LocalLLMProvider(ABC):
    """Interface a future local-model integration would implement.

    No concrete implementation ships in this build. Calling
    ``get_active_provider()`` always returns ``None`` today.
    """

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def suggest_draft_variation(self, draft_type: str, context: dict, base_text: str) -> str:
        """Return an alternative phrasing of ``base_text``. Implementations
        must not introduce facts absent from ``context`` (numbers, quotes,
        credits, achievements)."""


def get_active_provider() -> LocalLLMProvider | None:
    """Always returns None in this build: no LLM provider is enabled."""
    return None
