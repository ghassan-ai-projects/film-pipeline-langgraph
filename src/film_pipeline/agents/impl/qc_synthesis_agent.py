"""QCSynthesisAgent — synthesizes multiple validator reports into a ConsensusReport."""

from __future__ import annotations

from typing import Any

from film_pipeline.agents.base import BaseAgent
from film_pipeline.schemas.base import ValidationStatus
from film_pipeline.schemas.validation import ConsensusReport, ReviewerScore


def _normalize_consensus_payload(model_output: dict[str, Any]) -> dict[str, Any]:
    """Normalize the consensus payload into a consensus field dict.

    The LLM may return the reviewers as a bare list (e.g.
    ``{"consensus": [{"model_id": ...}]}``) instead of a dict with separate
    ``reviewers``, ``shared_findings``, etc. keys; any non-list, non-dict
    payload degrades to an empty report.
    """
    consensus = model_output.get("consensus", model_output)
    if isinstance(consensus, list):
        return {"reviewers": consensus}
    return consensus if isinstance(consensus, dict) else {}


class QCSynthesisAgent(BaseAgent):
    """Synthesizes multiple validator reports into a unified QC report.

    Output artifact: ``ConsensusReport``
    """

    def prepare(
        self,
        state: dict[str, Any],
        kb_context: object,
        task: str,
    ) -> dict[str, Any]:
        _ = kb_context
        project_id = str(state.get("project_id", ""))
        validator_report_refs = str(state.get("validator_report_refs", ""))
        return {
            "project_id": project_id,
            "validator_report_refs": validator_report_refs,
            "task": task,
        }

    def execute(self, model_output: dict[str, Any]) -> dict[str, Any]:
        data = _normalize_consensus_payload(model_output)

        reviewers_data = data.get("reviewers", [])
        reviewers = [
            ReviewerScore(
                model_id=str(r.get("model_id", f"model_{i}")),
                validator_id=str(r.get("validator_id", "")),
                score=float(r.get("score", 50.0)),
                status=ValidationStatus(str(r.get("status", "pass"))),
            )
            for i, r in enumerate(reviewers_data)
        ]

        report = ConsensusReport(
            review_id=str(data.get("review_id", "qc-001")),
            artifact_refs=[str(a) for a in data.get("artifact_refs", [])],
            reviewers=reviewers,
            agreement_level=data.get("agreement_level", "medium"),
            consensus_status=ValidationStatus(str(data.get("consensus_status", "pass"))),
            shared_findings=[str(f) for f in data.get("shared_findings", [])],
            disagreements=[str(d) for d in data.get("disagreements", [])],
            orchestrator_recommendation=str(data.get("orchestrator_recommendation", "")),
        )
        return {"consensus_report": report}

    def validate(self, result: dict[str, Any]) -> bool:
        report = result.get("consensus_report")
        if not isinstance(report, ConsensusReport):
            return False
        return bool(report.review_id and len(report.reviewers) > 0)
