# Phase: iterative_coding

**Goal**: build every checklist component through the review cycle below.
Requires `architecture_approved: true` — if it is false, something is wrong;
stop and tell the user instead of coding.

## Component review cycle

- Build ONE component at a time, only ones whose `depends_on` are all
  `built` in the checklist. If several are eligible, propose one and ask.
- After writing a component's files: set its status to `in_review` in
  `state.json`. DO NOT `git commit`.
- Present what was built and wait for review. Only after the user approves:
  set status to `built`, then run
  `git add -A && git commit -m "component: <name>"` (state.json rides in the
  same commit). Keep local junk (`.coverage`, `.DS_Store`, local DBs) out of
  the commit.
- If the user rejects: `git checkout -- . && git clean -fd` (this also
  reverts state.json), then re-plan with their feedback.

## New requests while in this phase

- A new feature/change → add it to `component_checklist` as `pending` with
  correct `depends_on`, then run it through the cycle above.
- A stack change → do not improvise: copy the current blueprint to
  `prior_architecture`, set `phase` to `tech_stack_selection`, update
  `state.json`, then read that phase file and follow it.

## Completion

`all_complete` requires every checklist item `built` AND explicit user
confirmation. Once complete, the harness stays in this phase as maintenance
mode: new requests become new checklist entries.
