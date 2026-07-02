from datetime import datetime, timezone

from aunix.composio.connector import ComposioConnector
from aunix.composio.interpolate import interpolate_runtime_arguments
from aunix.composio.normalize import normalize_rows
from aunix.spec import ComposioSource


def test_interpolate_runtime_date_placeholders():
    now = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)
    out = interpolate_runtime_arguments(
        {
            "start": "{{now_minus_5_days_iso}}",
            "end": "{{now_iso}}",
        },
        now=now,
    )
    assert out["end"] == "2026-07-02T12:00:00Z"
    assert out["start"].startswith("2026-06-27T12:00:00")


def test_expand_salesforce_updated_ids():
    rows = normalize_rows(
        {"data": {"ids": ["006ABC", "006DEF"], "latestDateCovered": "2026-07-01T20:37:00.000+0000"}}
    )
    assert rows == [
        {"Id": "006ABC", "latestDateCovered": "2026-07-01T20:37:00.000+0000"},
        {"Id": "006DEF", "latestDateCovered": "2026-07-01T20:37:00.000+0000"},
    ]


def test_expand_skips_validation_error_rows():
    rows = normalize_rows({"data": {"message": "missing fields", "status_code": 400}})
    assert rows == []


def test_expand_skips_http_error_rows():
    rows = normalize_rows({"data": {"http_error": "400", "message": "bad date"}})
    assert rows == []


def test_connector_interpolates_before_execute(monkeypatch):
    source = ComposioSource(
        toolkit="salesforce",
        tool_slug="SALESFORCE_GET_S_OBJECTS_UPDATED",
        arguments={"sobject": "Opportunity", "start": "{{now_minus_5_days_iso}}", "end": "{{now_iso}}"},
        record_key="Id",
    )
    captured: dict = {}

    def fake_execute(slug, arguments, user_id=None):
        captured["arguments"] = arguments
        return {"data": {"ids": ["006XYZ"], "latestDateCovered": "2026-07-01T00:00:00Z"}}

    monkeypatch.setattr("aunix.composio.connector.execute_tool", fake_execute)
    now = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)
    rows = ComposioConnector(source, now=now).fetch()
    assert "{{" not in captured["arguments"]["start"]
    assert rows == [{"Id": "006XYZ", "latestDateCovered": "2026-07-01T00:00:00Z"}]
