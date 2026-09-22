---
name: design-taste
description: Anti-slop frontend design taste skill for the Host Community Case Desk and public portal. Preserves established UI aesthetics while enforcing high typographic quality, purposeful density, restrained motion, and accessible micro-interactions.
---

# Design Taste Skill: Case Desk & Community Intake

## 1. Design Read & Core Philosophy

* **Target Audience**: Community members reporting high-stakes environmental grievances (oil spills, gas flaring, health hazards) and liaison officers managing active cases.
* **Aesthetic Standard**: Utilitarian excellence, modern dark-accented workspace, clean high-contrast data density, and human-first empathy.
* **Core Rule**: **Preserve the user's established layout and brand feel** (e.g. topbar brand mark, tab navigation, split workspace views), while refining spacing, micro-interactions, and contrast.

## 2. Anti-Default Discipline

* **Banned Generic Patterns**:
  * No generic purple/magenta AI gradients.
  * No cards-inside-cards-inside-cards nesting.
  * No bouncy, distracting infinite animations on functional buttons.
  * No low-contrast grey-on-grey text that harms legibility in sunlight or on low-end mobile devices.
* **Required Quality Markers**:
  * Crisp badge styling with distinct semantic colors:
    * `Reported`: Calm Slate / Neutral
    * `Under Investigation`: Subdued Amber / Orange
    * `Response Issued`: Cyan / Blue
    * `Resolved`: Muted Emerald Green
    * `Escalated` / `Breached`: Alert Crimson Red
  * Generous mobile tap targets (minimum 44x44px for action buttons).
  * Monospace accents for case references (`ELEME-2026-004`), timestamps, and verification codes (`font-family: ui-monospace, SFMono-Regular, monospace`).

## 3. Micro-Interactions & Restrained Motion

* Use `transition: all 0.15s ease-out` for hover states and button presses.
* Dialog and drawer entrances: Subtle fade and upward slide (`translateY(8px)` $\rightarrow$ `translateY(0)`).
* Loading states: Skeleton placeholders with a smooth background pulse rather than harsh spinners.

## 4. Typography & Visual Hierarchy

* System font stack prioritizing legibility: `system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`.
* Headings: Tight letter-spacing (`letter-spacing: -0.015em`), strong semantic weights.
* Body: 14px to 15px for workspace tables, 16px for public intake forms and chat messages.
