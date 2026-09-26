"""Generation batch planning, approval, status, and lifecycle tools.

Split by lifecycle stage; this facade preserves the original import surface.
"""

from __future__ import annotations

from film_pipeline.filmspec import is_text_only_policy as is_text_only_policy
from film_pipeline.mcp.tools.generation._text_only import (
    _complete_text_only_generation,
)
from film_pipeline.mcp.tools.generation.dispatch import (
    cancel_generation_request,
    resume_generation_polling,
    start_generation_batch,
)
from film_pipeline.mcp.tools.generation.planning import (
    _sync_generation_requests_from_ledger,
    approve_generation_spend,
    plan_generation_batch,
    preview_generation_prompts,
)
from film_pipeline.mcp.tools.generation.promote import promote_test_to_production
from film_pipeline.mcp.tools.generation.status import (
    get_generation_status,
    list_active_generations,
)

__all__ = [
    "_complete_text_only_generation",
    "_sync_generation_requests_from_ledger",
    "approve_generation_spend",
    "cancel_generation_request",
    "get_generation_status",
    "list_active_generations",
    "plan_generation_batch",
    "preview_generation_prompts",
    "promote_test_to_production",
    "resume_generation_polling",
    "start_generation_batch",
]
