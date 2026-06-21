"""QCSynthesisAgent — synthesizes multiple validator reports into a ConsensusReport."""

from __future__ import annotations

from typing import Any

from film_pipeline.agents.base import BaseAgent
from film_pipeline.schemas._base import ValidationStatus
from film_pipeline.schemas.validation import ConsensusReport, ReviewerScore


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
        data = model_output.get("consensus", model_output)

        # Handle the case where the LLM returns the reviewers as a direct
        # list (e.g. {"consensus": [{"model_id": ...}]}) instead of a dict
        # with separate "reviewers", "shared_findings", etc. keys.
        if isinstance(data, list):
            reviewers_data = data
            artifact_refs: list[str] = []
            shared_findings: list[str] = []
            disagreements: list[str] = []
            review_id = "qc-001"
            agreement_level = "medium"
            consensus_status = ValidationStatus("pass")
            orchestrator_recommendation = ""
        elif isinstance(data, dict):
            reviewers_data = data.get("reviewers", [])
            artifact_refs = [str(a) for a in data.get("artifact_refs", [])]
            shared_findings = [str(f) for f in data.get("shared_findings", [])]
            disagreements = [str(d) for d in data.get("disagreements", [])]
            review_id = str(data.get("review_id", "qc-001"))
            agreement_level = str(data.get("agreement_level", "medium"))
            consensus_status = ValidationStatus(str(data.get("consensus_status", "pass")))
            orchestrator_recommendation = str(data.get("orchestrator_recommendation", ""))
        else:
            reviewers_data = []
            artifact_refs = []
            shared_findings = []
            disagreements = []
            review_id = "qc-001"
            agreement_level = "medium"
            consensus_status = ValidationStatus("pass")
            orchestrator_recommendation = ""

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
            review_id=review_id,
            artifact_refs=artifact_refs,
            reviewers=reviewers,
            agreement_level=agreement_level,
            consensus_status=consensus_status,
            shared_findings=shared_findings,
            disagreements=disagreements,
            orchestrator_recommendation=orchestrator_recommendation,
        )
        return {"consensus_report": report}

    def validate(self, result: dict[str, Any]) -> bool:
        report = result.get("consensus_report")
        if not isinstance(report, ConsensusReport):
            return False
        return bool(report.review_id and len(report.reviewers) > 0)
