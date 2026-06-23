# TUI Pages

This folder defines the concrete page model for the TUI.

The goal is to turn the broader architecture into implementable screens with:

- navigation role
- purpose
- primary user
- required data
- actions
- cross-links
- state and refresh behavior

## Navigation Model

Recommended top-level navigation:

- `Project Create`
- `Dashboard`
- `Review`
- `Structure`
- `Scenes`
- `Assets`
- `Validation`
- `Checkpoints`
- `Providers`
- `Audit`
- `Project Settings`

## Navigation Principles

### 1. Start broad, drill narrow

Typical flow:

`Dashboard -> Review/Structure/Scenes/Assets -> focused action -> refresh -> back to summary`

### 2. Support multiple working levels

The TUI must support:

- project level
- act level
- scene level
- asset/metadata level
- phase/review level
- operational/recovery level

### 3. Keep context stable

Moving between pages should preserve:

- active project
- active workflow mode
- selected act, scene, or asset where possible
- pending drafts that are safe to preserve locally

## Recommended Hotkeys

- `g n`: Project Create
- `g d`: Dashboard
- `g r`: Review
- `g t`: Structure
- `g s`: Scenes
- `g a`: Assets
- `g v`: Validation
- `g c`: Checkpoints
- `g p`: Providers
- `g u`: Audit
- `g ,`: Project Settings

## Files

1. [00-navigation-map.md](./00-navigation-map.md)
2. [01-project-create-page.md](./01-project-create-page.md)
3. [01-dashboard-page.md](./01-dashboard-page.md)
4. [02-review-page.md](./02-review-page.md)
5. [03-structure-page.md](./03-structure-page.md)
6. [04-scenes-page.md](./04-scenes-page.md)
7. [05-assets-page.md](./05-assets-page.md)
8. [06-validation-page.md](./06-validation-page.md)
9. [07-checkpoints-page.md](./07-checkpoints-page.md)
10. [08-providers-page.md](./08-providers-page.md)
11. [09-audit-page.md](./09-audit-page.md)
12. [10-project-settings-page.md](./10-project-settings-page.md)
