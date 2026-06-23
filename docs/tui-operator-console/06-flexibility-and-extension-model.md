# Flexibility And Extension Model

## Main Requirement

The TUI must stay useful as the studio expands across:

- more phases
- more providers
- more validators
- more artifact types
- more operating modes

## Design Strategy

Build the TUI around registries, typed view models, and pluggable screens, not hard-coded
phase assumptions scattered everywhere.

## Flexibility Dimensions

### 1. Phase growth

The graph already spans intake through delivery. The TUI should not assume only the current
subset in the README.

Requirement:

- navigation should render phase metadata from config or schemas
- phase badges and timelines should tolerate new phases

### 2. Tool growth

The MCP catalog will evolve.

Requirement:

- client should cache the tool catalog
- commands should degrade cleanly if a tool is unavailable

### 3. Artifact growth

New artifact types should not require redesigning the whole UI.

Requirement:

- default renderer: metadata + pretty JSON/markdown/plain text
- specialized renderers only where they add clear value

### 4. Mode growth

The system already distinguishes `mock` and `real`, and should explicitly distinguish
workflow modes such as `manual`, `hybrid`, and `automatic`.

Requirement:

- runtime mode must be visible globally
- workflow mode must be visible globally
- actions with real spend must change copy, color, and confirmation level

### 5. Headless and partial automation

The product supports auto-approve profiles and should promote workflow behavior into a
first-class project setting.

Requirement:

- the TUI should show when a project is manual, hybrid, or effectively headless
- the operator must understand whether workflow behavior came from profile default or project override

## Plugin-Oriented TUI Architecture

Do not over-engineer this in V1, but leave room for:

- screen registration
- widget registration
- renderer registration by artifact type
- command registration

A simple internal registry is enough.

## Configuration Model

Recommended TUI config areas:

- theme
- refresh intervals
- default landing tab
- compact vs comfortable density
- visible columns by screen
- confirmation strictness

Store this separately from project data.

## Internationalization

Not a near-term priority.

Do not design the copy system around hard-coded terminal strings everywhere. Centralized UI
labels will keep this possible later with low rework.

## Accessibility

Terminal UI accessibility is constrained, but still important.

Requirements:

- all actions reachable by keyboard
- color not the only status signal
- concise labels
- focus state always visible
- long content readable with scrolling and search

## Scalability Limits To Plan For

### Project count

Tens of projects should be comfortable. Hundreds require search, filters, and paging.

### Artifact count

Artifact browsers need pagination and lazy detail loading.

### Long text

Script and treatment views need search, jump-to-section, and wrap toggles.

### Generation volume

If reference or batch generation grows, provider views need summary-first, row-detail-second
patterns.

## Maintainability Rules

- keep transport code separate from widgets
- keep view-model mapping separate from rendering
- avoid screen-specific copies of the same MCP call logic
- prefer composition over giant monolithic screens
