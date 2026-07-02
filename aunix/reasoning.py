"""Reasoner seam. RuleBasedReasoner is the deterministic offline implementation;
the agentu-backed LLM reasoner (Plan 2) implements the same protocol to add
narrative root-cause analysis and multi-factor ranking."""
from typing import Protocol

from pydantic import BaseModel

from aunix.conditions import Breach
from aunix.findings import CandidateFinding
from aunix.spec import AgentSpec, resolve_record_key


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
            findings = [
                f for row, breach in breaches for f in self._breach_findings(spec, row, breach)
            ]
            return Insight(findings=findings)
        return Insight(findings=self._ranked_findings(spec, rows))

    def _breach_findings(self, spec: AgentSpec, row: dict, breach: Breach) -> list[CandidateFinding]:
        key = resolve_record_key(spec, row)
        if spec.conditions and spec.conditions.mode == "all":
            # all-mode breaches are one composite event; the field set is the full
            # group, so the key is stable across runs
            fields = ",".join(sorted(c.field for c in breach.matched))
            return [self._finding(spec, row, key, f"{key}:all:{fields}", fields)]
        # any-mode: one finding per matched condition, so an ongoing breach stays
        # quiet while a newly firing condition still alerts
        return [
            self._finding(spec, row, key, f"{key}:{c.field}", c.field)
            for c in breach.matched
        ]

    def _finding(
        self, spec: AgentSpec, row: dict, key: str, dedupe_key: str, fields: str
    ) -> CandidateFinding:
        return CandidateFinding(
            dedupe_key=dedupe_key,
            severity="warning",
            summary=f"{key}: condition breach on {fields}",
            recommendation="Review the record and contact the responsible party.",
            source_ref=f"{spec.data_sources[0]}://{key}",
            details={"row": _jsonable(row), "matched": fields},
        )

    def _ranked_findings(self, spec: AgentSpec, rows: list[dict]) -> list[CandidateFinding]:
        ranked = sorted(rows, key=lambda r: _numeric(r.get(spec.rank_by)), reverse=True)
        return [
            CandidateFinding(
                dedupe_key=f"rank-{i + 1}:{resolve_record_key(spec, row)}",
                severity="info",
                summary=f"#{i + 1}: {resolve_record_key(spec, row)} ({spec.rank_by}={row.get(spec.rank_by)})",
                recommendation="Prioritize outreach.",
                source_ref=f"{spec.data_sources[0]}://{resolve_record_key(spec, row)}",
                details={"row": _jsonable(row)},
            )
            for i, row in enumerate(ranked[: spec.top_n])
        ]


def _jsonable(row: dict) -> dict:
    return {
        k: (v.isoformat() if hasattr(v, "isoformat") else v)
        for k, v in row.items()
    }


def _numeric(value) -> float:
    """Non-numeric rank values sort last rather than crashing the run."""
    return value if isinstance(value, (int, float)) else 0.0
