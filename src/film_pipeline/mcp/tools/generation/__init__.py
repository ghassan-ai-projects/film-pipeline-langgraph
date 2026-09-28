"""Generation batch planning, approval, status, and lifecycle tools.

Split by lifecycle stage; this facade preserves the original import surface.
"""

from __future__ import annotations

from film_pipeline.filmspec import is_text_only_policy as is_text_only_policy
from film_pipeline.mcp.tools.generation._text_only import (
    _complete_text_only_generation,
)
from film_pipeline.mcp.tools.generation.dispatch import (
    GENERATION_DISPATCH_TOOLS,
    cancel_generation_request,
    resume_generation_polling,
    start_generation_batch,
)
from film_pipeline.mcp.tools.generation.planning import (
    GENERATION_PLANNING_TOOLS,
    _sync_generation_requests_from_ledger,
    plan_generation_batch,
    preview_generation_prompts,
)
from film_pipeline.mcp.tools.generation.promote import (
    GENERATION_PROMOTE_TOOLS,
    promote_test_to_production,
)
from film_pipeline.mcp.tools.generation.status import (
    GENERATION_STATUS_TOOLS,
    get_generation_status,
    list_active_generations,
)

__all__ = [
    "GENERATION_DISPATCH_TOOLS",
    "GENERATION_PLANNING_TOOLS",
    "GENERATION_PROMOTE_TOOLS",
    "GENERATION_STATUS_TOOLS",
    "_complete_text_only_generation",
    "_sync_generation_requests_from_ledger",
    "cancel_generation_request",
    "get_generation_status",
    "is_text_only_policy",
    "list_active_generations",
    "plan_generation_batch",
    "preview_generation_prompts",
    "promote_test_to_production",
    "resume_generation_polling",
    "start_generation_batch",
]
