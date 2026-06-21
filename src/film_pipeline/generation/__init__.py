"""Generation — ledger, planning, prompt construction, and lifecycle management."""

from film_pipeline.generation.compositor import (
    build_character_identity_sheet,
    build_environment_board,
    build_expression_sheet,
    build_scale_sheet,
    build_style_board,
    replace_tile,
)
from film_pipeline.generation.delta_regenerator import regenerate_failing_tiles
from film_pipeline.generation.frame_heuristics import HeuristicResult, run_heuristic_checks
from film_pipeline.generation.frame_reviewer import (
    FrameReviewResult,
    review_frame,
    should_review_frame,
)
from film_pipeline.generation.frame_sidecar import (
    read_frame_sidecar,
    write_frame_sidecar,
)
from film_pipeline.generation.ledger import GenerationLedgerManager
from film_pipeline.generation.prompt_builder import build_structured_prompt
from film_pipeline.generation.sheet_reviewer import (
    SheetReviewResult,
    review_composite_sheet,
)

__all__ = [
    "FrameReviewResult",
    "GenerationLedgerManager",
    "HeuristicResult",
    "SheetReviewResult",
    "build_character_identity_sheet",
    "build_environment_board",
    "build_structured_prompt",
    "read_frame_sidecar",
    "regenerate_failing_tiles",
    "replace_tile",
    "review_composite_sheet",
    "review_frame",
    "run_heuristic_checks",
    "should_review_frame",
    "write_frame_sidecar",
]
