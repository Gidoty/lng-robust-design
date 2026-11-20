# CLAUDE.md (lng-robust-design)

This folder is the computational engine for a journal manuscript on robust LNG refrigeration design for Niger Delta
associated gas. It is separate from the ScholarAI project in the rest of this repository. Do not touch `backend/`,
`frontend/`, `portfolio/` or the root files from here.

## Do this first, every session

1. Sync: `git fetch origin ccr-0a266400-jmatdr` and read from `origin/ccr-0a266400-jmatdr` (or merge it). The engine session
   commits to that branch and does not use others.
2. Read `HANDOFF_FOR_MANUSCRIPT_CLAUDE.md`, then `STATUS.md`. They are the current state of the work and the writing rules.
3. Check `git log --oneline origin/ccr-0a266400-jmatdr -10` for what changed since you last looked.

## Rules that always apply

- Every number in the manuscript must come from a file the engine produced. Otherwise write `[AUTHOR TO PROVIDE]`.
- The folder `lng_robust/runs/*_SMOKE/` is a smoke test. Its numbers are not results. Never quote them.
- Do not state or imply an outcome before the data exist.
- Do not add or complete references from memory.
- Never commit secrets, `.env` files or the `.venv/` folder.

## Roles

- Engine session: edits `lng_robust/`, `STATUS.md`, `HANDOFF_FOR_MANUSCRIPT_CLAUDE.md`.
- Manuscript session: edits only `manuscript/` (draft text, tables, figure captions, reference checks). It does not edit engine
  code. If the engine needs a change, write the request in `manuscript/REQUESTS_TO_ENGINE.md`; the engine session reads it.
