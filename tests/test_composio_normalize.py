from aunix.composio.normalize import normalize_rows


def test_normalize_hubspot_deals_default_mapping():
    payload = {
        "results": [
            {
                "id": "123",
                "properties": {
                    "dealname": "Acme",
                    "amount": "50000",
                    "dealstage": "negotiation",
                    "hs_lastmodifieddate": "2026-01-01T00:00:00Z",
                },
            }
        ]
    }
    rows = normalize_rows(payload)
    assert len(rows) == 1
    assert rows[0]["lead"] == "Acme"
    assert rows[0]["deal_size"] == 50000.0
    assert rows[0]["hubspot_id"] == "123"


def test_normalize_custom_row_mapping():
    payload = {"items": [{"name": "Beta", "value": 9}]}
    rows = normalize_rows(payload, {"label": "name", "score": "value"})
    assert rows == [{"label": "Beta", "score": 9}]
