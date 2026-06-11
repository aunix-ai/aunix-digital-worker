from datetime import datetime, timezone

from aunix.conditions import Breach
from aunix.reasoning import RuleBasedReasoner
from aunix.spec import Condition, ConditionGroup
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


def test_any_mode_emits_one_finding_per_matched_condition():
    spec = make_spec()
    row = {"po_number": "PO-4567"}
    breach = Breach(
        matched=[
            Condition(field="delivery_date", operator="gt", value="expected_date"),
            Condition(field="last_tracking_update", operator="stale_hours", value=48),
        ]
    )
    insight = RuleBasedReasoner().reason(spec, [row], [(row, breach)])
    assert [f.dedupe_key for f in insight.findings] == [
        "PO-4567:delivery_date",
        "PO-4567:last_tracking_update",
    ]


def test_all_mode_emits_single_composite_finding():
    spec = make_spec(
        conditions=ConditionGroup(
            mode="all",
            conditions=[
                Condition(field="delay_hours", operator="gt", value=24),
                Condition(field="priority", operator="eq", value="high"),
            ],
        )
    )
    row = {"po_number": "PO-9999", "delay_hours": 30, "priority": "high"}
    breach = Breach(
        matched=[
            Condition(field="delay_hours", operator="gt", value=24),
            Condition(field="priority", operator="eq", value="high"),
        ]
    )
    insight = RuleBasedReasoner().reason(spec, [row], [(row, breach)])
    assert [f.dedupe_key for f in insight.findings] == ["PO-9999:all:delay_hours,priority"]


def test_non_numeric_rank_values_sort_last_without_crashing():
    spec = make_spec(
        task_type="analysis",
        conditions=None,
        data_sources=["csv"],
        record_key="lead",
        rank_by="deal_size",
        top_n=3,
    )
    rows = [
        {"lead": "A", "deal_size": "N/A"},
        {"lead": "B", "deal_size": 300.0},
        {"lead": "C", "deal_size": 200.0},
    ]
    insight = RuleBasedReasoner().reason(spec, rows, [])
    assert [f.details["row"]["lead"] for f in insight.findings] == ["B", "C", "A"]


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
