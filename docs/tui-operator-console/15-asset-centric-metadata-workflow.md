# Asset-Centric Metadata Workflow

## Purpose

The TUI should support navigation and targeted enhancement of reference images and other
metadata-rich creative assets.

This should generalize beyond scenes.

## Why It Matters

Creative control does not live only in text artifacts. It also lives in:

- reference images
- character reference sheets
- environment boards
- shot entries
- prompt metadata
- validation sidecars
- generation-plan rows

If the TUI only handles scenes and phase summaries well, it will still feel incomplete for
visual development and production planning.

## Main Requirement

A user must be able to:

- browse structured asset lists
- inspect asset metadata deeply
- compare asset versions
- request targeted enhancement of one asset or metadata record
- understand downstream impact of that enhancement

## Recommended Asset Families

Start with these first:

- reference images
- reference index entries
- character identity sheets
- environment boards
- shot rows
- generation-plan rows

## Reference Image Workflow

For each reference image or reference entry, the TUI should show:

- asset id
- subject type and subject id
- asset type
- provider and generation status
- quality score
- validation summary
- approval status
- prompt anchor metadata
- usage links to scenes, shots, or prompts

It should also define how the image itself is viewed:

- primary: terminal image preview when supported by the environment
- fallback: metadata-first view with file path, dimensions, and linked usage
- escape hatch: explicit open/export command for external visual inspection when terminal preview is insufficient

## Recommended Workspace

Use the dedicated `Artifacts` page as the asset-oriented workspace.

Recommended layout:

- asset family navigator
- asset list
- active asset metadata panel
- asset preview/details panel
- related usage/dependency panel
- asset actions panel

## Asset Actions

Required actions:

- `inspect metadata`
- `compare versions`
- `request enhancement`
- `mark for review`
- `jump to related scene`
- `jump to related shot`

Later possible actions:

- `rerun validator for this asset`
- `refresh prompt metadata from this asset`
- `regenerate dependent rows`

## Scope Rule

Like scene changes, asset enhancements must remain honest about scope.

Examples:

- improving a reference caption may be local
- changing a character identity reference may affect prompts, shot plans, and consistency checks
- changing environment metadata may affect lighting assumptions across multiple scenes

The TUI must show whether a requested enhancement is:

- local
- dependent
- broad-impact

## Recommended Backend Concepts

Add service concepts such as:

- `AssetSummary`
- `AssetDetail`
- `AssetMetadataView`
- `AssetEnhancementRequest`
- `AssetComparison`
- `AssetImpactPreview`

## Recommended Services

Likely responsibilities:

- `ArtifactService.list_assets(project_id, family)`
- `ArtifactService.get_asset_detail(project_id, asset_id)`
- `ArtifactService.get_reference_entry(project_id, reference_id)`
- `ReviewService.request_asset_enhancement(project_id, asset_id, notes)`
- `ValidationService.list_asset_issues(project_id, asset_id)`
- `CheckpointService.compare_asset_versions(project_id, asset_id, from_ref, to_ref)`

Asset workflow rule:

- `Artifacts` owns asset-targeted enhancement requests
- `Review` owns phase-level acceptance when the asset change affects reviewable candidate baselines

## Reference Image Metadata Details

For visual assets, metadata should expose:

- reference id
- asset path
- subject type
- subject id
- visual role
- provider
- generation parameters if available
- quality score
- ai usability score if available
- approval history
- dependent scenes or shots

## Relationship To Other Data

The same interaction model should extend to other structured data families:

- scene rows
- shot rows
- continuity entries
- prompt entries
- generation requests

Pattern:

- list
- detail
- issues
- compare
- enhance
- impact preview

## UX Requirements

### Navigation

- filter by asset family
- filter by subject
- filter by status
- jump from scene to related references
- jump from reference to related shots/scenes

### Enhancement

Enhancement notes should support:

- improve clarity
- improve consistency
- align with character identity
- align with environment rules
- raise quality
- refine metadata

### Comparison

Users should compare:

- approved asset vs candidate asset
- metadata version A vs metadata version B
- asset metadata vs upstream source constraints

## V1 Recommendation

Implement:

- reference-image list and detail
- reference metadata panel
- asset comparison
- targeted enhancement request
- impact preview

Delay:

- full image rendering pipeline inside TUI
- multi-asset batch enhancement
- direct metadata editing for every asset family

## Acceptance Criteria

- user can navigate reference images and related metadata efficiently
- user can request targeted enhancement for one asset
- user can understand dependencies and blast radius
- the same pattern can extend to other metadata-rich asset families
