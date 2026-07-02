"""Toolkit slugs enabled for Digital Worker Composio sessions."""

from typing import Literal

ComposioToolkitSlug = Literal["hubspot", "salesforce", "quickbooks", "netsuite", "gmail"]

COMPOSIO_TOOLKITS: tuple[ComposioToolkitSlug, ...] = (
    "hubspot",
    "salesforce",
    "quickbooks",
    "netsuite",
    "gmail",
)

TOOLKIT_DISPLAY: dict[str, dict[str, str]] = {
    "hubspot": {"name": "HubSpot", "logo": "https://logos.composio.dev/api/hubspot"},
    "salesforce": {"name": "Salesforce", "logo": "https://logos.composio.dev/api/salesforce"},
    "quickbooks": {"name": "QuickBooks", "logo": "https://logos.composio.dev/api/quickbooks"},
    "netsuite": {"name": "NetSuite", "logo": "https://logos.composio.dev/api/netsuite"},
    "gmail": {"name": "Gmail", "logo": "https://logos.composio.dev/api/gmail"},
}
