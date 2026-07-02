from aunix.actions.gate import gate
from aunix.actions.planner import ProposedAction
from aunix.spec import ActionPermission, ActionPolicy
from aunix.testing import make_spec


def l4(policy, *perms):
    return make_spec(autonomy_level=4, actions=list(perms), policy=policy)


def test_l3_always_queues():
    spec = make_spec(autonomy_level=3, actions=[ActionPermission(type="resolve")])
    p = ProposedAction(type="resolve", params={}, dedupe_key="k")
    assert gate(spec, p, run_auto_count=0, day_auto_count=0) == "queued"


def test_resolve_auto_executes_when_whitelisted():
    spec = l4(ActionPolicy(resolve_auto=True), ActionPermission(type="resolve"))
    p = ProposedAction(type="resolve", params={}, dedupe_key="k")
    assert gate(spec, p, run_auto_count=0, day_auto_count=0) == "auto"


def test_type_not_whitelisted_queues():
    spec = l4(ActionPolicy(resolve_auto=False), ActionPermission(type="resolve"))
    p = ProposedAction(type="resolve", params={}, dedupe_key="k")
    assert gate(spec, p, run_auto_count=0, day_auto_count=0) == "queued"


def test_email_requires_recipient_in_allowed_domain():
    spec = l4(ActionPolicy(email_auto=True, email_to_domains=["acme.com"]),
              ActionPermission(type="email", to_field="supplier_email"))
    in_bounds = ProposedAction(type="email", params={"to": "ops@acme.com"}, dedupe_key="k1")
    out_of_bounds = ProposedAction(type="email", params={"to": "ops@evil.com"}, dedupe_key="k2")
    no_recipient = ProposedAction(type="email", params={}, dedupe_key="k3")
    assert gate(spec, in_bounds, run_auto_count=0, day_auto_count=0) == "auto"
    assert gate(spec, out_of_bounds, run_auto_count=0, day_auto_count=0) == "queued"
    assert gate(spec, no_recipient, run_auto_count=0, day_auto_count=0) == "queued"


def test_hubspot_op_must_be_whitelisted():
    spec = l4(ActionPolicy(hubspot_auto=True, hubspot_ops=["add_note"]),
              ActionPermission(type="hubspot", ops=["add_note", "set_property"]))
    note = ProposedAction(type="hubspot", params={"op": "add_note"}, dedupe_key="k1")
    prop = ProposedAction(type="hubspot", params={"op": "set_property"}, dedupe_key="k2")
    assert gate(spec, note, run_auto_count=0, day_auto_count=0) == "auto"
    assert gate(spec, prop, run_auto_count=0, day_auto_count=0) == "queued"


def test_per_run_cap_queues_overflow():
    spec = l4(ActionPolicy(resolve_auto=True, per_run=2), ActionPermission(type="resolve"))
    p = ProposedAction(type="resolve", params={}, dedupe_key="k")
    assert gate(spec, p, run_auto_count=1, day_auto_count=0) == "auto"
    assert gate(spec, p, run_auto_count=2, day_auto_count=0) == "queued"


def test_per_day_cap_queues_overflow():
    spec = l4(ActionPolicy(resolve_auto=True, per_day=5), ActionPermission(type="resolve"))
    p = ProposedAction(type="resolve", params={}, dedupe_key="k")
    assert gate(spec, p, run_auto_count=0, day_auto_count=4) == "auto"
    assert gate(spec, p, run_auto_count=0, day_auto_count=5) == "queued"


def test_composio_slug_must_be_whitelisted():
    spec = l4(
        ActionPolicy(composio_auto=True, composio_tool_slugs=["HUBSPOT_CREATE_NOTE"]),
        ActionPermission(type="composio", tool_slug="HUBSPOT_CREATE_NOTE"),
    )
    allowed = ProposedAction(
        type="composio",
        params={"tool_slug": "HUBSPOT_CREATE_NOTE", "arguments": {}},
        dedupe_key="k1",
    )
    blocked = ProposedAction(
        type="composio",
        params={"tool_slug": "HUBSPOT_DELETE_DEAL", "arguments": {}},
        dedupe_key="k2",
    )
    assert gate(spec, allowed, run_auto_count=0, day_auto_count=0) == "auto"
    assert gate(spec, blocked, run_auto_count=0, day_auto_count=0) == "queued"
