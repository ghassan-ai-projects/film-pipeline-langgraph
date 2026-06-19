"""Knowledge base operating model: manifest, retrieval, context packets.

The orchestrator never dumps the full KB into an agent prompt. Instead it
builds a :class:`KBContextPacket` per graph node with curated authority levels.
"""

from __future__ import annotations
