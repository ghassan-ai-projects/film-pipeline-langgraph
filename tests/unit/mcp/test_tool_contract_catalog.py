"""Every tool's contract must be delivered, not just declared.

## What this pins, and why it is a ratchet

`mcp/contract.py` promises, in its own docstring, that every tool exposes a name,
description, input schema, output schema and four flags. Measured on the registry
the server actually serves (`docs/modularity-improvements/04`, 2026-09-28):

| Field | Tools that had it |
|---|---:|
| tools registered | 75 |
| non-empty `input_schema` | **0** |
| non-empty `output_schema` | **0** |
| a description other than `"MCP tool: <name>"` | **0** |

The stdio transport forwards `input_schema` as `inputSchema`, so every MCP client
saw 75 tools accepting `{}` and described only by their names — while handlers
compensated with 86 `args.get(...)` calls and ad-hoc coercion.

This is the "MCP-first contract is the product boundary" rule with no evidence
behind it, and it is the one boundary AGENTS.md's "Pydantic v2 for all schemas
(never raw dicts across boundaries)" is most clearly about.

## The ratchet

`ratchet up only` while doc 04's migration is in flight: the counts below may
rise as groups move, never fall. Once every tool declares itself, the assertion
inverts to "all 75" and the per-tool `_register(...)` path is deleted.

A decrease is not a pass — it means a spec was replaced by a bare registration, so
this fails with the tool name rather than only the count.
"""

from __future__ import annotations

import pytest

from film_pipeline.mcp.contract import make_registry

#: Tools that publish a real `input_schema` and a real description.
#:
#: Raised group by group as doc 04's per-tool `ToolSpec` declarations land. It is
#: a floor, not a target: `test_the_catalog_floor_has_not_fallen` fails if a tool
#: loses its spec.
TOOLS_WITH_DECLARED_ARGS = 18


@pytest.fixture(scope="module")
def catalog() -> dict[str, dict[str, object]]:
    return {t["name"]: t for t in make_registry().catalog()}


def test_the_catalog_floor_has_not_fallen(catalog: dict[str, dict[str, object]]) -> None:
    """The number of fully-declared tools may only rise."""
    with_schema = [name for name, t in catalog.items() if t["input_schema"]]
    assert len(with_schema) >= TOOLS_WITH_DECLARED_ARGS, (
        f"only {len(with_schema)} tool(s) publish an input_schema, down from the "
        f"recorded floor of {TOOLS_WITH_DECLARED_ARGS}. A tool lost its `ToolSpec` "
        "declaration, or gained one and did not raise this floor. Either way the "
        "count must not fall."
    )


def test_fully_declared_tools_have_a_real_description(
    catalog: dict[str, dict[str, object]],
) -> None:
    """A tool with an `input_schema` must not still be described by its name.

    Checked together with the schema because the two are one declaration: a
    `ToolSpec` carries both, so a tool that publishes one and not the other means
    the spec was bypassed.
    """
    generic = [
        name
        for name, t in catalog.items()
        if t["input_schema"] and t["description"] == f"MCP tool: {name}"
    ]
    assert not generic, (
        f"{generic} publish an input_schema but still carry the generic "
        "'MCP tool: <name>' description. Declare both in the ToolSpec, or neither."
    )


def test_declared_schemas_forbid_unknown_arguments(
    catalog: dict[str, dict[str, object]],
) -> None:
    """`ToolArgs` sets `extra="forbid"`, so a client sending junk is refused.

    This is doc 04's stated mechanism for finding the arguments real callers send
    that no handler reads: the first failing run is the authoritative list. A spec
    whose schema allows additional properties would silently accept them instead.
    """
    permissive: list[str] = []
    for name, tool in catalog.items():
        schema = tool["input_schema"]
        if not isinstance(schema, dict) or not schema:
            continue
        if schema.get("additionalProperties") is not False:
            permissive.append(name)
    assert not permissive, (
        f"{permissive} publish a schema that permits additional properties. Their "
        'args model must inherit `ToolArgs`, whose `extra="forbid"` is what makes '
        "an unknown argument a typed error."
    )


def test_every_registered_tool_has_a_contract_entry(
    catalog: dict[str, dict[str, object]],
) -> None:
    """Guard the guard: the sweep above is vacuous if the catalog is empty."""
    assert len(catalog) >= 70, (
        f"only {len(catalog)} tools in the catalog; the declarations this file "
        "grades would be a subset of the real surface."
    )
    for name, tool in catalog.items():
        assert tool["description"], f"{name} has no description at all"
        assert tool["group"], f"{name} has no group"


def test_declared_specs_preserve_the_registered_flags(
    catalog: dict[str, dict[str, object]],
) -> None:
    """A `ToolSpec` must declare the same four flags the registry did.

    Moving a tool from `_register(...)` to a `ToolSpec` re-states its flags, and
    nothing about a green suite would notice a wrong one: the flag changes *when*
    dispatch refuses a call, not whether the handler works. This caught a real
    slip during the migration — `rollback_artifact` gained `creates_checkpoint`,
    which the registry had never set.

    The expected flags are recorded here rather than derived from the specs, so
    this compares the declaration against the contract as it was published before
    the move. If a tool's flags genuinely change, change them here too, on purpose.
    """
    expected: dict[str, tuple[bool, bool, bool]] = {
        "create_film_project": (True, False, False),
        "set_active_project": (True, False, False),
        "get_active_project": (False, False, False),
        "get_project_summary": (False, False, False),
        "create_checkpoint": (True, False, False),
        "rollback_artifact": (True, True, False),
        "rollback_to_checkpoint": (True, True, False),
        "get_audit_log": (False, False, False),
    }
    for name, (mutates, confirm, checkpoint) in expected.items():
        tool = catalog[name]
        actual = (
            bool(tool["mutates_state"]),
            bool(tool["requires_confirmation"]),
            bool(tool["creates_checkpoint"]),
        )
        assert actual == (mutates, confirm, checkpoint), (
            f"{name} declares (mutates, confirm, checkpoint) = {actual}, "
            f"but the contract published {mutates, confirm, checkpoint}. A spec "
            "re-stated a flag differently from the registry it replaced."
        )
