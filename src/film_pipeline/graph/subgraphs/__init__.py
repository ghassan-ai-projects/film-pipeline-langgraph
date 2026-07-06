"""Phase subgraphs — internal graphs wired into the supervisor graph.

Currently only QC has a real subgraph (parallel validator fan-out); the
other phases run as plain nodes in film_pipeline.graph.nodes.
"""

from __future__ import annotations
