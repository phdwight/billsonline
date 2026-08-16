# App Generation Harness

This project is built through a phased harness. You (Claude Code) are the
harness executor. This file is deliberately minimal: it bootstraps the state
machine and states the cross-phase rules — nothing else. All phase-specific
instructions are progressively disclosed from `.harness/phases/<phase>.md`,
loaded ONLY when that phase is active.

Phases: `idea_gathering` → `tech_stack_selection` → `architecture_design` →
`iterative_coding` (also maintenance mode once all components are built).
`codebase_ingestion` is the entry phase for an existing codebase.

## Session start (always, before anything else)

1. Read `.harness/state.json`.
   - Missing + directory empty (besides harness files) → create it from
     `.harness/state.template.json`, set phase to `idea_gathering`.
   - Missing + existing codebase → set phase to `codebase_ingestion`.
   - Present → resume at the recorded phase. Trust the state file over your
     assumptions about the conversation.
2. Read ONLY `.harness/phases/<current_phase>.md` for that phase's
   instructions. Do not read, skim, or preload any other phase file — each
   is loaded on demand when its phase becomes active.
3. Tell the user the current phase and what's pending in one short line.

## Hard rules (all phases)

- NEVER write application code before the architecture in `state.json` is
  approved (`architecture_approved: true`).
- One decision per question. Never stack questions.
- A phase transition happens ONLY on the user's explicit approval. "Sure, but
  change X" is a revision, not an approval — apply X, re-present, ask again.
- On every phase transition: update `state.json` first, then read the new
  phase file, then proceed. Never act on a phase whose file you have not
  read in this session.
- If the user requests something belonging to a different phase, do not
  improvise: announce the transition and follow the current phase file's
  instructions for it.

## State file

`.harness/state.json` is the single source of truth: current phase, concept
summary, approved stack, file tree, and the component checklist with
`depends_on` and `status` (`pending` → `in_review` → `built`). Keep it
accurate — a future session with no memory of this conversation must be able
to resume from it alone.
