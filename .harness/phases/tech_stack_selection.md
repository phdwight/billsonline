# Phase: tech_stack_selection

**Goal**: an `approved_stack` in `state.json` that fits the approved
`concept_summary`. Still no application code.

## Procedure

1. Propose ONE coherent default stack (language, framework, DB, frontend,
   testing, deployment) with a one-line rationale per choice, sized to the
   concept — do not enumerate alternatives unless the user asks.
2. Resolve disagreements one decision at a time: if the user pushes back on a
   layer, present the 2–3 realistic options for THAT layer only, with
   trade-offs, and ask them to pick.
3. Record the result in `approved_stack` (one key per layer) and re-present
   the full stack for sign-off.

If this phase was re-entered from coding (a stack change request), the old
blueprint is already in `prior_architecture` — say explicitly which layers
change and what migration of existing components that implies.

## Exit

On explicit approval of the full stack → set `phase` to
`architecture_design` in `state.json`, then read
`.harness/phases/architecture_design.md`.
