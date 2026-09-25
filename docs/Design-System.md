# Acestream Scraper Design System

This document describes the visual language, interaction rules, and reusable UI
patterns used by the Acestream Scraper frontend. It is a contributor guide for
extending the interface without fragmenting its appearance or behavior.

The executable sources of truth are:

- `frontend/src/theme.ts` for tokens, typography, motion, and Material UI
  component overrides.
- `frontend/src/theme.d.ts` for the typed token contract.
- `frontend/src/components/layout/` for the application shell and page
  composition primitives.
- `frontend/src/components/state/` for shared empty and inline status states.
- `frontend/src/styles/` for responsive layout helpers.

If this document and the implementation disagree, update both in the same pull
request. Do not copy token values into feature components.

## 1. Product and design principles

Acestream Scraper is an operational control panel for people who may not know
the details of AceStream, EPG, network routing, or container services. The UI
must make state and next actions understandable without hiding useful detail.

1. **Operational clarity.** Health, progress, errors, ownership, and available
   actions must be easy to scan.
2. **Guided workflows.** Prefer explicit labels, short explanations, safe
   defaults, and recoverable actions over expert-only controls.
3. **Compact structure.** The product handles dense inventories and settings.
   Use hierarchy and grouping rather than excessive whitespace.
4. **Consistent semantics.** A status, action, or surface should retain the same
   meaning in every feature and in both themes.
5. **Accessible by default.** Keyboard access, visible focus, readable contrast,
   touch targets, reduced motion, and non-color cues are part of the component
   contract.
6. **Responsive by composition.** Pages adapt their layout and action density;
   they do not become reduced desktop screenshots.

## 2. Visual character

The product uses a restrained operational aesthetic:

- teal identifies the primary action and the product accent;
- blue identifies navigation, information, and secondary emphasis;
- warm orange is reserved for highlights and approachable emphasis;
- surfaces carry most of the hierarchy through borders, elevation, and spacing;
- IBM Plex Sans provides a practical, technical tone without relying on
  monospaced text for general content.

The interface supports light and dark themes. Theme selection follows the system
preference until the user explicitly chooses a mode; that choice is stored in
`localStorage` under `app-theme-mode`.

## 3. Token model

Feature code should read semantic values from `theme.appTokens`. Material UI
palette values are derived from the same token set. Raw colors are acceptable
only for data that has no existing semantic role and should be promoted to a
token when reused.

### 3.1 Surfaces and text

| Token | Light | Dark | Intended use |
| --- | --- | --- | --- |
| `surface.canvas` | `#f3f6fb` | `#0f1720` | Application background |
| `surface.panel` | `#ffffff` | `#17222d` | Default paper and dialogs |
| `surface.muted` | `#e7eef6` | `#1c2c38` | Subdued groups and hover states |
| `surface.raised` | `#fbfdff` | `#223240` | Content shell and emphasized sections |
| `surface.border` | `rgba(16, 33, 47, 0.08)` | `rgba(166, 193, 214, 0.16)` | Structural borders |
| `text.primary` | `#10212f` | `#edf5fb` | Titles and primary content |
| `text.secondary` | `#41556a` | `#b6c8d8` | Supporting content |
| `text.muted` | `#66788a` | `#89a1b3` | Low-emphasis metadata |
| `text.inverse` | `#f8fbff` | `#10212f` | Text on strongly colored surfaces |

### 3.2 Actions and accents

| Role | Light | Dark | Rule |
| --- | --- | --- | --- |
| Primary | `#0f766e` | `#14b8a6` | One principal action per decision area |
| Primary hover | `#115e59` | `#0f9385` | Hover for the primary action |
| Secondary background | `#dce9fb` | `#163355` | Supporting actions and selected navigation |
| Secondary text | `#0b5ed7` | `#bfd8ff` | Informational and secondary emphasis |
| Destructive | `#d14343` | `#d86363` | Actions that remove or interrupt state |
| Warm accent | `#dd8a42` | `#f0a84b` | Sparse highlight; never the default action |

