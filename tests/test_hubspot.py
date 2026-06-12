import httpx

from aunix.connectors.hubspot import HubSpotConnector

PAGE_1 = {
    "results": [
        {"id": "1", "properties": {"dealname": "Acme Renewal", "amount": "2500000",
                                   "dealstage": "negotiation", "hs_lastmodifieddate": "2026-06-10T08:00:00Z"}},
        {"id": "2", "properties": {"dealname": "Globex Expansion", "amount": None,
                                   "dealstage": "proposal", "hs_lastmodifieddate": None}},
    ],
    "paging": {"next": {"after": "2"}},
}
PAGE_2 = {
    "results": [
        {"id": "3", "properties": {"dealname": "Hooli Platform", "amount": "3100000",
                                   "dealstage": "proposal", "hs_lastmodifieddate": "2026-06-11T08:00:00Z"}},
    ],
}


def mock_client():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-token"
        assert request.url.path == "/crm/v3/objects/deals"
        if request.url.params.get("after") == "2":
            return httpx.Response(200, json=PAGE_2)
        return httpx.Response(200, json=PAGE_1)

    return httpx.Client(base_url="https://api.hubapi.com", transport=httpx.MockTransport(handler),
                        headers={"Authorization": "Bearer test-token"})


def test_fetches_and_maps_all_pages():
    rows = HubSpotConnector(access_token="test-token", client=mock_client()).fetch()
    assert [r["lead"] for r in rows] == ["Acme Renewal", "Globex Expansion", "Hooli Platform"]
    assert rows[0]["deal_size"] == 2500000.0
    assert rows[1]["deal_size"] == 0.0  # missing amount maps to 0, not a crash
    assert rows[2]["hubspot_id"] == "3"


def test_http_error_propagates_for_runner_to_record():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "invalid token"})

    client = httpx.Client(base_url="https://api.hubapi.com", transport=httpx.MockTransport(handler))
    try:
        HubSpotConnector(access_token="bad", client=client).fetch()
        assert False, "expected HTTPStatusError"
    except httpx.HTTPStatusError as exc:
        assert exc.response.status_code == 401
