# App Generation Harness

This project is built through a phased harness. You (Claude Code) are the
harness executor. The state machine below is MANDATORY — it overrides your
default inclination to just start coding.

## Session start (always, before anything else)

1. Read `.harness/state.json`.
   - Missing + directory empty (besides harness files) → create it from
     `.harness/state.template.json`, set phase to `idea_gathering`.
   - Missing + existing codebase → set phase to `codebase_ingestion`.
   - Present → resume at the recorded phase. Trust the state file over your
     assumptions about the conversation.
2. Read ONLY `.harness/phases/<current_phase>.md` for that phase's
   instructions. Do not read the other phase files — they are loaded on
   demand when the phase changes.
3. Tell the user the current phase and what's pending in one short line.

## Hard rules (all phases)

- NEVER write application code before the architecture in `state.json` is
  approved (`architecture_approved: true`).
- One decision per question. Never stack questions.
- A phase transition happens ONLY on the user's explicit approval. "Sure, but
  change X" is a revision, not an approval — apply X, re-present, ask again.
- On every phase transition: update `state.json` first, then read the new
  phase file, then proceed.
- If the user requests something belonging to a different phase (e.g. a stack
  change during coding), do not improvise: announce the transition back to
  `tech_stack_selection`, record the old blueprint under `prior_architecture`
  in state, update state, and follow that phase file.

## Component review cycle (iterative_coding)

- Build ONE component at a time, only ones whose `depends_on` are all
  `built` in the checklist.
- After writing a component's files: set its status to `in_review` in
  `state.json`. DO NOT `git commit`.
- Only after the user approves the code: set status to `built`, then run
  `git add -A && git commit -m "component: <name>"` (state.json rides in the
  same commit).
- If the user rejects: `git checkout -- . && git clean -fd` (this also
  reverts state.json), then re-plan.
- `all_complete` requires every checklist item `built` AND user confirmation.

## State file

`.harness/state.json` is the single source of truth: current phase, concept
summary, approved stack, file tree, and the component checklist with
`depends_on` and `status` (`pending` → `in_review` → `built`). Keep it
accurate — a future session with no memory of this conversation must be able
to resume from it alone.
