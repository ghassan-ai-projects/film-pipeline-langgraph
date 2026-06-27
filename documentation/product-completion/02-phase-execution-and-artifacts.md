# 02 Phase Execution And Artifacts

---

## Goal

Turn every core phase into real artifact-producing work.

Core phases:

- intake
- constitution
- development
- script
- visual development
- shot bible
- generation planning
- generation
- QC

---

## Final Product Result

When this area is complete:

- each phase creates real typed artifacts
- downstream phases consume upstream artifacts
- artifact lineage is inspectable
- the project can be inspected at any phase and show meaningful outputs

---

## Required Artifact Outputs

### Intake

- project profile artifact
- intake analysis artifact
- approval-ready config summary

### Constitution

- film constitution artifact

### Development

- treatment artifact
- scene intent artifact set

### Script

- story bible artifact
- script artifact

### Visual Development

- character bible artifacts
- environment bible artifacts
- reference strategy artifact
- approved reference manifest

### Shot Bible

- shot bible artifact
- continuity ledger artifact
- master film matrix artifact

### Generation Planning

- prompt package artifacts
- provider plan artifact
- spend plan artifact

### Generation

- generation ledger artifacts
- generated clip artifacts
- extracted frame or preview artifacts

### QC

- QC validation bundle
- continuity review bundle

### External Handoff

- validated clip inventory
- prompt/reference archive for downstream editorial
- validation summary for manual finishing

---

## Required Metadata

Every artifact must include:

- artifact id
- artifact type
- project id
- phase
- version
- status
- parent refs
- created by
- reviewed by
- validation refs
- approval ref
- KB context ref

---

## Concrete Tests

### Unit Tests

- artifact write/read roundtrip
- metadata completeness
- artifact version supersession
- lineage relationships

### Integration Tests

- phase executor writes expected artifact types
- downstream phase consumes upstream artifact refs
- revision creates new artifact version without deleting prior approved version

### Final Acceptance Tests

- `idea -> constitution -> development -> script` produces real persisted artifacts
- visual development produces approved references before shot-bible work is allowed
- generation planning consumes approved upstream artifacts only
- generation and QC produce inspectable clip-level outputs and validation evidence for external finishing

---

## Acceptance Criteria

This area is done only when all of the following are true:

- every core phase writes at least one typed artifact
- no core phase is represented only by phase labels
- every artifact has complete metadata and lineage
- downstream phases consume stored artifacts, not reconstructed ad hoc inputs
- version history remains available after revisions
