from aunix.actions.planner import DraftedActions, LlmActionPlanner, ProposedAction
from aunix.llm import FakeLlm, LlmError
from aunix.models import Finding
from aunix.spec import ActionPermission
from aunix.testing import make_spec


def finding():
    return Finding(id=7, agent_id=1, run_id=3, dedupe_key="PO-4567:delivery_date",
                   summary="PO-4567 delayed 2 days", recommendation="Contact supplier",
                   source_ref="simship://PO-4567", severity="warning",
                   details={"row": {"po_number": "PO-4567", "supplier_email": "orders@acme.com"}})


def spec():
    return make_spec(autonomy_level=3, actions=[ActionPermission(type="email", to_field="supplier_email")])


def test_llm_drafts_are_constrained_to_permitted_types_and_keys():
    # LLM tries to also draft a forbidden 'hubspot' action and a wrong key
    fake = FakeLlm([DraftedActions(actions=[
        ProposedAction(type="email", params={"to": "orders@acme.com", "subject": "S", "body": "B"},
                       dedupe_key="ignored-by-us"),
        ProposedAction(type="hubspot", params={}, dedupe_key="x"),
    ])])
    actions = LlmActionPlanner(fake).plan(spec(), finding())
    assert [a.type for a in actions] == ["email"]          # forbidden type dropped
    assert actions[0].dedupe_key == "PO-4567:delivery_date:email"  # key forced deterministic
    assert actions[0].params["subject"] == "S"             # LLM content kept


def test_llm_failure_falls_back_to_rule_based():
    actions = LlmActionPlanner(FakeLlm([LlmError("down")])).plan(spec(), finding())
    assert [a.type for a in actions] == ["email"]
    assert actions[0].params["to"] == "orders@acme.com"    # rule-based recipient
