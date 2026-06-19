# film-pipeline-langgraph

LangGraph-based film creation pipeline for a professional, human-supervised AI film studio.

The goal is not a single prompt-to-video script. The project direction is a studio operating
system: an orchestrator agent coordinates many small expert agents, uses the existing film
knowledge base, validates work at many levels, and pauses for human review.

This project is MCP-first. OpenClaw should be the primary operator surface for creating
projects, submitting ideas, reviewing phases, approving work, inspecting artifacts, resuming
after errors, checking provider health, and rolling back to checkpoints. The LangGraph studio
runtime should be designed around MCP tool contracts from day one, not wrapped with MCP after
the core pipeline is built.

Agent prompts should follow the RCTCO framework from
`film-knowledge-base/prompt-framework.md`.

## Current Planning Docs

- [Vision and direction](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/vision-and-direction.md)
- [Fresh review](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/fresh-review.md)
- [Architecture blueprint](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/architecture-blueprint.md)
- [Agent architecture](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/agent-architecture.md)
- [Knowledge base operating model](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/kb-operating-model.md)
- [Remaining needs](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/remaining-needs.md)
- [E2E test scenarios](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/e2e-test-scenarios.md)
- [Reference image flow](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/reference-image-flow.md)
- [Environment consistency](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/environment-consistency.md)
- [Project intake](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/project-intake.md)
- [Versioning and checkpoints](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/versioning-and-checkpoints.md)
- [Multi-angle coverage](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/multi-angle-coverage.md)
- [Clip generation execution](/Users/ghassan/my-projects/film-pipeline-langgraph/docs/clip-generation-execution.md)

## Local Research Inputs

- `film-knowledge-base/` contains the existing film protocol, postmortem, scripts, skills,
  validation rubrics, project notes, PDFs, and lessons from previous films.
- `~/external-projects/agentic-drama-pipeline` is useful for typed workflow contracts and
  inspectable multi-agent outputs.
- `~/external-projects/ai-drama-engine-demo` is useful for practical QC reports, reference
  image handling, face consistency checks, and delivery summaries.
- `~/external-projects/VEO.IO` reinforces the platform/product framing.

## Immediate Direction

1. Keep the current docs as planning source of truth.
2. Convert the vision into MCP tools, schemas, graph phases, artifact contracts, and
   validation agents.
3. Build the first MVP around pre-production, review, and validation before spending budget
   on full generation.
