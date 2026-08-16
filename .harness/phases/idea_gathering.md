# Phase: idea_gathering

**Goal**: turn a vague app idea into a concrete `concept_summary` in
`state.json`. No stack talk, no architecture, no code.

## Procedure

1. Interview the user — ONE question per message. Cover, in roughly this
   order: the core problem, the primary user, the 3–5 must-have capabilities,
   explicit non-goals, and any hard constraints (offline, mobile, budget,
   integrations).
2. Stop interviewing as soon as you can write a crisp summary — do not
   exhaust the list for its own sake. 4–7 questions is typical.
3. Write the summary (5–10 sentences: problem, user, capabilities, non-goals,
   constraints) into `concept_summary` in `state.json` and present it back.
4. Ask for approval of the summary.

## Exit

On explicit approval → set `phase` to `tech_stack_selection` in
`state.json`, then read `.harness/phases/tech_stack_selection.md`.
Revisions ("yes but…") are applied and re-presented; they are not approval.
