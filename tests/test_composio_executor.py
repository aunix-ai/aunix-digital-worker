from aunix.composio.executor import _interpolate_value
from aunix.models import Finding


def test_interpolate_finding_fields():
    finding = Finding(
        agent_id=1,
        run_id=1,
        dedupe_key="k",
        severity="high",
        summary="Stale deal",
        recommendation="Follow up",
        source_ref="Deal #1",
        details={"row": {"hubspot_id": "99", "deal_size": 50000}},
    )
    out = _interpolate_value(
        {"note": "{{finding.summary}}", "deal_id": "{{finding.hubspot_id}}"},
        finding,
    )
    assert out == {"note": "Stale deal", "deal_id": "99"}
