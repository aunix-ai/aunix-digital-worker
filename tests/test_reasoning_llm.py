from datetime import datetime, timezone

from aunix.conditions import Breach
from aunix.llm import FakeLlm, LlmError
from aunix.reasoning_llm import Enrichment, EnrichedFinding, LlmReasoner
from aunix.spec import Condition
from aunix.testing import make_spec

NOW = datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc)


def breach_input():
    spec = make_spec()
    row = {"po_number": "PO-4567", "supplier": "Acme", "delivery_date": "2026-06-23",
           "expected_date": "2026-06-21"}
    breach = Breach(matched=[Condition(field="delivery_date", operator="gt", value="expected_date")])
    return spec, [row], [(row, breach)]


def test_llm_rewrites_narrative_but_keys_stay_deterministic():
    spec, rows, breaches = breach_input()
    fake = FakeLlm([Enrichment(findings=[EnrichedFinding(
        dedupe_key="PO-4567:delivery_date",
        summary="PO-4567 delayed 2 days due to customs hold; revised ETA Jun 23",
        recommendation="Contact Acme to confirm the revised ETA.",
    )])])
    insight = LlmReasoner(fake).reason(spec, rows, breaches)
    assert len(insight.findings) == 1
    f = insight.findings[0]
    assert f.dedupe_key == "PO-4567:delivery_date"  # deterministic, not LLM-chosen
    assert "customs hold" in f.summary
    assert "Acme" in f.recommendation


def test_llm_failure_falls_back_to_rule_based_findings():
    spec, rows, breaches = breach_input()
    insight = LlmReasoner(FakeLlm([LlmError("api down")])).reason(spec, rows, breaches)
    assert len(insight.findings) == 1
    assert insight.findings[0].dedupe_key == "PO-4567:delivery_date"
    assert "condition breach" in insight.findings[0].summary  # rule-based template


def test_unknown_keys_from_llm_are_ignored():
    spec, rows, breaches = breach_input()
    fake = FakeLlm([Enrichment(findings=[EnrichedFinding(
        dedupe_key="PO-9999:invented", summary="x", recommendation="y")])])
    insight = LlmReasoner(fake).reason(spec, rows, breaches)
    assert insight.findings[0].dedupe_key == "PO-4567:delivery_date"
    assert "condition breach" in insight.findings[0].summary  # untouched


def test_no_findings_skips_llm_call():
    spec = make_spec()
    fake = FakeLlm([])
    insight = LlmReasoner(fake).reason(spec, [], [])
    assert insight.findings == []
    assert fake.prompts == []
