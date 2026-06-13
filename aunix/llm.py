"""LLM seam. OpenAiLlm is the production implementation (official SDK, structured
outputs via the Responses API). AnthropicLlm is a drop-in alternate. FakeLlm
drives offline tests — it is provider-agnostic, so the test suite never touches a
live API regardless of which implementation is wired."""
from typing import Protocol, TypeVar

import anthropic
import openai
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LlmError(Exception):
    pass


class LlmClient(Protocol):
    def parse(self, *, system: str, prompt: str, schema: type[T]) -> T: ...


class OpenAiLlm:
    """Production LLM via OpenAI's Responses API. Credentials resolve through the
    SDK's own chain (OPENAI_API_KEY); the model comes from settings (OPENAI_MODEL)."""

    def __init__(self, model: str = "gpt-5.1", client: "openai.OpenAI | None" = None):
        self.model = model
        self._client = client  # constructed lazily so building this (and Runtime) needs no key

    @property
    def client(self) -> "openai.OpenAI":
        if self._client is None:
            self._client = openai.OpenAI()
        return self._client

    def parse(self, *, system: str, prompt: str, schema: type[T]) -> T:
        try:
            response = self.client.responses.parse(
                model=self.model,
                instructions=system,
                input=prompt,
                text_format=schema,
            )
        except openai.APIError as exc:
            raise LlmError(str(exc)) from exc
        if response.output_parsed is None:
            raise LlmError(f"no structured output (status={response.status})")
        return response.output_parsed


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
