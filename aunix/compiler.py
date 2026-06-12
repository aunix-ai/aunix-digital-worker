"""Human-to-Agent interface: compile a natural-language instruction into a
structured AgentSpec, or return clarifying questions when the intent is
under-specified. The interpreted spec is shown to the user for confirmation
before activation - no agent runs on an unconfirmed interpretation."""
from pydantic import BaseModel, ValidationError

from aunix.llm import LlmClient
from aunix.spec import AgentSpec

SYSTEM = """You compile natural-language instructions into an agent specification.

Rules:
- task_type is "monitoring" for watch/alert intents and "analysis" for \
report/ranking/briefing intents.
- data_sources is a subset of: "simship" (purchase orders and shipments), \
"hubspot" (CRM deals/leads), "csv" (uploaded sales reports).
- record_key is "po_number" for simship and "lead" for hubspot or csv.
- Monitoring specs need a conditions group. Available operators: gt, lt, gte, \
lte, eq, ne (a string value naming another column compares the two columns, \
ordering operators only), and stale_hours (numeric value, hours since a \
timestamp column last changed). simship columns: po_number, supplier, \
expected_date, delivery_date, last_tracking_update, priority, status.
- Analysis specs need rank_by (a numeric column: "deal_size") and top_n; \
put any richer ranking guidance in reasoning_instructions.
- schedule: interval (interval_minutes) for continuous monitoring, daily \
(daily_time "HH:MM" 24h) for briefings, on_demand if the user will trigger runs.
- notifications.channels from "feed" and "email"; email requires email_to.
- autonomy_level is 1 (notify) or 2 (recommend); this platform never executes \
actions.
- If a required detail is missing or ambiguous (e.g. no email address for an \
email channel, no schedule time), return clarifying_questions instead of a \
spec. Ask only for what you genuinely cannot infer."""


class CompiledIntent(BaseModel):
    """LLM output: exactly one of spec / clarifying_questions is populated."""

    spec: AgentSpec | None = None
    clarifying_questions: list[str] = []


class CompileResult(BaseModel):
    spec: AgentSpec | None
    questions: list[str]


def compile_intent(llm: LlmClient, text: str) -> CompileResult:
    try:
        out = llm.parse(system=SYSTEM, prompt=text, schema=CompiledIntent)
    except ValidationError as exc:
        retry_prompt = (
            f"{text}\n\nYour previous attempt failed validation:\n{exc}\n"
            "Return a corrected result."
        )
        out = llm.parse(system=SYSTEM, prompt=retry_prompt, schema=CompiledIntent)
    return CompileResult(spec=out.spec, questions=out.clarifying_questions)
