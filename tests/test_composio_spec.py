from aunix.spec import AgentSpec, ComposioSource, resolve_data_source_id


def test_composio_source_id():
    src = ComposioSource(
        toolkit="hubspot",
        tool_slug="HUBSPOT_LIST_DEALS",
        record_key="hubspot_id",
    )
    assert src.source_id() == "composio:hubspot_list_deals"


def test_agent_spec_accepts_mixed_data_sources():
    spec = AgentSpec.model_validate(
        {
            "name": "Watcher",
            "objective": "Watch deals",
            "task_type": "monitoring",
            "data_sources": [
                "simship",
                {
                    "type": "composio",
                    "toolkit": "hubspot",
                    "tool_slug": "HUBSPOT_LIST_DEALS",
                    "arguments": {},
                    "record_key": "hubspot_id",
                    "row_mapping": {},
                },
            ],
            "schedule": {"mode": "interval", "interval_minutes": 15},
            "notifications": {"channels": ["feed"]},
        }
    )
    assert resolve_data_source_id(spec.data_sources[0]) == "simship"
    assert resolve_data_source_id(spec.data_sources[1]) == "composio:hubspot_list_deals"


def test_composio_action_permission():
    spec = AgentSpec.model_validate(
        {
            "name": "Actor",
            "objective": "Act",
            "task_type": "monitoring",
            "data_sources": ["simship"],
            "schedule": {"mode": "interval", "interval_minutes": 15},
            "notifications": {"channels": ["feed"]},
            "autonomy_level": 4,
            "actions": [
                {
                    "type": "composio",
                    "tool_slug": "HUBSPOT_CREATE_NOTE",
                    "argument_template": {"note": "{{finding.summary}}"},
                }
            ],
            "policy": {
                "composio_auto": True,
                "composio_tool_slugs": ["HUBSPOT_CREATE_NOTE"],
            },
        }
    )
    assert spec.actions[0].tool_slug == "HUBSPOT_CREATE_NOTE"
