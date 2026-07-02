from aunix.composio.client import get_composio_user_id


def test_placeholder_owner_maps_to_default_composio_user(monkeypatch):
    monkeypatch.setenv("COMPOSIO_USER_ID", "flowops-demo-user")
    assert get_composio_user_id("me") == "flowops-demo-user"
    assert get_composio_user_id(None) == "flowops-demo-user"


def test_explicit_owner_is_preserved(monkeypatch):
    monkeypatch.setenv("COMPOSIO_USER_ID", "flowops-demo-user")
    assert get_composio_user_id("tenant-acme-42") == "tenant-acme-42"
