"""Layered KB retrieval — deterministic, tagged, and semantic lookups."""

from __future__ import annotations

from dataclasses import dataclass

from film_pipeline.kb.manifest import KBManifest
from film_pipeline.schemas._base import KbAuthority
from film_pipeline.schemas.kb import KBItemMetadata


@dataclass
class KBRetrieval:
    """Layered retrieval engine: deterministic → tagged → example.

    Usage::

        manifest = KBManifest.from_yaml(path)
        retrieval = KBRetrieval(manifest)
        items = retrieval.for_task(phase="generation", agent_id="generation-agent")
    """

    manifest: KBManifest

    def deterministic(self, item_ids: list[str]) -> list[KBItemMetadata]:
        """Retrieve items by exact id, ignoring authority or status."""
        result: list[KBItemMetadata] = []
        for item_id in item_ids:
            item = self.manifest.get(item_id)
            if item is not None:
                result.append(item)
        return result

    def by_tags(
        self,
        *,
        phase: str | None = None,
        agent_id: str | None = None,
        domain: str | None = None,
        authority: KbAuthority | None = None,
    ) -> list[KBItemMetadata]:
        """Tag-based retrieval — filter by phase, agent, domain, authority."""
        items = self.manifest.active_only()

        if authority is not None:
            items = [i for i in items if i.authority == authority]
        if phase is not None:
            items = [
                i for i in items if "all" in i.applies_to_phases or phase in i.applies_to_phases
            ]
        if agent_id is not None:
            items = [
                i for i in items if "all" in i.applies_to_agents or agent_id in i.applies_to_agents
            ]
        if domain is not None:
            items = [i for i in items if domain in i.domains]

        return items

    def examples(
        self,
        *,
        phase: str | None = None,
        domain: str | None = None,
    ) -> list[KBItemMetadata]:
        """Retrieve example/format items only."""
        return self.by_tags(
            phase=phase,
            domain=domain,
            authority=KbAuthority.CASE_STUDY,
        )

    def for_task(
        self,
        *,
        phase: str,
        agent_id: str,
        required_policy_ids: list[str] | None = None,
    ) -> dict[str, list[KBItemMetadata]]:
        """Layered retrieval for a specific agent task.

        Returns a dict keyed by authority level for packet assembly.
        """
        result: dict[str, list[KBItemMetadata]] = {
            "canonical": [],
            "playbooks": [],
            "case_studies": [],
        }

        # Layer 1: Deterministic — always include required canonical rules
        if required_policy_ids:
            result["canonical"] = self.deterministic(required_policy_ids)

        # Layer 2: Tagged — canonical policies for this phase+agent
        canonical = self.by_tags(
            phase=phase,
            agent_id=agent_id,
            authority=KbAuthority.CANONICAL,
        )
        for item in canonical:
            if item not in result["canonical"]:
                result["canonical"].append(item)

        # Layer 3: Tagged — active playbooks for this phase+agent
        result["playbooks"] = self.by_tags(
            phase=phase,
            agent_id=agent_id,
            authority=KbAuthority.ACTIVE_PLAYBOOK,
        )

        # Layer 4: Case studies (risks and lessons)
        result["case_studies"] = self.by_tags(
            phase=phase,
            agent_id=agent_id,
            authority=KbAuthority.CASE_STUDY,
        )

        return result
