from datetime import datetime, timezone

from aunix.conditions import Breach
from aunix.reasoning import RuleBasedReasoner
from aunix.spec import Condition
from aunix.testing import make_spec

NOW = datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc)


def test_monitoring_breaches_become_findings():
    spec = make_spec()
    row = {"po_number": "PO-4567", "supplier": "Acme", "last_tracking_update": NOW}
    breach = Breach(matched=[Condition(field="delivery_date", operator="gt", value="expected_date")])
    insight = RuleBasedReasoner().reason(spec, [row], [(row, breach)])
    assert len(insight.findings) == 1
    f = insight.findings[0]
    assert f.dedupe_key == "PO-4567:delivery_date"
    assert "PO-4567" in f.summary
    assert f.source_ref == "simship://PO-4567"
    assert f.details["row"]["last_tracking_update"] == NOW.isoformat()  # JSON-safe


def test_analysis_ranks_top_n():
    spec = make_spec(
        task_type="analysis",
        conditions=None,
        data_sources=["csv"],
        record_key="lead",
        rank_by="deal_size",
        top_n=2,
    )
    rows = [
        {"lead": "A", "deal_size": 100.0},
        {"lead": "B", "deal_size": 300.0},
        {"lead": "C", "deal_size": 200.0},
    ]
    insight = RuleBasedReasoner().reason(spec, rows, [])
    assert [f.details["row"]["lead"] for f in insight.findings] == ["B", "C"]
    assert insight.findings[0].dedupe_key == "rank-1:B"
