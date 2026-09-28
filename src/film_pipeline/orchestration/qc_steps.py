"""The QC steps both QC entry paths owe.

Two steps of a QC pass are not the subgraph's private business, and they used to
live in ``nodes/qc.py``: emitting a matrix patch from per-row findings, and
building the consensus report from the validator reports collected. They are here
so that both the sequential runner (``nodes.qc``, for the phases that still call
``_run_validators`` directly) and the parallel subgraph (``subgraphs.qc``, the QC
phase node) share one implementation.

## Why this sits at the `orchestration` root

The placement is a cycle constraint, measured rather than guessed.
``subgraphs.qc`` needs these two functions and ``nodes.qc`` needs them too, so
they must sit *below* both. Anywhere under ``nodes`` makes ``subgraphs ->
nodes``; anywhere under ``subgraphs`` makes ``nodes -> subgraphs``, which is the
same cycle reversed. At the root, with only leaf modules under it, the edges run
one way and terminate:

    nodes.qc     -> orchestration.qc_steps   -> leaf modules
    subgraphs.qc -> orchestration.qc_steps   -> leaf modules

``orchestration.qc_phase_node`` was tried here too and reverted: a root-level
module importing ``subgraphs`` reads to Enola as the ``orchestration`` root
depending on ``subgraphs``, which closes a three-module cycle on paper even
though importing ``subgraphs.qc`` loads no ``nodes`` module at runtime. The
compiled-node accessor therefore lives inside ``subgraphs.qc``, and only the leaf
helpers live here.

See ``documentation/qc-single-implementation.md`` for the QC decision itself.
"""

from __future__ import annotations

import logging

from film_pipeline.orchestration.state_schema import StudioGraphState
from film_pipeline.validation.consensus import ConsensusBuilder

_logger = logging.getLogger(__name__)


def build_consensus_if_needed(state: StudioGraphState, phase: str) -> None:
    """Build a consensus report when multiple validators produced reports.

    Deterministic: ``validation.consensus.ConsensusBuilder`` summarises the
    reports the validators actually returned, so it cannot disagree with them.
    The earlier agent-based synthesis asked the clip-validator to free-text a
    summary of findings it had not seen; the subgraph never ran it, and the
    decision recorded in ``documentation/qc-single-implementation.md`` drops it
    in favour of this one.
    """
    reports = state.get("_validation_reports", [])
    if len(reports) < 2:
        return

    artifact_refs: list[str] = state.get("artifact_refs", [])

    try:
        consensus = ConsensusBuilder().build(reports, artifact_refs)
    except Exception:
        _logger.warning(
            "consensus synthesis failed for phase %s; continuing without it",
            phase,
            exc_info=True,
        )
        return

    from film_pipeline.orchestration.nodes._agent_artifacts import _save_artifact

    ref = _save_artifact(state, consensus, "consensus_report", phase)
    if ref:
        state["consensus_report_ref"] = ref
        state.setdefault("artifact_refs", []).append(ref)


__all__ = ["build_consensus_if_needed"]
