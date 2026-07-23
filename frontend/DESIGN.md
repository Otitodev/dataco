# Dataco Design System

A minimal, Apple-flavoured system for a data-trust triage tool, following the
spirit of Apple's [Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines):

- **Clarity** — the system typeface at legible sizes, generous whitespace, and
  strong contrast. Text is the interface.
- **Deference** — quiet neutrals and soft, rounded surfaces stay out of the way.
  Chrome recedes so the content (the issues) leads.
- **Depth** — a light grouped background with white cards and gentle elevation on
  hover gives a subtle sense of layers, never heavy borders or drop shadows.

One rule carries the product: **colour appears only where it means something.**
The interface is neutral; the severity scale is the single place colour is used,
so a splash of red always means *critical* and nothing competes with it.

Everything lives in [`src/app.css`](./src/app.css) (tokens) and
[`src/lib/`](./src/lib) (logic + components). Change a token there and it
propagates everywhere — nothing is hardcoded in a screen.

**Scope:** light mode only for now. Dark-mode tokens are a later addition.

---

## Tokens

Defined as Tailwind v4 `@theme` variables in `app.css`, so each becomes a
utility (`bg-brand`, `text-ink-900`, `bg-severity-critical`, …).
**Every colour pair below passes WCAG AA**, verified with the contrast formula.

### Surfaces & label hierarchy

| Token | Hex | Use | AA on white / page |
|---|---|---|---|
| `surface-page` | `#F5F5F7` | App canvas (grouped background) | — |
| `surface-card` | `#FFFFFF` | Cards, header | — |
| `surface-sunken` | `#ECECEE` | Hovers, chips, resolved pills | — |
| `ink-900` | `#1D1D1F` | Primary text (label) | 16.8 / 15.5 |
| `ink-600` | `#55555A` | Body / secondary text | 7.4 / 6.8 |
| `ink-400` | `#6E6E73` | Meta, captions, placeholders | 5.1 / 4.7 |
| `line` | `#D2D2D7` | Hairline separators | — |

The three ink levels mirror Apple's label / secondaryLabel / tertiaryLabel — but
tuned so **even the lightest passes AA** (Apple's own tertiary does not).

### Accent

| Token | Hex | Use |
|---|---|---|
| `brand` | `#0071E3` | Links, primary buttons, focus ring (AA 4.7) |
| `brand-ink` | `#0058B0` | Button hover / pressed |

Apple system blue — the one accent. Used for actions and navigation, never decoration.

### Severity scale (the only intentional colour)

Each level has three roles: **vivid** (the status dot, an iOS system colour),
**tint** (badge background), **ink** (badge text, darkened to pass AA on the tint).

| Level | Vivid | Tint | Ink | AA (ink/tint) |
|---|---|---|---|---|
| `critical` | `#FF3B30` | `#FFECEB` | `#C4271D` | 5.05 |
| `high` | `#FF9500` | `#FFF2E0` | `#985A00` | 5.01 |
| `medium` | `#FFCC00` | `#FFF8DB` | `#8A6D00` | 4.62 |
| `low` | `#007AFF` | `#E6F0FE` | `#0058B0` | 6.04 |
| `resolved` | `#8E8E93` | — | — | — |

Note: `low`/high-confidence share the blue family, and `resolved`/low-confidence
share neutral — a deliberate "blue reads calm/good, grey reads inactive"
mapping, not an accident.

### Type

The **system font stack** — SF Pro on Apple platforms, Segoe UI on Windows — so
the UI looks native and loads zero web fonts. Hierarchy comes from size and
weight, not from switching families.

| Token | Stack | Use |
|---|---|---|
| `font-sans` | `-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", …` | Everything |
| `font-mono` | `ui-monospace, "SF Mono", Menlo, …` | Real code only — schema field listings |

**Type scale** (the ladder used across screens; keep to it):

| Role | Classes |
|---|---|
| Page title | `text-3xl font-semibold tracking-tight` |
| Detail title | `text-2xl font-semibold tracking-tight` |
| Card / section title | `text-sm font-semibold` |
| Body | `text-[15px] text-ink-600` (relaxed leading for prose) |
| Card item title | `text-[15px] font-semibold tracking-tight` |
| Caption / meta | `text-xs text-ink-400` |

Numbers that sit in columns or update (counts) use `tabular-nums`.

---

## Components

In [`src/lib/components/`](./src/lib/components). Import via `$lib/components/X.svelte`.

| Component | Props | Purpose |
|---|---|---|
| `Card.svelte` | `href?`, `class?`, `children` | Rounded-2xl white surface with a hairline border; lifts on hover when it's a link (`href`). No severity styling — colour stays in the badge. |
| `IssueCard.svelte` | `issue` | Dashboard card — severity badge, asset name, owner, blast-radius count. |
| `SeverityBadge.svelte` | `severity` | Pill: tinted background, dark ink label, vivid status dot. |
| `StatusPill.svelte` | `status` | active / investigating / resolved. |
| `ConfidenceLabel.svelte` | `confidence` | high / medium / low confidence. |

### Shared logic

- [`src/lib/severity.ts`](./src/lib/severity.ts) — the **single source of truth**
  for severity / status / confidence styling and `sortBySeverity()`. Class
  strings are complete literals so Tailwind's scanner picks them up; **never
  build a Tailwind class by string interpolation.**
- [`src/lib/format.ts`](./src/lib/format.ts) — `timeAgo()` and `humanize()`.

---

## Conventions

- **Colour = meaning.** The neutral palette carries the whole UI; reach for a
  severity colour only to signal severity. No decorative colour.
- **One source of truth per concept.** Need a severity colour anywhere? Read it
  from `severity.ts`, never re-derive it in a component.
- **Shape:** cards are `rounded-2xl`, pills and buttons are `rounded-full`, chips
  are `rounded-md`. Borders are the single hairline `line`; lean on whitespace
  and elevation over rules.
- **Copy is UI.** Empty states invite action ("All clear — new issues appear
  here…"); errors say what broke and how to fix it. Buttons name the action and
  keep that name through the flow.
- **Quality floor:** keyboard focus is a themed 2px brand ring applied globally
  via `:focus-visible` in `app.css` (never the browser default), layouts reflow
  to one column on mobile, and motion is disabled under `prefers-reduced-motion`.

---

## Extending

- **New status/severity value:** add it to the map in `severity.ts` and every
  component updates automatically.
- **New surface or accent:** add a `--color-*` token in `app.css` `@theme` and
  use it as `bg-*` / `text-*` / `border-*`. Don't reach for raw Tailwind palette
  colours (`gray-500`, `blue-600`) in screens — they bypass the system. Verify
  any new text/background pair reaches AA (4.5:1) before shipping it.
- **New component:** compose from `Card` + the badges; keep it presentational and
  pull styling tokens from `severity.ts`.
- **Dark mode (later):** add a `@media (prefers-color-scheme: dark)` block that
  re-maps the surface and ink tokens; components won't need to change.
