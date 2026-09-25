"""Compatibility aliases for :mod:`film_pipeline.orchestration.state_schema`."""

from __future__ import annotations

from film_pipeline.orchestration.state_schema import GraphServices as GraphServices
from film_pipeline.orchestration.state_schema import StudioGraphState as StudioGraphState
from film_pipeline.orchestration.state_schema import (
    merge_generation_requests as merge_generation_requests,
)
from film_pipeline.orchestration.state_schema import merge_issues as merge_issues
from film_pipeline.orchestration.state_schema import merge_unique as merge_unique

__all__ = [
    "GraphServices",
    "StudioGraphState",
    "merge_generation_requests",
    "merge_issues",
    "merge_unique",
]
