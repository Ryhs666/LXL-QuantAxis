"""Provider-neutral LLM completion contracts."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CompletionResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: Decimal = Decimal("0")


class LLMPort(Protocol):
    def complete(self, *, prompt: str) -> CompletionResponse: ...