Disabled colors and the focus ring also live under `appTokens.action`. Use the
Material UI `disabled` state and `focusVisible` behavior so the correct theme
values are applied.

### 3.3 Status families

The four status families are `success`, `warning`, `error`, and `info`. Each
exposes `bg`, `border`, `text`, and `icon`. A status treatment must use the full
family rather than combining values from different severities.

Status meaning must never depend on color alone. Pair color with at least one of:

- a clear text label;
- a recognizable icon with an accessible name;
- an explicit state description or next action.

Use `role="alert"` for errors and warnings that require attention. Use
`role="status"` for passive success and information updates. The shared
`InlineStatusNotice` already applies this rule.

### 3.4 Layout and motion

Material UI's default spacing unit is 8 px. Numeric spacing values in `sx`
therefore use that scale.

| Token | Value | Purpose |
| --- | ---: | --- |
| `layout.pageGap` | `3` / 24 px | Separation between page regions |
| `layout.sectionGap` | `2` / 16 px | Internal section rhythm |
| `layout.panelPadding` | `2.5` / 20 px | Standard panel padding |
| `layout.cardRadius` | `10px` | Cards, buttons, chips, and notices |
| `motion.durationShort` | `120ms` | Small state changes |
| `motion.durationStandard` | `180ms` | Default transition |
| `motion.durationReduced` | `80ms` | Reduced-motion fallback |
| `motion.easingStandard` | `cubic-bezier(0.2, 0, 0, 1)` | Default easing |

When `prefers-reduced-motion: reduce` is active, the standard duration is reduced
to 80 ms. Essential information must appear independently of animation.

## 4. Typography

The font stack starts with IBM Plex Sans and falls back to system sans-serif
fonts. Use Material UI variants rather than declaring font size and weight in a
feature component.

| Variant | Size and style | Use |
| --- | --- | --- |
| `pageTitle` | `clamp(1.75rem, 2.2vw, 2.35rem)`, 700 | One `h1` per page |
| `sectionTitle` | `1rem`, 600 | Section and card headings |
| `body1` | `0.95rem`, line height 1.55 | Main prose and form content |
| `body2` | `0.875rem`, line height 1.45 | Compact supporting content |
| `helperText` | `0.8125rem`, line height 1.45 | Guidance near controls |
| `statusMeta` | `0.75rem`, 500, uppercase | Short operational metadata |
| `denseData` | `0.8125rem`, 500 | Tables and dense lists |

Keep heading levels semantic even when the visual variant differs. A section
title normally renders as `h2`; nested feature content may use `h3` while keeping
an appropriate visual variant.

## 5. Responsive layout

The shell's breakpoints are an explicit application contract:

| Range | Boundary | Behavior |
| --- | --- | --- |
| Compact | up to `899.95px` | Drawer navigation, stacked actions, 44 px controls |
| Desktop | from `900px` | Persistent navigation and two-column header layout |
| Wide | from `1280px` | Wider content and optional primary/supporting regions |

The navigation width is 264 px. Standard content is capped at 1280 px and wide
content at 1440 px. `Live TV` is intentionally allowed to use the full available
width. Horizontal page padding grows from 16 px to 24 px and then 32 px; the
compact shell reduces its outer padding to preserve usable space.

On compact screens:

- primary header actions stack and fill the available width;
- secondary header actions move into the `More actions` menu when appropriate;
- tables must either use the responsive-table helper or provide an equivalent
  card/list representation;
- dialog margins shrink and action rows wrap;
- buttons, icon buttons, tabs, and navigation items have a minimum height of
  44 px;
- text inputs use 16 px text to prevent browser zoom on focus.

Do not infer responsive behavior from Material UI's default `sm` or `md` names
when working on the shell. Use the dimensions exposed by
`theme.appTokens.layout.shell`.

