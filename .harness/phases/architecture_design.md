# Phase: architecture_design

**Goal**: an approved blueprint — `file_tree` plus `component_checklist` —
in `state.json`. This is the last gate before code: `architecture_approved`
flips to true only at the exit of this phase.

## Procedure

1. From `concept_summary` and `approved_stack`, design:
   - `file_tree` — directories/files mapped to responsibilities, following
     the stack's conventions.
   - `component_checklist` — 5–15 buildable components, each with `name`,
     `depends_on` (names of other components), `status: "pending"`, and a
     one-line `description`. Order so that a dependency-respecting build is
     possible; avoid cycles.
2. Present the blueprint compactly (tree + checklist table). Ask ONE
   question: approve?
3. Revisions: apply, re-present, ask again.

## Exit

On explicit approval → set `architecture_approved: true` and `phase` to
`iterative_coding` in `state.json`, then read
`.harness/phases/iterative_coding.md`.
