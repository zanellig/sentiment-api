# AGENTS.md

pysentimiento service being migrated into a monorepo audio pipeline: Jobs API, Transcriber (WhisperX) and Analyzer (pysentimiento). `services/analyzer/app/` is the legacy synchronous service until phase 3 of the migration plan replaces it.

## Before you change anything

- **Decisions**: `docs/adr/`. Read the ADRs the change touches; a change that contradicts one starts with a new ADR.
- **Terms**: `GLOSSARY.md`. "task" only names pysentimiento's `task=` argument.
- **Order and done criteria**: `plans/migracion-monorepo.md`. The ADR wins when they disagree.
- **Code layout**: each service is a `src/` package organised by responsibility, transports at the edge (ADR-0023). New code goes there, never into `services/analyzer/app/`.

## Running models

Model weights (several GB) download on first load. Run anything that loads real models on Codespaces, RunPod or the RTX 3070 machine; locally, test with fake models.

## Gotchas in `services/analyzer/app/`

- `create_analyzer` has no `device` parameter: it is ignored for sequence tasks and raises `TypeError` for `ner`/`pos`. Device placement belongs to the Analyzer worker (plan, phase 2).
- The request's `config.lang` does not choose the model: models load with `settings.pysentimiento.LANG`, keyed by task alone.

## Conventions

- English in code, docstrings, API responses and `GLOSSARY.md`; Spanish in `plans/` and `docs/adr/`.
- Conventional Commits, one scope per commit.
- Tests live in a `tests/` folder beside the code they cover.

## Agent skills

### Issue tracker

GitHub Issues on `zanellig/voice-insights`, through `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default triage roles, plus service and risk labels; phases are milestones. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one root `GLOSSARY.md` and `docs/adr/`. See `docs/agents/domain.md`.
