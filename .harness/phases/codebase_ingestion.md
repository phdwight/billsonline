# Phase: codebase_ingestion

**Goal**: reconstruct the harness state from an existing codebase so future
sessions can resume from `state.json` alone. Entry phase when the harness is
adopted into a repo that already has code.

## Procedure

1. Survey the repo: README/docs, entrypoints, dependency manifests, source
   layout, tests, CI, deployment config. Prefer docs over reading every file.
2. Populate `state.json`:
   - `concept_summary` — what the app is and does, from evidence not guesses.
   - `approved_stack` — languages, frameworks, DB, testing, CI/CD, deploy.
   - `file_tree` — a compact map of directories to responsibilities.
   - `component_checklist` — the major components with `depends_on`; mark a
     component `built` only if it exists, is committed, and is covered by
     passing tests; anything half-finished is `in_review` or `pending`.
3. Present the reconstructed blueprint as a short summary. Ask ONE question:
   does the user approve it as the recorded architecture?

## Exit

On explicit approval → set `architecture_approved: true` and `phase` to
`iterative_coding` in `state.json`, then read
`.harness/phases/iterative_coding.md`. If the user corrects anything, apply
the correction, re-present, and ask again.
