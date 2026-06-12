from pydantic import ValidationError

from aunix.compiler import ClarifyingQuestion, CompiledIntent, compile_intent
from aunix.llm import FakeLlm
from aunix.testing import make_spec


def test_clear_intent_compiles_to_spec():
    fake = FakeLlm([CompiledIntent(spec=make_spec())])
    result = compile_intent(fake, "Watch my POs and alert me on delays")
    assert result.spec is not None
    assert result.spec.task_type == "monitoring"
    assert result.questions == []


def test_ambiguous_intent_returns_structured_clarifying_questions():
    fake = FakeLlm([CompiledIntent(clarifying_questions=[
        ClarifyingQuestion(text="Which data source holds your POs?",
                           choices=["simship", "hubspot", "csv"])
    ])])
    result = compile_intent(fake, "watch my stuff")
    assert result.spec is None
    assert result.questions[0].text == "Which data source holds your POs?"
    assert result.questions[0].choices == ["simship", "hubspot", "csv"]
    assert result.questions[0].kind == "text"


def test_validation_failure_retries_once_with_error_feedback():
    err = None
    try:
        make_spec(top_n=0)
    except ValidationError as exc:
        err = exc
    fake = FakeLlm([err, CompiledIntent(spec=make_spec())])
    result = compile_intent(fake, "rank my leads")
    assert result.spec is not None
    assert len(fake.prompts) == 2
    assert "failed validation" in fake.prompts[1]


def test_spec_with_questions_resolves_to_questions_win():
    q = ClarifyingQuestion(text="What schedule?")
    intent = CompiledIntent(spec=make_spec(), clarifying_questions=[q])
    assert intent.spec is None
    fake = FakeLlm([CompiledIntent(spec=make_spec(), clarifying_questions=[q])])
    result = compile_intent(fake, "watch things")
    assert result.spec is None
    assert [x.text for x in result.questions] == ["What schedule?"]


def test_double_validation_failure_degrades_to_question():
    def err():
        try:
            make_spec(top_n=0)
        except ValidationError as exc:
            return exc
    fake = FakeLlm([err(), err()])
    result = compile_intent(fake, "rank my leads")
    assert result.spec is None
    assert len(result.questions) == 1


def test_llm_errors_are_not_retried():
    from aunix.llm import LlmError
    fake = FakeLlm([LlmError("api down")])
    try:
        compile_intent(fake, "watch my POs")
        assert False, "expected LlmError to propagate"
    except LlmError:
        pass
    assert len(fake.prompts) == 1  # no retry on transport failures
