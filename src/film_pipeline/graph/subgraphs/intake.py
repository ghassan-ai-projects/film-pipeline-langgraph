"""Intake subgraph — classify input, infer config, present for approval."""

from __future__ import annotations

from film_pipeline.graph.nodes import intake_node

# Subgraph entry point: delegates to intake_node for now.
# Future: router → intake-classifier-agent → config-inference-agent → validator → synthesizer.
__all__ = ["intake_node"]
