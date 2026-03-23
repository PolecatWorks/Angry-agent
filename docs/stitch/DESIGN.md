```markdown
# Design System Strategy: The Architectural Intelligence Framework

## 1. Overview & Creative North Star: "The Digital Atrium"
This design system rejects the cluttered, boxy aesthetics of legacy enterprise software. Our Creative North Star is **"The Digital Atrium"**—an environment characterized by vast structural clarity, light-filled transitions, and intentional layering. 

We move beyond the "template" look by utilizing **Architectural Asymmetry**. Instead of a centered, rigid grid, we lean into a weighted layout where the left-hand communication zone feels grounded and stable, while the right-hand "Workspace" panel feels ethereal and elevated through glassmorphism. We achieve power not through density, but through high-contrast typography and "breathable" data visualizations that command authority.

---

## 2. Colors & Surface Philosophy
The palette is a sophisticated interplay of deep slates and luminous whites, punctuated by a high-energy 'Action Blue'.

### The "No-Line" Rule
**Strict Mandate:** Designers are prohibited from using 1px solid borders for sectioning or layout containment. 
Structural boundaries must be defined solely through background color shifts. For example, a `surface-container-low` (#f2f3ff) navigation rail should sit flush against a `surface` (#faf8ff) main stage. The human eye perceives the tonal shift as a boundary; a line is a visual "stutter" that we must avoid.

### Surface Hierarchy & Nesting
Treat the UI as a physical stack of premium materials. Use the `surface-container` tiers to create "nested" depth:
*   **Base Layer:** `surface` (#faf8ff) for the widest application background.
*   **Secondary Zones:** `surface-container-low` (#f2f3ff) for sidebars or secondary navigation.
*   **Actionable Content:** `surface-container-lowest` (#ffffff) for primary cards or data modules to create a "lifted" feel.
*   **High-Intensity Focus:** `surface-container-high` (#e2e7ff) for active states or highlighted data rows.

### The "Glass & Gradient" Rule
To elevate the Enterprise AI experience, the right-hand Workspace must utilize **Glassmorphism**. Use `surface-variant` (#dae2fd) at 60% opacity with a `20px` backdrop-blur. 

**Signature Texture:** For primary CTAs and AI-generated insights, use a subtle linear gradient: 
`linear-gradient(135deg, #003ec7 0%, #0052ff 100%)`. This provides a "glow" that flat hex codes cannot replicate.

---

## 3. Typography: Editorial Authority
We pair **Manrope** (Display/Headlines) with **Inter** (Body/UI) to balance character with utility.

*   **Display & Headline (Manrope):** These are your "Editorial" voices. Use `display-md` (2.75rem) for high-level AI summaries. The wide apertures of Manrope convey modern, high-trust technology.
*   **Title & Body (Inter):** Inter is our "Workhorse." Use `body-md` (0.875rem) for the majority of data-heavy enterprise tables. It is optimized for screen readability at small scales.
*   **Label (Inter):** Use `label-sm` (0.6875rem) in uppercase with 5% letter-spacing for metadata and table headers. This creates a "Pro" architectural feel.

---

## 4. Elevation & Depth
In this system, elevation is a product of light and tone, not heavy shadows.

*   **The Layering Principle:** Depth is achieved by "stacking." A `surface-container-lowest` (#ffffff) card placed on a `surface-container-low` (#f2f3ff) background creates a natural, soft lift.
*   **Ambient Shadows:** If an element must float (e.g., a dropdown or modal), use an ultra-diffused shadow: `box-shadow: 0 12px 40px rgba(19, 27, 46, 0.06);`. The shadow color must be a derivative of `on-surface` (#131b2e), never pure black.
*   **The Ghost Border Fallback:** If a container requires more definition for accessibility, use the `outline-variant` (#c3c5d9) at **15% opacity**. This creates a "hint" of a boundary without breaking the No-Line Rule.

---

## 5. Components

### Buttons & Actions
*   **Primary:** Gradient fill (`primary` to `primary_container`) with `lg` (0.5rem) roundedness. No border. Text is `on_primary` (#ffffff).
*   **Secondary:** `surface-container-highest` (#dae2fd) background. This feels integrated into the UI rather than "pasted" on.
*   **Tertiary:** Ghost style. Use `primary` (#003ec7) text with no background until hover.

### The AI Workspace Panel (Glass Component)
This panel distinguishes itself from the chat area through a `surface-variant` fill at 70% opacity and a `backdrop-filter: blur(12px)`. This creates a "working laboratory" feel for AI collaboration.

### Data Cards & Lists
*   **Forbid Dividers:** Do not use lines to separate list items. Use the **Spacing Scale** `spacing-4` (0.9rem) or `spacing-5` (1.1rem) to create clear "islands" of information.
*   **Active States:** An active list item should shift to `surface-container-high` (#e2e7ff) with a `primary` (#003ec7) vertical indicator bar (3px wide) on the far left.

### Input Fields
*   **Base:** `surface-container-lowest` (#ffffff) with a `sm` (0.125rem) "Ghost Border" (outline-variant at 20%).
*   **Focus State:** The border transitions to `primary` (#003ec7) at 100% opacity with a soft `primary_fixed` (#dde1ff) outer glow.

---

## 6. Do’s and Don’ts

### Do
*   **Do** use asymmetrical spacing. A wider left margin (e.g., `spacing-16`) vs. a tighter right margin (e.g., `spacing-8`) creates a sophisticated, non-generic layout.
*   **Do** use `tertiary` (#952200) sparingly for "Warning" or "High-Priority" AI flags. It is a warm accent that breaks the cool slate/blue palette.
*   **Do** leverage `full` (9999px) roundedness for chips and status indicators, but stick to `lg` (0.5rem) for structural cards.

### Don't
*   **Don't** use pure black (#000000) for text. Use `on_surface` (#131b2e) to maintain the "Slate" sophistication.
*   **Don't** use standard "Drop Shadows." If it doesn't look like light passing through glass or hitting paper, it’s too heavy.
*   **Don't** use more than two levels of nesting. If you need a card inside a card inside a card, reconsider the information architecture. Use spacing instead.

---

## 7. Signature AI Component: "The Insight Prism"
For AI-generated content, use a container with a `surface-container-lowest` background and a 1px "Ghost Border" that uses a gradient of `primary` to `tertiary` at 30% opacity. This signals to the user that the content is "Living" and "Machine-Generated," maintaining high trust through distinct visual cues.```