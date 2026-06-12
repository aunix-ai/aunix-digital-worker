"""LLM-enriched reasoner. Wraps the deterministic reasoner: the finding set and
dedupe keys stay deterministic (stable keys keep the alert state machine sane);
the LLM rewrites summaries and recommendations into root-cause narratives.
Any LLM failure falls back to the rule-based findings - alerting never breaks
because the LLM did."""
import json
import logging

from pydantic import BaseModel

from aunix.conditions import Breach
from aunix.llm import LlmClient
from aunix.reasoning import Insight, Reasoner, RuleBasedReasoner
from aunix.spec import AgentSpec

logger = logging.getLogger(__name__)

SYSTEM = """You write operational alert narratives for a business monitoring \
platform. For each finding, rewrite the summary as a concise root-cause \
narrative (what happened, why it matters, relevant numbers/dates from the \
data) and the recommendation as one specific, actionable next step. Keep each \
dedupe_key exactly as given - never invent, merge, or rename keys. For ranked \
analysis findings, honor the user's ranking guidance when writing summaries."""


class EnrichedFinding(BaseModel):
    dedupe_key: str
    summary: str
    recommendation: str


class Enrichment(BaseModel):
    findings: list[EnrichedFinding]


class LlmReasoner:
    def __init__(self, llm: LlmClient, fallback: Reasoner | None = None):
        self.llm = llm
        self.fallback = fallback or RuleBasedReasoner()

    def reason(
        self,
        spec: AgentSpec,
        rows: list[dict],
        breaches: list[tuple[dict, Breach]],
    ) -> Insight:
        base = self.fallback.reason(spec, rows, breaches)
        if not base.findings:
            return base
        try:
            enriched = self.llm.parse(
                system=SYSTEM, prompt=self._prompt(spec, base), schema=Enrichment
            )
        except Exception:
            logger.exception("LLM enrichment failed; using rule-based findings")
            return base
        by_key = {e.dedupe_key: e for e in enriched.findings}
        for finding in base.findings:
            e = by_key.get(finding.dedupe_key)
            if e:
                finding.summary = e.summary
                finding.recommendation = e.recommendation
        return base

    def _prompt(self, spec: AgentSpec, base: Insight) -> str:
        findings = [
            {
                "dedupe_key": f.dedupe_key,
                "current_summary": f.summary,
                "data": f.details,
            }
            for f in base.findings
        ]
        parts = [f"Agent objective: {spec.objective}"]
        if spec.reasoning_instructions:
            parts.append(f"Ranking/analysis guidance: {spec.reasoning_instructions}")
        parts.append(f"Findings to enrich:\n{json.dumps(findings, indent=2)}")
        return "\n\n".join(parts)
