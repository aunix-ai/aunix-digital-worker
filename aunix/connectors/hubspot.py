"""HubSpot CRM connector (private-app access token). Fetches deals and maps
them to the row shape analysis agents rank (lead / deal_size / stage). The
full OAuth2 install flow is deferred; the token comes from settings.

Connector errors propagate: the runner records them as a failed run."""
import httpx

PROPERTIES = "dealname,amount,dealstage,hs_lastmodifieddate"


class HubSpotConnector:
    source_id = "hubspot"

    def __init__(self, access_token: str, client: httpx.Client | None = None):
        self.client = client or httpx.Client(
            base_url="https://api.hubapi.com",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )

    def fetch(self) -> list[dict]:
        rows: list[dict] = []
        after: str | None = None
        while True:
            params: dict = {"limit": 100, "properties": PROPERTIES}
            if after:
                params["after"] = after
            resp = self.client.get("/crm/v3/objects/deals", params=params)
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("results", []):
                props = item.get("properties") or {}
                rows.append(
                    {
                        "lead": props.get("dealname"),
                        "deal_size": float(props["amount"]) if props.get("amount") else 0.0,
                        "stage": props.get("dealstage"),
                        "last_modified": props.get("hs_lastmodifieddate"),
                        "hubspot_id": item.get("id"),
                    }
                )
            after = ((data.get("paging") or {}).get("next") or {}).get("after")
            if not after:
                return rows
