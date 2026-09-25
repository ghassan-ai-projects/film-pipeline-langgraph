"""Compatibility aliases for devharness scenarios.

Re-exports from the canonical owner. Strict mypy requires an explicit export
surface, so each name is re-exported as itself.
"""

from film_pipeline.devharness.scenarios import ALL_SCENARIOS as ALL_SCENARIOS
from film_pipeline.devharness.scenarios import AUTH_FAILURE as AUTH_FAILURE
from film_pipeline.devharness.scenarios import CORRUPT_ASSET as CORRUPT_ASSET
from film_pipeline.devharness.scenarios import (
    DOWNLOAD_FAILURE_THEN_SUCCESS as DOWNLOAD_FAILURE_THEN_SUCCESS,
)
from film_pipeline.devharness.scenarios import FRAME_EXTRACTION_FAILURE as FRAME_EXTRACTION_FAILURE
from film_pipeline.devharness.scenarios import (
    HAPPY_PATH_SEQUENTIAL_CHAIN as HAPPY_PATH_SEQUENTIAL_CHAIN,
)
from film_pipeline.devharness.scenarios import MODERATION_BLOCK as MODERATION_BLOCK
from film_pipeline.devharness.scenarios import (
    NETWORK_ERROR_AFTER_JOB_ID as NETWORK_ERROR_AFTER_JOB_ID,
)
from film_pipeline.devharness.scenarios import PROVIDER_OUTAGE as PROVIDER_OUTAGE
from film_pipeline.devharness.scenarios import QUOTA_EXHAUSTED as QUOTA_EXHAUSTED
from film_pipeline.devharness.scenarios import SLOW_POLL_THEN_COMPLETE as SLOW_POLL_THEN_COMPLETE
from film_pipeline.devharness.scenarios import (
    SUBMIT_ERROR_BEFORE_JOB_ID as SUBMIT_ERROR_BEFORE_JOB_ID,
)
from film_pipeline.devharness.scenarios import TIMEOUT_THEN_RESUME as TIMEOUT_THEN_RESUME
from film_pipeline.devharness.scenarios import (
    VALIDATOR_FAILURE_AFTER_GENERATION as VALIDATOR_FAILURE_AFTER_GENERATION,
)

__all__ = [
    "ALL_SCENARIOS",
    "AUTH_FAILURE",
    "CORRUPT_ASSET",
    "DOWNLOAD_FAILURE_THEN_SUCCESS",
    "FRAME_EXTRACTION_FAILURE",
    "HAPPY_PATH_SEQUENTIAL_CHAIN",
    "MODERATION_BLOCK",
    "NETWORK_ERROR_AFTER_JOB_ID",
    "PROVIDER_OUTAGE",
    "QUOTA_EXHAUSTED",
    "SLOW_POLL_THEN_COMPLETE",
    "SUBMIT_ERROR_BEFORE_JOB_ID",
    "TIMEOUT_THEN_RESUME",
    "VALIDATOR_FAILURE_AFTER_GENERATION",
]
