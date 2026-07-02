from aunix.schema_types import _coerce_json_object, _coerce_json_string_map
from aunix.spec import ActionPermission, ComposioSource


def test_json_object_accepts_dict_or_string():
    assert _coerce_json_object({}) == {}
    assert _coerce_json_object('{"limit": 10}') == {"limit": 10}


def test_json_string_map_accepts_dict_or_string():
    assert _coerce_json_string_map({"deal_id": "id"}) == {"deal_id": "id"}
    assert _coerce_json_string_map('{"deal_id": "id"}') == {"deal_id": "id"}


def test_action_permission_argument_template_from_json_string():
    perm = ActionPermission.model_validate(
        {
            "type": "composio",
            "tool_slug": "HUBSPOT_CREATE_NOTE",
            "argument_template": '{"note": "{{finding.summary}}"}',
        }
    )
    assert perm.argument_template == {"note": "{{finding.summary}}"}


def test_composio_source_arguments_from_json_string():
    src = ComposioSource.model_validate(
        {
            "toolkit": "hubspot",
            "tool_slug": "HUBSPOT_LIST_DEALS",
            "arguments": '{"limit": 25}',
            "row_mapping": '{"deal_id": "id"}',
        }
    )
    assert src.arguments == {"limit": 25}
    assert src.row_mapping == {"deal_id": "id"}


def test_compiled_intent_schema_has_no_open_dict_objects():
    from aunix.compiler import CompiledIntent

    schema = CompiledIntent.model_json_schema()

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "object" and node.get("additionalProperties") is True:
                raise AssertionError(f"open dict schema: {node}")
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(schema)
