# 04 — The MCP contract is declared, not delivered

**Priority: 2 (the product boundary; a stated project rule).** Size: M, one tool group
per commit.

## Finding

`mcp/contract.py` promises, in its module docstring, that every tool exposes a name,
description, input schema, output schema, and four flags. Measured on the registry the
server actually serves (`make_registry().catalog()`):

| Field | Tools that have it |
|---|---:|
| tools registered | 75 |
| non-empty `input_schema` | **0** |
| non-empty `output_schema` | **0** |
| a description other than `"MCP tool: <name>"` | **0** |
| `creates_checkpoint=True` | 1 — and the flag is **never read** outside `contract.py`/`registry.py` |
| `idempotency_key_field` set | 0 — also never read |

The stdio transport forwards `input_schema` as `inputSchema`
([_stdio_transport.py:39](../../src/film_pipeline/mcp/_stdio_transport.py)), so every
MCP client sees 75 tools that accept `{}` and are described only by their names.
Handlers compensate by parsing `args.get(...)` **86 times** with ad-hoc coercion
(`_coerce_runtime_arg`, `bool(args.get("confirmed"))`, `str(args.get("note", ""))`).

AGENTS.md: *"Use Pydantic v2 for all schemas (never raw dicts across boundaries)."* The
MCP boundary is the one boundary the blueprint calls the product surface, and it is
the one boundary with raw dicts on both sides.

### The tool list is declared three times

| Place | Entries |
|---|---:|
| `mcp/registry.py` — import block + `_register(...)` calls | 75 |
| `mcp/tools/__init__.py` — `_TOOL_MODULES` name -> module map (PEP 562 lazy facade) | 76 (75 + `register_all_tools`) |
| `mcp/tools/__init__.pyi` — type stub for the lazy facade | 75 |

They agree today (the measurement script checks this). Adding a tool means editing all
three plus the handler module; the facade exists so `registry` can import handlers
lazily and so tests can monkeypatch `get_runtime` on the package — both of which doc 01
removes the need for.

## Recommendation

### Slice 1 — the tool declaration is the handler's module

Declare each tool once, next to its handler:

```python
class ApprovePhaseArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmed: bool = False
    note: str = ""

APPROVE_PHASE = ToolSpec(
    name="approve_phase",
    group=ToolGroup.REVIEW,
    description="Approve the current phase's human gate and advance.",
    args=ApprovePhaseArgs,
    mutates=True, confirm=True, active_project=True,
    handler=approve_phase,
)
```

`registry.py` becomes a list of specs per tool group; `input_schema` is
`ApprovePhaseArgs.model_json_schema()`; dispatch validates `args` with the model before
calling the handler, so the 86 `args.get` sites become attribute reads on a typed
object. Delete `_TOOL_MODULES` and the `.pyi` stub when the last group moves.

`extra="forbid"` is the same experiment that produced the 96-failure work list in the
schemas round: it will enumerate every caller passing an argument no handler reads.

**Falsifiable check (per group):** the measurement script's "with input_schema" count
rises by the group's size; a dispatch test sends an unknown argument and gets a typed
validation error instead of silent acceptance.

### Slice 2 — delete or honour the dead flags

`creates_checkpoint` and `idempotency_key_field` are published in the catalog and read
by nothing. Either dispatch implements them (checkpoint after a successful mutating
call; reject a repeated idempotency key), or delete them. Publishing a flag no code
honours is a contract claim with no evidence behind it.

### Slice 3 — output models where a consumer exists

Only add `output_schema` for tools whose output another program parses (the CLI driver
reads `ok`, `state`, `error`). Everything else can stay a dict until a consumer needs
it — do not model outputs speculatively.

## Guard to leave behind

Add a catalog test (`tests/unit/test_mcp.py` already builds the catalog but asserts no schema content): every registered tool has a non-empty `input_schema`
and a non-generic description. Ratchet it by group while the migration is in flight
(count of compliant tools may only rise), then make it absolute.

## What this does not establish

Which argument names clients actually send today. Before tightening with
`extra="forbid"`, grep the CLI driver, `scripts/`, and any operator docs for the
arguments they pass; the first failing run is the authoritative list.
