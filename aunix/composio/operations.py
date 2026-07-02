"""Composio API operations: connections, search, schema, execute, OAuth."""
from __future__ import annotations

from typing import Any

from aunix.composio.client import get_composio_client, get_session
from aunix.composio.constants import COMPOSIO_TOOLKITS, TOOLKIT_DISPLAY


def _model_to_dict(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return value


def list_toolkit_connections(user_id: str | None = None) -> list[dict]:
    session = get_session(user_id)
    result = session.toolkits(toolkits=list(COMPOSIO_TOOLKITS))
    items = getattr(result, "items", None) or []
    out: list[dict] = []
    for slug in COMPOSIO_TOOLKITS:
        meta = TOOLKIT_DISPLAY.get(slug, {"name": slug.title(), "logo": ""})
        item = next((i for i in items if getattr(i, "slug", None) == slug), None)
        connection = getattr(item, "connection", None) if item else None
        connected_account = getattr(connection, "connected_account", None) if connection else None
        is_active = bool(getattr(connection, "is_active", False)) if connection else False
        status = getattr(connected_account, "status", None) if connected_account else None
        if is_active and not status:
            status = "ACTIVE"
        if not status:
            status = "NOT_CONNECTED"
        out.append(
            {
                "slug": slug,
                "name": getattr(item, "name", None) or meta["name"],
                "logo": getattr(item, "logo", None) or meta["logo"],
                "is_connected": is_active,
                "status": status,
                "connected_account_id": getattr(connected_account, "id", None) if connected_account else None,
                "requires_auth_config": slug == "netsuite",
            }
        )
    return out


def search_tools(query: str, user_id: str | None = None, toolkits: list[str] | None = None) -> Any:
    session = get_session(user_id, toolkits=toolkits)
    return _model_to_dict(session.search(query=query))


def get_tool_schema(tool_slug: str, user_id: str | None = None) -> dict:
    composio = get_composio_client()
    from aunix.composio.client import get_composio_user_id

    uid = get_composio_user_id(user_id)
    tool = composio.client.tools.retrieve(tool_slug=tool_slug)
    tool_dict = _model_to_dict(tool)
    input_schema = tool_dict.get("input_parameters") or tool_dict.get("parameters")
    if input_schema is None:
        fn = tool_dict.get("function") or {}
        input_schema = fn.get("parameters")
    return {
        "slug": tool_dict.get("slug") or tool_dict.get("name") or tool_slug,
        "description": tool_dict.get("description"),
        "input_schema": input_schema,
        "output_schema": tool_dict.get("output_parameters") or tool_dict.get("response"),
        "raw": tool_dict,
    }


def execute_tool(
    tool_slug: str,
    arguments: dict[str, Any],
    *,
    user_id: str | None = None,
) -> Any:
    session = get_session(user_id)
    response = session.execute(tool_slug, arguments=arguments or {})
    return _model_to_dict(response)


def get_connect_link(
    toolkit: str,
    callback_url: str,
    *,
    user_id: str | None = None,
) -> dict[str, str]:
    session = get_session(user_id, toolkits=[toolkit])
    connection = session.authorize(toolkit, callback_url=callback_url)
    return {
        "redirect_url": getattr(connection, "redirect_url", "") or "",
        "connection_request_id": getattr(connection, "id", "") or "",
    }
