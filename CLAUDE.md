# CLAUDE.md (lng-robust-design)

This repository is the computational engine and study pipeline for a journal manuscript on robust LNG refrigeration design for
Niger Delta associated gas. It started as a folder of `Gidoty/scholarship_application_intelligence_system` (branch `ccr-0a266400-jmatdr`)
and moved here on 2026-11-20. That old branch keeps a mirror of `STATUS.md`, `HANDOFF_FOR_MANUSCRIPT_CLAUDE.md` and `manuscript/` so the
manuscript session can still read them there.

## Do this first, every session

1. Read `HANDOFF_FOR_MANUSCRIPT_CLAUDE.md`, then `STATUS.md`. They are the current state of the work and the writing rules.
2. Engine session: work in `Gidoty/lng-robust-design`. Manuscript session: read the mirror on the old branch, or this repository.
3. Results live on branches `results/<run_id>` of this repository (tables, figures, `provenance.json`, `RESULTS_SUMMARY.md`). Quote a number
   only from a file in such a package, and name the file and row.

## Rules that always apply

- Every number in the manuscript must come from a file the engine produced. Otherwise write `[AUTHOR TO PROVIDE]`.
- A results package from the `probe` preset (or any folder labelled SMOKE) is a timing run. Its numbers are not results. Never quote them.
- Surrogate values are never results. They appear only in the surrogate-reliability table and figures.
- Do not state or imply an outcome before the data exist.
- Do not add or complete references from memory.
- Decisions D1 to D11 and the PoR definition (manuscript Eq. 8) belong to the authors. Do not change them.
- Never commit secrets, `.env` files or the `.venv/` folder.

## Roles

- Engine session: edits `lng_robust/`, `tools/`, `.github/`, `STATUS.md`, `HANDOFF_FOR_MANUSCRIPT_CLAUDE.md`.
- Manuscript session: edits only `manuscript/` (draft text, tables, figure captions, reference checks). It does not edit engine code.
  If the engine needs a change, write the request in `manuscript/REQUESTS_TO_ENGINE.md`; the engine session reads it.