## 6. Composition primitives

### `AppShell`

Owns global navigation, the skip link, background, responsive content width, and
the main landmark. Pages render inside it and should not create another global
container.

### `PageHeader`

Use at the top of a route-level page. It owns the `h1`, optional subtitle,
principal actions, secondary actions, and compact overflow behavior. Keep the
subtitle short and task-oriented.

### `ContentSection`

Use to group a coherent set of controls or data. It owns the bordered surface,
section heading, description, actions, and responsive action layout. On wide
screens, `wideLayout="primary"` and `wideLayout="supporting"` may participate in
the shared two-region page layout.

### State components

- `EmptyState` explains why content is absent and offers one useful next action.
- `InlineStatusNotice` communicates success, information, warnings, or errors
  using the semantic status token family.
- Material UI `Alert`, loading indicators, and skeletons are appropriate when
  their semantics match; keep their copy specific to the current operation.

### Dense data

Use tables for comparison and inventory management on larger screens. Preserve:

- visible column labels and predictable action placement;
- tabular numerals for counts and measurements;
- keyboard access to row actions;
- horizontal containment or a deliberate card representation on compact screens;
- loading, empty, error, and partial-result states.

## 7. Actions, forms, and feedback

### Action hierarchy

- Use a contained primary button for the action that advances or completes the
  current task.
- Use outlined buttons for supporting actions.
- Put infrequent row actions in `RowActionsMenu`.
- Mark destructive actions with `color="error"`, state the affected object, and
  use `ConfirmDialog` when the outcome is difficult to undo.
- Do not place multiple visually equal primary actions in one decision area.

### Forms

- Labels describe the value, while helper text explains format or consequence.
- Validation messages appear near the field and explain how to recover.
- Save actions remain discoverable on compact screens and indicate pending state.
- Disabled controls need contextual explanation when the reason is not obvious.
- Never rely on placeholder text as the only label.

### Async feedback

React Query owns server state. During mutations, prevent duplicate submission and
keep prior information visible when it remains valid. Errors should use the
normalized API error contract and retain correlation details when they help
diagnosis. Success feedback should confirm what changed, not merely say
"Success".

## 8. Accessibility contract

Every UI contribution must preserve the following baseline:

- one logical `h1` per route and ordered headings beneath it;
- reachable controls and menus by keyboard;
- visible focus treatment supplied by the theme;
- a useful accessible name for icon-only controls;
- 44 px compact-screen targets for common interactive elements;
- status meaning conveyed by text or icon as well as color;
- dialogs with a labelled title, contained focus, and a clear dismissal path;
- data tables with headers and an equivalent usable compact presentation;
- loading announcements that do not repeatedly interrupt assistive technology;
- animations that respect reduced-motion preferences.

Use the existing `Skip to content` link and `main` landmark; do not add competing
page-level main landmarks.

## 9. Content style

Write for an operator who wants to complete a task safely:

- use direct verbs: **Add source**, **Check stream**, **Save order**;
- name the object and the result;
- explain technical requirements immediately before they matter;
- distinguish unavailable, disabled, offline, skipped, and failed states;
- do not call imported catalogue data "online" until a signal check verifies it;
- keep error messages actionable and avoid internal implementation terms unless
  they help troubleshooting.

## 10. Contribution checklist

Before submitting a UI change:

1. Reuse a shared primitive before introducing a feature-specific equivalent.
2. Use semantic theme tokens in reusable UI.
3. Check light and dark themes.
4. Check one compact width and one desktop width.
5. Complete the primary flow using only the keyboard.
6. Check loading, empty, error, and success states that apply.
7. Confirm status meaning remains clear without color.
8. Add or update focused component tests when behavior changes.
9. Record visual review evidence in
   `docs/dev/frontend-design-review-evidence.md` when changing shared primitives
   or the design foundation.
10. Update this document and `frontend/src/theme.ts` together when the token or
    component contract changes.
