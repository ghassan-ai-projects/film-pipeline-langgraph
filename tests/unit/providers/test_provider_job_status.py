"""Contract tests for the provider-job status vocabulary.

``ProviderJob.status`` is a closed :class:`StrEnum` vocabulary shared by every
adapter. Members must serialize as their plain string values so existing JSON
payloads stay byte-identical.
"""

from __future__ import annotations

import json

from film_pipeline.providers.base import ProviderJob, ProviderJobStatus

_CONSUMED_VOCABULARY = {"submitted", "processing", "completed", "failed", "cancelled"}


def test_provider_job_status_values_round_trip() -> None:
    for member in ProviderJobStatus:
        assert ProviderJobStatus(member.value) is member


def test_provider_job_status_serializes_as_plain_string() -> None:
    for member in ProviderJobStatus:
        assert json.loads(json.dumps(member)) == member.value
        assert str(member) == member.value


def test_provider_job_status_covers_produced_vocabulary() -> None:
    assert {status.value for status in ProviderJobStatus} == _CONSUMED_VOCABULARY


def test_provider_job_default_status_is_submitted() -> None:
    job = ProviderJob(job_id="j1", shot_id="S001", provider_id="mock-video-provider", model="m")
    assert job.status is ProviderJobStatus.SUBMITTED
    assert job.status.value == "submitted"
