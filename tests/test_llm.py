import pytest
from pydantic import BaseModel

from aunix.llm import FakeLlm, LlmError


class Out(BaseModel):
    answer: str


def test_fake_llm_returns_queued_outputs_and_records_prompts():
    fake = FakeLlm([Out(answer="a"), Out(answer="b")])
    assert fake.parse(system="s", prompt="p1", schema=Out).answer == "a"
    assert fake.parse(system="s", prompt="p2", schema=Out).answer == "b"
    assert fake.prompts == ["p1", "p2"]


def test_fake_llm_raises_queued_exceptions():
    fake = FakeLlm([LlmError("boom"), Out(answer="ok")])
    with pytest.raises(LlmError):
        fake.parse(system="s", prompt="p", schema=Out)
    assert fake.parse(system="s", prompt="p", schema=Out).answer == "ok"


def test_anthropic_api_errors_are_wrapped(monkeypatch):
    import httpx
    import anthropic

    from aunix.llm import AnthropicLlm

    class BoomMessages:
        def parse(self, **kwargs):
            raise anthropic.APIConnectionError(request=httpx.Request("GET", "http://x"))

    class BoomClient:
        messages = BoomMessages()

    llm = AnthropicLlm(client=BoomClient())
    with pytest.raises(LlmError):
        llm.parse(system="s", prompt="p", schema=Out)
