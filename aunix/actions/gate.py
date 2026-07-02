"""The L4 policy gate (pure logic). Decides, per proposed action, whether it
auto-executes ("auto") or falls back to the L3 approval queue ("queued").

Safety invariant — **L4 ⊆ L3**: an action auto-executes only when the policy
explicitly whitelists its type, its target is within the type's declared bounds,
and neither the per-run nor per-day cap is exceeded. Everything else queues for a
human; nothing is ever silently dropped. L3 (or any spec without a policy) always
queues."""
from aunix.actions.planner import ProposedAction
from aunix.spec import AgentSpec


def _recipient_domain_allowed(recipient: str | None, domains: list[str]) -> bool:
    if not recipient or "@" not in recipient:
        return False
    domain = recipient.rsplit("@", 1)[1].lower()
    return domain in {d.lower().lstrip("@") for d in domains}


def gate(spec: AgentSpec, proposed: ProposedAction, *,
         run_auto_count: int, day_auto_count: int) -> str:
    """Return "auto" or "queued" for a single proposed action.

    run_auto_count / day_auto_count are the number of actions already auto-approved
    in this run / this agent's rolling 24h window, used to enforce the caps.
    """
    if spec.autonomy_level != 4 or spec.policy is None:
        return "queued"
    policy = spec.policy
    if run_auto_count >= policy.per_run or day_auto_count >= policy.per_day:
        return "queued"

    if proposed.type == "email":
        if not policy.email_auto:
            return "queued"
        if not _recipient_domain_allowed(proposed.params.get("to"), policy.email_to_domains):
            return "queued"
        return "auto"
    if proposed.type == "hubspot":
        if not policy.hubspot_auto:
            return "queued"
        if proposed.params.get("op", "add_note") not in policy.hubspot_ops:
            return "queued"
        return "auto"
    if proposed.type == "composio":
        if not policy.composio_auto:
            return "queued"
        slug = str(proposed.params.get("tool_slug") or "")
        if policy.composio_tool_slugs and slug not in policy.composio_tool_slugs:
            return "queued"
        return "auto"
    if proposed.type == "task":
        return "auto" if policy.task_auto else "queued"
    if proposed.type == "resolve":
        return "auto" if policy.resolve_auto else "queued"
    return "queued"
