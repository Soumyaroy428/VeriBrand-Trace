# Design System Specification (DESIGN.md)
## VeriBrand Trace — High-Integrity Governance & Analytics

> **Design Archetype:** Modern Dark Minimalist / Swiss Precision Engineering  
> **Concept:** Sovereign, auditable pre-publication brand governance designed with cryptographic rigor, high-contrast typography, and zero decorative fluff.

---

## 1. Color System (OKLCH Semantic Tokens)

All colors are defined using the perceptually uniform `oklch(L C H)` color space. Neutrals are subtly tinted toward a deep slate-navy brand hue (`H: 250`, `C: 0.006–0.012`) to eliminate ungrounded dead grays.

### 1.1 Dark Theme (Default)
```css
:root[data-theme="dark"], :root {
  /* Canvas & Surfaces */
  --bg-canvas: oklch(0.14 0.008 250);         /* Deep obsidian background #0f1218 */
  --bg-surface: oklch(0.18 0.010 250);        /* Primary card/panel surface #151922 */
  --bg-surface-elevated: oklch(0.22 0.012 250);/* Hover/active elevation #1c222e */
  --bg-surface-subtle: oklch(0.16 0.009 250);  /* Inset metric/track wells */

  /* Borders & Dividers (Crisp 1px borders, no heavy drop shadows) */
  --border-subtle: oklch(0.24 0.010 250);      /* Standard card/divider border */
  --border-muted: oklch(0.30 0.012 250);       /* Interactive element border */
  --border-active: oklch(0.48 0.020 250);      /* Focus / hover highlight */

  /* Text & Typography Hierarchy (WCAG AAA / AA compliant contrast >= 7:1) */
  --text-title: oklch(0.98 0.005 250);         /* Pure crisp headline #f8fafc */
  --text-body: oklch(0.85 0.010 250);          /* Primary legible prose #d1d5db */
  --text-muted: oklch(0.62 0.012 250);         /* Metadata, captions, timestamps */
  --text-inverse: oklch(0.12 0.008 250);       /* High-contrast badge text */

  /* Semantic Brand & Action Accents */
  --brand-primary: oklch(0.72 0.14 175);       /* Precision Teal #14b8a6 */
  --brand-primary-hover: oklch(0.78 0.16 175); /* Hover brightness boost */
  --brand-primary-subtle: oklch(0.24 0.04 175);/* Teal badge/accent tint */

  /* Audit Severity Tokens */
  --severity-critical: oklch(0.62 0.22 25);    /* Critical/Blocking Crimson */
  --severity-critical-subtle: oklch(0.22 0.06 25);
  --severity-high: oklch(0.72 0.18 55);        /* High/Amber Warning */
  --severity-high-subtle: oklch(0.24 0.05 55);
  --severity-medium: oklch(0.78 0.16 85);      /* Medium/Gold Caution */
  --severity-medium-subtle: oklch(0.25 0.05 85);
  --severity-low: oklch(0.72 0.14 240);        /* Informational/Blue */
  --severity-low-subtle: oklch(0.22 0.04 240);
  --severity-pass: oklch(0.76 0.16 150);       /* Verified/Emerald */
  --severity-pass-subtle: oklch(0.22 0.05 150);
}
```

### 1.2 Light Theme (Alternative)
```css
:root[data-theme="light"] {
  --bg-canvas: oklch(0.98 0.004 250);          /* Off-white canvas #f8fafc */
  --bg-surface: oklch(1.00 0.000 0);           /* Crisp white surface */
  --bg-surface-elevated: oklch(0.96 0.006 250);/* Hover card background */
  --bg-surface-subtle: oklch(0.94 0.006 250);  /* Wells & inset tracks */

  --border-subtle: oklch(0.88 0.008 250);
  --border-muted: oklch(0.78 0.010 250);
  --border-active: oklch(0.55 0.015 250);

  --text-title: oklch(0.14 0.008 250);
  --text-body: oklch(0.28 0.010 250);
  --text-muted: oklch(0.48 0.012 250);
  --text-inverse: oklch(0.98 0.004 250);

  --brand-primary: oklch(0.58 0.14 175);
  --brand-primary-hover: oklch(0.52 0.15 175);
  --brand-primary-subtle: oklch(0.92 0.04 175);

  --severity-critical: oklch(0.55 0.22 25);
  --severity-critical-subtle: oklch(0.95 0.04 25);
  --severity-high: oklch(0.62 0.18 55);
  --severity-high-subtle: oklch(0.94 0.04 55);
  --severity-medium: oklch(0.68 0.16 85);
  --severity-medium-subtle: oklch(0.95 0.04 85);
  --severity-low: oklch(0.55 0.14 240);
  --severity-low-subtle: oklch(0.94 0.03 240);
  --severity-pass: oklch(0.58 0.16 150);
  --severity-pass-subtle: oklch(0.93 0.04 150);
}
```

---

## 2. Typography

- **Display & Headlines:** Strict editorial sans-serif stack with tabular numbers enabled. Primary titles must never exceed 2 lines.
  `font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;`
- **Data, Hash & Metric Readouts:** High-legibility monospaced stack with zero-slashed figures.
  `font-family: ui-monospace, "SF Mono", "Cascadia Code", "Roboto Mono", Menlo, Consolas, monospace;`
- **Typographic Scale:**
  - `Display 1`: 32px / 1.15 line-height / -0.03em tracking (Bold 700)
  - `Title 2`: 22px / 1.25 line-height / -0.02em tracking (Semibold 600)
  - `Subhead`: 14px / 1.4 line-height / -0.01em tracking (Medium 500)
  - `Body`: 13px / 1.5 line-height / normal tracking (Regular 400)
  - `Caption/Overline`: 11px / 1.3 line-height / +0.05em tracking (Semibold 600, uppercase)

---

## 3. Elevation, Spacing & Layout Architecture

1. **Crisp 1px Boundaries:** We reject heavy blurred drop shadows. Depth is achieved strictly via crisp 1px borders (`var(--border-subtle)`), 1px inset highlights, and surface lightness contrasts.
2. **Asymmetric Editorial Balance:** Never default to 3 identical rounded cards. Group high-priority telemetry into an asymmetric split:
   - **Primary Hero (60%):** Readiness Velocity & Throughput Gauge.
   - **Secondary Hero (40%):** Sovereign Human Reviewer Authority breakdown.
3. **Container Queries:** Self-contained widgets declare `@container` to adapt their internal layout (stacked vs. horizontal) based on available panel width, independent of viewport.

---

## 4. Component Anatomy

- **Metric Tiles:** Minimum 16px padding, subtle inset track well, monospace bold value, WCAG AA compliant delta indicator.
- **Progress Ratio Bars:** 6px continuous track, rounded-full, with separate fill segments for clean multi-state categorization.
- **Buttons & Controls:** High-visibility keyboard focus rings (`focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-400 focus-visible:ring-offset-2`), smooth 150ms ease-out transitions.
- **Empty & Loading States:** Dedicated skeleton waveforms and zero-data fallback states explaining the exact missing trigger.
