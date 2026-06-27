---
name: Recall AI
source: Stitch project 12113312558662173038
preview: https://stitch.withgoogle.com/preview/12113312558662173038
---

# Recall AI Design System (Light Theme)

Synced from Stitch HTML exports (Search Hub, Enhanced Search, My Library, Login, Marketing Landing).

## Core surfaces

| Token | Hex | Usage |
|-------|-----|-------|
| cream-bg | `#ffffff` | Page background (Search Hub, Enhanced Search, Auth, Landing) |
| background / surface | `#ffffff` | Page background (Library, Upload) |
| luminous-cream | `#ffffff` | Cards, filter panels, inputs |
| primary | `#002753` | Headlines, buttons, sidebar, match badges |
| on-primary | `#ffffff` | Text on primary surfaces |
| on-surface | `#1a1c20` | Body text |
| on-surface-variant | `#434750` | Secondary text, inactive chips |
| outline | `#737781` | Placeholders, borders |
| outline-variant | `#c3c6d1` | Dividers, input borders |

## Semantic status (from Stitch Library screen)

| State | Background | Text |
|-------|------------|------|
| Completed | `secondary-container/50` (`#ffdd67`) | `on-secondary-container` (`#766100`) |
| Processing | `secondary-container/30` | `secondary` (`#715c00`) |
| Failed | `error-container/50` (`#ffdad6`) | `on-error-container` (`#93000a`) |
| Pending | `surface-container` | `on-surface-variant` |

## Alerts

| Type | Classes |
|------|---------|
| Success | `alert-success` — primary-container tint |
| Error | `alert-error` — error-container tint |

## Navigation (sidebar)

- Background: `primary` (`#002753`)
- Inactive links: `text-primary-fixed-dim/70`
- Active link: `bg-primary-fixed-dim/10 text-on-primary`
- CTA button: `bg-primary-fixed-dim text-primary hover:bg-white`

## Top bar

- Background: `bg-surface` with `border-outline-variant/10`
- Search input: `bg-surface-container-low` with `rounded-full`
- Avatar: `bg-primary-fixed` (library) or `bg-primary-container` (enhanced search)

## Do not use

- Ad-hoc greens (`#10c469`, `#28a745`) — not in Stitch palette
- Legacy blues/purples (`#3498db`, `#9b59b6`)
- `text-on-primary-container` on small avatars — prefer `bg-primary text-on-primary`
