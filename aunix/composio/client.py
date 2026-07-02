"""Composio SDK client and scoped session factory."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from composio import Composio

from aunix.composio.constants import COMPOSIO_TOOLKITS

AuthConfigMap = dict[str, str]


def _settings():
    from aunix.config import Settings
    return Settings()


@lru_cache(maxsize=1)
def get_composio_client() -> Composio:
    api_key = os.environ.get("COMPOSIO_API_KEY", "").strip() or (_settings().composio_api_key or "").strip()
    if not api_key:
        raise RuntimeError("COMPOSIO_API_KEY is not configured")
    return Composio(api_key=api_key)


def get_composio_user_id(owner: str | None = None) -> str:
    """Map an agent owner to a Composio user id.

    Web UI owners like ``me`` are local placeholders — Composio connections are
    keyed by COMPOSIO_USER_ID until per-user mapping exists.
    """
    env_uid = os.environ.get("COMPOSIO_USER_ID", "").strip()
    default = env_uid or (_settings().composio_user_id or "flowops-demo-user")
    if not owner or not owner.strip():
        return default
    owner = owner.strip()
    if owner in {"me", "default", "local", "user"}:
        return default
    return owner


def resolve_auth_configs(composio: Composio | None = None) -> AuthConfigMap:
    composio = composio or get_composio_client()
    configs: AuthConfigMap = {}
    for toolkit, env_key in (
        ("salesforce", "COMPOSIO_AUTH_CONFIG_SALESFORCE"),
        ("quickbooks", "COMPOSIO_AUTH_CONFIG_QUICKBOOKS"),
        ("gmail", "COMPOSIO_AUTH_CONFIG_GMAIL"),
        ("hubspot", "COMPOSIO_AUTH_CONFIG_HUBSPOT"),
        ("netsuite", "COMPOSIO_AUTH_CONFIG_NETSUITE"),
    ):
        value = os.environ.get(env_key, "").strip()
        if value:
            configs[toolkit] = value
    if "netsuite" not in configs:
        try:
            result = composio.auth_configs.list(toolkit="netsuite", limit=10)
            items = getattr(result, "items", None) or []
            config = next((item for item in items if getattr(item, "status", None) == "ENABLED"), None)
            if config is None and items:
                config = items[0]
            if config and getattr(config, "id", None):
                configs["netsuite"] = config.id
        except Exception:
            pass
    return configs


def get_enabled_toolkits(auth: AuthConfigMap | None = None) -> list[str]:
    auth = auth or resolve_auth_configs()
    enabled: list[str] = []
    for slug in COMPOSIO_TOOLKITS:
        if slug == "netsuite" and "netsuite" not in auth:
            continue
        enabled.append(slug)
    return enabled


def get_session(user_id: str | None = None, *, toolkits: list[str] | None = None) -> Any:
    """Create a Composio session scoped to a user and enabled toolkits."""
    composio = get_composio_client()
    uid = user_id or get_composio_user_id()
    auth_configs = resolve_auth_configs(composio)
    toolkit_list = toolkits or get_enabled_toolkits(auth_configs)
    kwargs: dict[str, Any] = {"user_id": uid, "toolkits": toolkit_list}
    if auth_configs:
        kwargs["auth_configs"] = auth_configs
    return composio.create(**kwargs)
