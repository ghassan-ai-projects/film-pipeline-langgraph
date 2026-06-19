"""Mock provider scenario definitions — 13 deterministic test scenarios."""

from __future__ import annotations

from film_pipeline.providers.mock_provider import ScenarioStep

# --- Happy path ---

HAPPY_PATH_SEQUENTIAL_CHAIN: list[ScenarioStep] = [
    ScenarioStep(shot_id="S001-01", submit="success", polls_before_complete=2),
    ScenarioStep(shot_id="S001-02", submit="success", polls_before_complete=2),
    ScenarioStep(shot_id="S001-03", submit="success", polls_before_complete=1),
]

SLOW_POLL_THEN_COMPLETE: list[ScenarioStep] = [
    ScenarioStep(shot_id="S001-01", submit="success", polls_before_complete=8),
]

# --- Error scenarios ---

TIMEOUT_THEN_RESUME: list[ScenarioStep] = [
    ScenarioStep(shot_id="S001-01", submit="success", polls_before_complete=99),
]

SUBMIT_ERROR_BEFORE_JOB_ID: list[ScenarioStep] = [
    ScenarioStep(
        shot_id="S001-01",
        submit="error",
        error_code="submit_rejected",
        expected_decision="retry_or_fail",
    ),
]

NETWORK_ERROR_AFTER_JOB_ID: list[ScenarioStep] = [
    ScenarioStep(
        shot_id="S001-01",
        submit="success",
        polls_before_complete=3,
        error_code="network_error",
        expected_decision="retry_once",
    ),
]

DOWNLOAD_FAILURE_THEN_SUCCESS: list[ScenarioStep] = [
    ScenarioStep(
        shot_id="S001-01",
        submit="success",
        polls_before_complete=1,
        output="corrupt",
        error_code="download_failure",
    ),
]

FRAME_EXTRACTION_FAILURE: list[ScenarioStep] = [
    ScenarioStep(
        shot_id="S001-01",
        submit="success",
        polls_before_complete=1,
        last_frame="failed",
        mid_frame="failed",
    ),
]

# --- Provider state scenarios ---

QUOTA_EXHAUSTED: list[ScenarioStep] = [
    ScenarioStep(shot_id="S001-01", submit="success", polls_before_complete=1),
    ScenarioStep(shot_id="S001-02", submit="success", polls_before_complete=1),
    ScenarioStep(
        shot_id="S001-03",
        submit="error",
        error_code="quota_exhausted",
        expected_decision="stop_until_resolved",
    ),
]

AUTH_FAILURE: list[ScenarioStep] = [
    ScenarioStep(
        shot_id="S001-01",
        submit="error",
        error_code="auth_failure",
        expected_decision="stop_until_resolved",
    ),
]

PROVIDER_OUTAGE: list[ScenarioStep] = [
    ScenarioStep(
        shot_id="S001-01",
        submit="error",
        error_code="provider_outage",
        expected_decision="pause_queue",
    ),
]

MODERATION_BLOCK: list[ScenarioStep] = [
    ScenarioStep(
        shot_id="S001-01",
        submit="success",
        polls_before_complete=1,
        error_code="moderation_blocked",
        expected_decision="review_prompt",
    ),
]

CORRUPT_ASSET: list[ScenarioStep] = [
    ScenarioStep(
        shot_id="S001-01",
        submit="success",
        polls_before_complete=1,
        output="corrupt",
        error_code="corrupt_asset",
        expected_decision="retry_generation",
    ),
]

VALIDATOR_FAILURE_AFTER_GENERATION: list[ScenarioStep] = [
    ScenarioStep(shot_id="S001-01", submit="success", polls_before_complete=1),
]

# --- Scenario registry ---

ALL_SCENARIOS: dict[str, list[ScenarioStep]] = {
    "happy_path_sequential_chain": HAPPY_PATH_SEQUENTIAL_CHAIN,
    "slow_poll_then_complete": SLOW_POLL_THEN_COMPLETE,
    "timeout_then_resume": TIMEOUT_THEN_RESUME,
    "submit_error_before_job_id": SUBMIT_ERROR_BEFORE_JOB_ID,
    "network_error_after_job_id": NETWORK_ERROR_AFTER_JOB_ID,
    "download_failure_then_success": DOWNLOAD_FAILURE_THEN_SUCCESS,
    "frame_extraction_failure": FRAME_EXTRACTION_FAILURE,
    "quota_exhausted": QUOTA_EXHAUSTED,
    "auth_failure": AUTH_FAILURE,
    "provider_outage": PROVIDER_OUTAGE,
    "moderation_block": MODERATION_BLOCK,
    "corrupt_asset": CORRUPT_ASSET,
    "validator_failure_after_generation": VALIDATOR_FAILURE_AFTER_GENERATION,
}
