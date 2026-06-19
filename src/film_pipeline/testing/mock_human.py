"""Mock human actor — deterministic, scenario-driven review decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class DecisionProfile(StrEnum):
    APPROVE_ALL = "approve_all"
    REVISE_SCRIPT_ONCE = "revise_script_once"
    REJECT_BAD_REFERENCE = "reject_bad_reference"
    APPROVE_SPEND_UNDER_LIMIT = "approve_spend_under_limit"
    STOP_ON_PROVIDER_BLOCK = "stop_on_provider_block"
    CONFIRM_ROLLBACK = "confirm_rollback"
    REJECT_FINAL_CUT = "reject_final_cut"


@dataclass
class MockHumanActor:
    profile: DecisionProfile = DecisionProfile.APPROVE_ALL
    script_revision_count: int = field(default=0, init=False)
    spend_limit_usd: float = 5.0
    test_mode: bool = True

    def decide(self, phase: str, review_type: str, summary: str = "") -> str:
        _ = summary
        if not self.test_mode:
            raise RuntimeError("Mock human actor is disabled in production mode.")

        if self.profile == DecisionProfile.APPROVE_ALL:
            return "approve"
        if self.profile == DecisionProfile.REVISE_SCRIPT_ONCE:
            if phase == "script" and self.script_revision_count == 0:
                self.script_revision_count += 1
                return "request_revision"
            return "approve"
        if self.profile == DecisionProfile.REJECT_BAD_REFERENCE:
            if review_type == "visual_bible_review":
                return "request_revision"
            return "approve"
        if self.profile == DecisionProfile.APPROVE_SPEND_UNDER_LIMIT:
            return "approve"
        if self.profile == DecisionProfile.STOP_ON_PROVIDER_BLOCK:
            return "approve"
        if self.profile == DecisionProfile.CONFIRM_ROLLBACK:
            return "approve"
        if self.profile == DecisionProfile.REJECT_FINAL_CUT:
            if review_type == "final_cut_review":
                return "request_revision"
            return "approve"

        return "approve"  # type: ignore[unreachable]

    def approval_record_metadata(self) -> dict[str, str]:
        return {"actor_type": "mock_human", "profile": self.profile.value}
