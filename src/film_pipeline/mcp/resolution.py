"""Project resolution: exact id → slug → title → alias → fuzzy → ask.

Implemented as an in-memory registry. A future phase may back it with the
artifact store, but the contract is the same.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher


@dataclass
class ProjectRecord:
    """Lightweight in-memory project record used for resolution."""

    project_id: str
    slug: str
    title: str
    aliases: list[str] = field(default_factory=list)


@dataclass
class ResolutionResult:
    """The outcome of resolving a project reference."""

    candidates: list[ProjectRecord]
    resolved: ProjectRecord | None = None
    ambiguous: bool = False

    @property
    def count(self) -> int:
        return len(self.candidates)


class AmbiguousProjectError(Exception):
    """Raised when a destructive action is requested on an ambiguous ref."""

    def __init__(self, candidates: list[ProjectRecord], ref: str) -> None:
        super().__init__(f"Ambiguous project reference '{ref}' matched {len(candidates)} projects")
        self.candidates = candidates
        self.ref = ref


class ProjectRegistry:
    """Tracks projects and resolves references.

    Resolution order: exact project_id → slug → title → alias → fuzzy.
    Destructive actions require an explicit resolved project.
    """

    def __init__(self) -> None:
        self._projects: list[ProjectRecord] = []

    def register(self, record: ProjectRecord) -> None:
        self._projects.append(record)

    def all(self) -> list[ProjectRecord]:
        return list(self._projects)

    def resolve(self, ref: str) -> ResolutionResult:
        """Resolve a reference, returning all candidates (best match first)."""
        if not ref:
            return ResolutionResult(candidates=[])
        candidates = self._exact_matches(ref)
        if candidates:
            return ResolutionResult(
                candidates=candidates,
                resolved=candidates[0],
                ambiguous=len(candidates) > 1,
            )
        candidates = self._fuzzy_matches(ref, threshold=0.7)
        return ResolutionResult(
            candidates=candidates,
            resolved=candidates[0] if len(candidates) == 1 else None,
            ambiguous=len(candidates) > 1,
        )

    def resolve_or_raise(self, ref: str) -> ProjectRecord:
        """Resolve a reference, raising on ambiguity or no match."""
        result = self.resolve(ref)
        if result.ambiguous:
            raise AmbiguousProjectError(result.candidates, ref)
        if result.resolved is None:
            raise KeyError(f"Unknown project reference: {ref}")
        return result.resolved

    def _exact_matches(self, ref: str) -> list[ProjectRecord]:
        ref_l = ref.lower()
        out: list[ProjectRecord] = []
        for p in self._projects:
            if (
                p.project_id == ref
                or p.slug == ref
                or p.title == ref
                or ref_l in (a.lower() for a in p.aliases)
            ):
                out.append(p)
        if not out:
            for p in self._projects:
                if p.slug.lower().startswith(ref_l) or p.title.lower().startswith(ref_l):
                    out.append(p)
        return out

    def _fuzzy_matches(self, ref: str, threshold: float) -> list[ProjectRecord]:
        scored: list[tuple[float, ProjectRecord]] = []
        for p in self._projects:
            candidates = [p.project_id, p.slug, p.title, *p.aliases]
            best = max(SequenceMatcher(None, ref.lower(), c.lower()).ratio() for c in candidates)
            if best >= threshold:
                scored.append((best, p))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored]
