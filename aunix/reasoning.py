"""Reasoner seam. RuleBasedReasoner is the deterministic offline implementation;
the agentu-backed LLM reasoner (Plan 2) implements the same protocol to add
narrative root-cause analysis and multi-factor ranking."""
from typing import Protocol

from pydantic import BaseModel

from aunix.conditions import Breach
from aunix.findings import CandidateFinding
from aunix.spec import AgentSpec


class Insight(BaseModel):
    findings: list[CandidateFinding]


class Reasoner(Protocol):
    def reason(
        self,
        spec: AgentSpec,
        rows: list[dict],
        breaches: list[tuple[dict, Breach]],
    ) -> Insight: ...


class RuleBasedReasoner:
    def reason(self, spec, rows, breaches) -> Insight:
        if spec.task_type == "monitoring":
            return Insight(findings=[self._breach_finding(spec, row, b) for row, b in breaches])
        return Insight(findings=self._ranked_findings(spec, rows))

    def _breach_finding(self, spec: AgentSpec, row: dict, breach: Breach) -> CandidateFinding:
        key = str(row.get(spec.record_key, "unknown"))
        fields = ",".join(c.field for c in breach.matched)
        return CandidateFinding(
            dedupe_key=f"{key}:{fields}",
            severity="warning",
            summary=f"{key}: condition breach on {fields}",
            recommendation="Review the record and contact the responsible party.",
            source_ref=f"{spec.data_sources[0]}://{key}",
            details={"row": _jsonable(row), "matched": fields},
        )

    def _ranked_findings(self, spec: AgentSpec, rows: list[dict]) -> list[CandidateFinding]:
        ranked = sorted(rows, key=lambda r: r.get(spec.rank_by) or 0, reverse=True)
        return [
            CandidateFinding(
                dedupe_key=f"rank-{i + 1}:{row.get(spec.record_key)}",
                severity="info",
                summary=f"#{i + 1}: {row.get(spec.record_key)} ({spec.rank_by}={row.get(spec.rank_by)})",
                recommendation="Prioritize outreach.",
                source_ref=f"{spec.data_sources[0]}://{row.get(spec.record_key)}",
                details={"row": _jsonable(row)},
            )
            for i, row in enumerate(ranked[: spec.top_n])
        ]


def _jsonable(row: dict) -> dict:
    return {
        k: (v.isoformat() if hasattr(v, "isoformat") else v)
        for k, v in row.items()
    }
