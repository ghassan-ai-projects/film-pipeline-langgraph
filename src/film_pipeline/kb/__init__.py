"""Knowledge base operating model: manifest, retrieval, context packets.

The orchestrator never dumps the full KB into an agent prompt. Instead it
builds a :class:`KBContextPacket` per graph node with curated authority levels.
"""

from __future__ import annotations

from film_pipeline.kb.conflicts import KBConflictDetector
from film_pipeline.kb.manifest import KBManifest
from film_pipeline.kb.packets import KBContextPacketBuilder
from film_pipeline.kb.retrieval import KBRetrieval

__all__ = [
    "KBConflictDetector",
    "KBContextPacketBuilder",
    "KBManifest",
    "KBRetrieval",
]
