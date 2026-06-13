from aunix.actions.planner import ProposedAction, RuleBasedActionPlanner
from aunix.models import Finding
from aunix.spec import ActionPermission
from aunix.testing import make_spec


def finding():
    return Finding(id=7, agent_id=1, run_id=3, dedupe_key="PO-4567:delivery_date",
                   summary="PO-4567 delayed 2 days", recommendation="Contact supplier",
                   source_ref="simship://PO-4567", severity="warning",
                   details={"row": {"po_number": "PO-4567", "supplier_email": "orders@acme.com"}})


def test_proposes_one_action_per_permitted_type():
    spec = make_spec(autonomy_level=3, actions=[
        ActionPermission(type="email", to_field="supplier_email"),
        ActionPermission(type="resolve"),
    ])
    actions = RuleBasedActionPlanner().plan(spec, finding())
    assert {a.type for a in actions} == {"email", "resolve"}


def test_dedupe_key_is_finding_plus_type():
    spec = make_spec(autonomy_level=3, actions=[ActionPermission(type="resolve")])
    a = RuleBasedActionPlanner().plan(spec, finding())[0]
    assert a.dedupe_key == "PO-4567:delivery_date:resolve"


def test_email_recipient_comes_from_to_field_then_to():
    f = finding()
    spec = make_spec(autonomy_level=3, actions=[ActionPermission(type="email", to_field="supplier_email")])
    assert RuleBasedActionPlanner().plan(spec, f)[0].params["to"] == "orders@acme.com"
    spec2 = make_spec(autonomy_level=3, actions=[ActionPermission(type="email", to="ops@fixed.com")])
    assert RuleBasedActionPlanner().plan(spec2, f)[0].params["to"] == "ops@fixed.com"


def test_unresolvable_email_recipient_is_omitted():
    spec = make_spec(autonomy_level=3, actions=[ActionPermission(type="email", to_field="missing")])
    assert RuleBasedActionPlanner().plan(spec, finding())[0].params.get("to") is None
