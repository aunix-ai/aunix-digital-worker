"""LLM seam. AnthropicLlm is the production implementation (official SDK,
structured outputs via messages.parse). FakeLlm drives offline tests. An
agentu-backed implementation can satisfy the same protocol when L3+ execution
agents need a sandboxed runtime."""
from typing import Protocol, TypeVar

import anthropic
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LlmError(Exception):
    pass


class LlmClient(Protocol):
    def parse(self, *, system: str, prompt: str, schema: type[T]) -> T: ...


class AnthropicLlm:
    def __init__(self, model: str = "claude-opus-4-8", client: anthropic.Anthropic | None = None):
        self.model = model
        self.client = client or anthropic.Anthropic()

    def parse(self, *, system: str, prompt: str, schema: type[T]) -> T:
        try:
            response = self.client.messages.parse(
                model=self.model,
                max_tokens=16000,
                thinking={"type": "adaptive"},
                system=system,
                messages=[{"role": "user", "content": prompt}],
                output_format=schema,
            )
        except anthropic.APIError as exc:
            raise LlmError(str(exc)) from exc
        if response.parsed_output is None:
            raise LlmError(f"no structured output (stop_reason={response.stop_reason})")
        return response.parsed_output


class FakeLlm:
    """Queue of pre-baked outputs; an Exception in the queue is raised instead."""

    def __init__(self, outputs: list):
        self.outputs = list(outputs)
        self.prompts: list[str] = []

    def parse(self, *, system: str, prompt: str, schema: type[T]) -> T:
        self.prompts.append(prompt)
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return out
