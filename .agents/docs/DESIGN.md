# ARTEL design rules

## Current visual system

Use the implemented Blueprint Paper design: light by default, cream-paper
surfaces, ink text, vermilion actions, thin rules, and restrained surface steps.
Dark mode uses the existing inverted palette through the shared theme control.

This document replaces the obsolete Replay Studio specification. Its dark-first
graphite/cyan palette, font stack, fixed editor shell, panel sizes, component
roadmap, and replay-only completion checklist are retired. Do not preserve them
as an alternative design system or apply copies of that specification elsewhere.

## Source of truth

Read the target application's current tokens, shared layout, theme implementation,
and a neighboring screen before making UI changes. The implementation owns exact
values; do not duplicate color values or invent new defaults in a document.

| Surface | Color and typography | Theme and shared UI |
| --- | --- | --- |
| Onboarding | `onboarding/src/styles/tokens.css`, `onboarding/src/styles/marketing.css` | `onboarding/src/theme.ts`, `onboarding/src/components/SiteLayout.tsx` |
| Console | `artel-home/src/styles/tokens.css`, `artel-home/src/styles/index.css` | `artel-home/src/theme.ts`, existing page layouts and components |
| Admin | `admin-page/src/styles/tokens.css`, `admin-page/src/styles/index.css` | `admin-page/src/theme.ts`, existing page layouts and components |

For another application, locate its implemented equivalents before styling it.
Follow [onboarding design rules](../../onboarding/.agents/docs/DESIGN.md) for site
layouts and documentation. Local rules must describe the current implementation;
an old copied Replay Studio document is not authority to restore a retired style.

## Tokens and typography

Reuse semantic tokens from the target application:

| Purpose | Onboarding | Console and admin |
| --- | --- | --- |
| Page background | `--paper` | `--color-bg-canvas` |
| Secondary surface | `--paper-2` | Appropriate `--color-bg-*` token |
| Primary text | `--ink` | `--color-text-primary` |
| Secondary text | `--ink-2` | `--color-text-secondary` |
| Divider | `--rule` | `--color-border-subtle` |
| Action accent | `--flare` | `--color-action-primary` |
| Headings | `--font-display` | `--font-display` |
| Body | `--font-body` | `--font-sans` |
| Code and identifiers | `--font-mono` | `--font-mono` |

The current font families are Space Grotesk for display, Pretendard for body,
and IBM Plex Mono for code, with the fallbacks defined in the token files.
Reuse existing spacing and radius tokens and component sizing.

Do not introduce page-specific hard-coded palettes or alternate font stacks.
Keep semantic status colors for their existing purposes. Check the contrast of
actual foreground/background pairs; an accent or muted token is not suitable
for every text role merely because it exists.

## Layout and theme

- Reuse the current application shell, navigation, controls, and content widths.
- Express hierarchy with typography, spacing, rules, and existing surface steps.
- Let the shared theme control update header, body, sidebars, dialogs, tables,
  code blocks, and footer together. Do not force a theme inside a page.
- Preserve the user's theme preference when navigating or adding a screen.
- Choose layout from the task and existing product patterns. Reference documents
  may need navigation rails and a table of contents; they retain the host site's
  colors, fonts, and chrome. QA screens also use the current product design.
- Keep content usable on narrow screens. Scroll wide tables and code inside their
  containers rather than widening the entire page.

## User-facing copy

Follow [user-facing copy rules](../../onboarding/.agents/docs/user-copy.md).
Write labels, instructions, constraints, and reference material the reader needs.
Do not add an introductory sentence that merely restates a heading or describes
what the page will explain. Do not fill empty space with promotional copy,
implementation notes, or validation badges.

## Verification

- Compare the complete changed screen with a current neighboring screen, including
  header, footer, typography, colors, borders, spacing, and control states.
- Test both themes with the existing theme control. Verify desktop and mobile
  widths, page overflow, sticky navigation, and section-link targets.
- Check keyboard navigation, visible focus, accessible names, and semantic
  headings. Maintain WCAG AA text contrast and respect reduced motion.
- Verify the interactions actually present in the change. Functional checks and
  a successful build do not substitute for reviewing the rendered screen.
