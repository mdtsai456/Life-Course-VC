---
title: "feat: Add example text suggestion buttons"
type: feat
status: completed
date: 2026-03-31
origin: docs/brainstorms/2026-03-31-example-text-suggestions-requirements.md
---

# feat: Add example text suggestion buttons

## Overview

Add two clickable example sentence buttons near the textarea in VoiceCloner so users can quickly fill in sample text. One casual, one formal. Pure frontend change.

## Problem Frame

Users face a blank textarea and don't know what length or style of text to enter. Example buttons lower the barrier to first use and demonstrate the feature's intended usage. (see origin: docs/brainstorms/2026-03-31-example-text-suggestions-requirements.md)

## Requirements Trace

- R1. Display 2 example sentence buttons near the textarea; clicking fills the textarea
- R2. Mixed style: one casual/conversational, one formal/reading
- R3. Clicking an example overwrites existing textarea content (no append)
- R4. Example buttons disabled during recording or processing

## Scope Boundaries

- No customizable examples
- No random/rotating examples
- No backend changes

## Context & Research

### Relevant Code and Patterns

- `frontend/src/components/VoiceCloner.jsx` — main component; `setText` state setter already exists for the textarea
- `frontend/src/index.css` — all styling lives here; button styles follow `.record-button` / `.submit-button` patterns
- Disabled state pattern: `isRecording || loading` is already used on the textarea (line 263) and submit button (line 208)

## Key Technical Decisions

- **Placement: above the textarea** — Users see examples before they start typing. Placing below risks being missed after the textarea is already focused.
- **Hardcoded strings in component** — Two strings is not worth extracting to config. Inline array in the component is simplest.
- **Style as small link-buttons** — The existing `.link-button` class (index.css line 113-121) provides an understated clickable style that won't compete visually with the primary record/submit buttons.

## Open Questions

### Resolved During Planning

- **Overwrite vs append?** Overwrite per R3 — simpler and matches "example fill" mental model.
- **Should textarea get focus after fill?** No — the user may want to edit, or may proceed to submit. Leaving focus neutral is simpler.

### Deferred to Implementation

- **Exact example sentences** — final wording can be tuned during implementation. Directional: one ~20 char casual greeting, one ~30 char formal narration.

## Implementation Units

- [x] **Unit 1: Example text buttons in VoiceCloner**

**Goal:** Add two example sentence buttons above the textarea that fill it on click.

**Requirements:** R1, R2, R3, R4

**Dependencies:** None

**Files:**
- Modify: `frontend/src/components/VoiceCloner.jsx`
- Modify: `frontend/src/index.css`

**Approach:**
- Define a small array of example objects `[{ label, text }]` at module scope (outside the component, like the existing `CLONE_PROGRESS_LABELS`)
- Render them as buttons above the `<textarea>`, using the `.link-button` base class with a wrapper for layout
- `onClick` calls `setText(example.text)`
- `disabled` uses the same `isRecording || loading` guard already on the textarea

**Patterns to follow:**
- `CLONE_PROGRESS_LABELS` constant pattern at module scope (VoiceCloner.jsx line 49)
- `.link-button` class for understated clickable text (index.css line 113)
- Disabled guard pattern: `isRecording || loading` (VoiceCloner.jsx line 263)

**Test scenarios:**
- Happy path: clicking example button sets textarea value to the example text
- Happy path: clicking a different example button replaces existing textarea content (R3)
- Edge case: buttons are disabled when `isRecording` is true (R4)
- Edge case: buttons are disabled when `loading` is true (R4)

**Verification:**
- Two example buttons visible above textarea
- Clicking either fills the textarea with the corresponding text
- Buttons are non-interactive during recording and processing states
- Visual style is understated and does not compete with primary action buttons

## System-Wide Impact

- **Interaction graph:** None — pure local UI state change via existing `setText`
- **Error propagation:** None — no new error paths
- **API surface parity:** None — no backend changes

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Example sentences feel unnatural | Keep them short and representative; easy to change later since they're just strings |

## Sources & References

- **Origin document:** [docs/brainstorms/2026-03-31-example-text-suggestions-requirements.md](docs/brainstorms/2026-03-31-example-text-suggestions-requirements.md)
