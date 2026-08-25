"""KB context packet builder — assembles governed KB slices per agent/task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from film_pipeline.kb.conflicts import KBConflictDetector
from film_pipeline.kb.manifest import KBManifest
from film_pipeline.kb.retrieval import KBRetrieval
from film_pipeline.schemas.kb import KBContextPacket, KBExcludedRef


def _resolve_authority_layers(
    detector: KBConflictDetector, retrieved: dict[str, list[Any]]
) -> tuple[list[Any], list[Any], list[Any], list[Any]]:
    """Resolve authority conflicts and supersessions across retrieved layers."""
    canonical, c_excluded = detector.resolve_authority(retrieved["canonical"])
    playbooks, p_excluded = detector.resolve_authority(retrieved["playbooks"])
    case_studies, cs_excluded = detector.resolve_authority(retrieved["case_studies"])

    # Also handle supersessions
    canonical, sup_excluded = detector.resolve_superseded(canonical)
    return canonical, playbooks, case_studies, c_excluded + p_excluded + cs_excluded + sup_excluded


def _note_unresolved_conflicts(conflicts: list[Any], all_excluded: list[KBExcludedRef]) -> None:
    """Record unresolved conflicts as excluded refs with reasons."""
    # If there are unresolved conflicts, note them in excluded
    for conflict in conflicts:
        if not conflict.resolved:
            all_excluded.append(
                KBExcludedRef(
                    ref=conflict.items[-1],
                    reason=f"Conflict with {conflict.items[0]}: {conflict.description}",
                )
            )


def _build_payload_map(items: list[Any]) -> dict[str, str]:
    """Map kept item ids to their first source path."""
    payload: dict[str, str] = {}
    for item in items:
        if item.source_refs:
            payload[item.id] = item.source_refs[0]
    return payload


@dataclass
class KBContextPacketBuilder:
    """Assembles a KBContextPacket for a specific agent and task.

    Input: project_id, phase, agent_id, task
    Output: governed KBContextPacket with authority-ordered refs
    """

    manifest: KBManifest

    def build(
        self,
        *,
        project_id: str,
        phase: str,
        agent_id: str,
        task: str,
    ) -> KBContextPacket:
        """Build a complete context packet for one agent task.

        Retrieval order:
        1. Canonical policies (deterministic + tagged)
        2. Active playbooks (tagged)
        3. Case study lessons (tagged)
        4. Conflict resolution (authority hierarchy)
        5. Excluded refs recorded with reasons
        """
        retrieval = KBRetrieval(self.manifest)
        detector = KBConflictDetector(self.manifest)

        # Layered retrieval
        retrieved = retrieval.for_task(
            phase=phase,
            agent_id=agent_id,
        )

        # Resolve conflicts within each authority layer
        canonical, playbooks, case_studies, all_excluded = _resolve_authority_layers(
            detector, retrieved
        )

        # Detect cross-authority conflicts
        all_kept = canonical + playbooks + case_studies
        conflicts = detector.detect_conflicts(all_kept)
        _note_unresolved_conflicts(conflicts, all_excluded)

        # Map to ref ids
        authority_refs = [item.id for item in canonical]
        playbook_refs = [item.id for item in playbooks]
        case_study_refs = [item.id for item in case_studies]

        return KBContextPacket(
            kb_context_id=f"kbctx:{project_id}:{agent_id}:{uuid4().hex[:8]}",
            project_id=project_id,
            phase=phase,
            agent_id=agent_id,
            task=task,
            authority_policy_refs=authority_refs,
            playbook_refs=playbook_refs,
            case_study_refs=case_study_refs,
            examples=[],
            excluded_refs=all_excluded,
            payload=_build_payload_map(all_kept),
        )
