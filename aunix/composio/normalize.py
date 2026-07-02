"""Map Composio execute responses to flat row dicts for the agent pipeline."""
from __future__ import annotations

from typing import Any


def _unwrap_payload(result: Any) -> Any:
    if result is None:
        return []
    if isinstance(result, dict):
        if "data" in result:
            return result["data"]
        if "results" in result:
            return result["results"]
        if "items" in result:
            return result["items"]
        if "records" in result:
            return result["records"]
    return result


def _get_path(obj: Any, path: str) -> Any:
    current = obj
    for part in path.split("."):
        if current is None:
            return None
        if part.endswith("]"):
            key, _, rest = part.partition("[")
            if not isinstance(current, dict):
                return None
            current = current.get(key)
            if rest == "]":
                continue
            if rest.endswith("]") and rest[:-1].isdigit():
                idx = int(rest[:-1])
                if isinstance(current, list) and 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
        elif isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            idx = int(part)
            current = current[idx] if 0 <= idx < len(current) else None
        else:
            return None
    return current


def _default_hubspot_deal_rows(payload: Any) -> list[dict]:
    rows: list[dict] = []
    items = _unwrap_payload(payload)
    if not isinstance(items, list):
        return rows
    for item in items:
        if not isinstance(item, dict):
            continue
        props = item.get("properties") if isinstance(item.get("properties"), dict) else {}
        amount = props.get("amount")
        rows.append(
            {
                "lead": props.get("dealname") or props.get("name"),
                "deal_size": float(amount) if amount not in (None, "") else 0.0,
                "stage": props.get("dealstage") or props.get("stage"),
                "last_modified": props.get("hs_lastmodifieddate") or props.get("lastmodifieddate"),
                "hubspot_id": item.get("id"),
            }
        )
    return rows


def _expand_salesforce_updated_rows(rows: list[dict]) -> list[dict]:
    """SALESFORCE_GET_S_OBJECTS_UPDATED returns {ids: [...]} — one row per Id."""
    expanded: list[dict] = []
    for row in rows:
        if "http_error" in row or "errorCode" in row or row.get("status_code"):
            continue
        ids = row.get("ids")
        if isinstance(ids, list) and ids:
            for opp_id in ids:
                expanded.append({"Id": opp_id, "latestDateCovered": row.get("latestDateCovered")})
            continue
        expanded.append(row)
    return expanded


def normalize_rows(result: Any, row_mapping: dict[str, str] | None = None) -> list[dict]:
    """Convert a Composio tool result into agent row dicts."""
    payload = result
    if isinstance(result, dict) and "data" in result and len(result) <= 4:
        payload = result["data"]
    elif hasattr(result, "data"):
        payload = result.data

    if not row_mapping:
        default_rows = _default_hubspot_deal_rows(payload)
        if default_rows:
            return default_rows

    items = _unwrap_payload(payload)
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        return []

    rows: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if not row_mapping:
            rows.append(item)
            continue
        row: dict[str, Any] = {}
        for target, source_path in row_mapping.items():
            row[target] = _get_path(item, source_path)
        rows.append(row)
    return _expand_salesforce_updated_rows(rows)
