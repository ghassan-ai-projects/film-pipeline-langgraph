"""KB curator — ingestion, promotion, card creation, and maintenance.

The curator is responsible for:
- Ingesting raw material into the KB (pdfs, scripts, notes)
- Creating and updating KB item metadata cards
- Promoting items between authority levels (raw_archive → case_study, etc.)
- Detecting stale or superseded items
- Validating KB item references and source paths

Currently a stub. The KB contains 12 manually curated items in the manifest.
"""

from __future__ import annotations
