"""Matrix patch artifacts — row-level updates without whole-matrix replacement.

Each downstream phase emits a ``MatrixPatch`` artifact that updates individual
rows of the Master Film Matrix. Patches are layered on top of the base matrix
via ``materialize_matrix()``.
"""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas._base import SchemaBase


class MatrixRowUpdate(SchemaBase):
    """A single row field update within a matrix patch."""

    shot_id: str = Field(description="Target shot row identifier.")
    set: dict[str, object] = Field(
        default_factory=dict,
        description="Fields to set, e.g. {'prompt_ref': '...', 'status': 'prompted'}.",
    )
    append: dict[str, list[object]] = Field(
        default_factory=dict,
        description="Fields to append to, e.g. {'asset_refs': ['gen/shot_0001.mp4']}.",
    )
    old_values: dict[str, object] = Field(
        default_factory=dict,
        description="Previous values for rollback support.",
    )


class MatrixPatch(SchemaBase):
    """A versioned patch to the Master Film Matrix.

    Applied on top of a base matrix. Multiple patches can be layered.
    """

    patch_id: str = Field(description="Unique identifier, e.g. 'gen_planning_batch_001'.")
    matrix_ref: str = Field(description="Base matrix ref this patch applies to.")
    phase: str = Field(description="Phase that produced this patch.")
    reason: str = Field(default="", description="Why this patch was created.")
    updates: list[MatrixRowUpdate] = Field(
        default_factory=list,
        description="Row-level updates to apply.",
    )
    created_by_agent: str = Field(default="", description="Agent that produced this patch.")

    def apply_to(self, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        """Apply this patch to a list of row dicts. Returns modified rows."""
        row_map: dict[str, dict[str, object]] = {}
        ordered_ids: list[str] = []
        for r in rows:
            sid = str(r.get("shot_id", ""))
            if sid not in row_map:
                ordered_ids.append(sid)
            row_map[sid] = r

        for update in self.updates:
            row = row_map.get(update.shot_id)
            if row is None:
                continue

            # Record old values for rollback
            for key in update.set:
                update.old_values[key] = row.get(key)
            for key in update.append:
                existing_val: object = row.get(key, [])
                update.old_values[key] = list(existing_val) if isinstance(existing_val, list) else []

            # Apply set
            row.update(update.set)

            # Apply append
            for key, values in update.append.items():
                existing = row.get(key, [])
                if not isinstance(existing, list):
                    existing = []
                row[key] = list(existing) + list(values)

        return [row_map[sid] for sid in ordered_ids]
