# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those roles to the actual label strings used in this repo's issue tracker.

| Label in mattpocock/skills | Label in our tracker | Meaning                                  |
| -------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`             | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`               | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`          | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `ready-for-human`    | Requires human implementation            |
| `wontfix`                  | `wontfix`            | Will not be actioned                     |

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the corresponding label string from this table.

Edit the "Label in our tracker" column to match whatever vocabulary you actually use.

## Project labels

Applied alongside the triage role. A ticket carries one service label and any risk labels that fit.

| Label | Meaning |
| --- | --- |
| `svc:api` | Touches the Jobs API |
| `svc:transcriber` | Touches the Transcriber |
| `svc:analyzer` | Touches the Analyzer |
| `pkg:contracts` | Touches `packages/contracts` |
| `infra` | Touches compose, APISIX or deploy config |
| `needs-gpu` | Done only after a run with real models on Codespaces, RunPod or the RTX 3070 machine |
| `privacy` | Touches Voices, embeddings, identities or retention (ADR-0013, 0015, 0016) |
| `adr` | Contradicts an ADR or needs a new one before implementation |
| `optional` | Nice to have; evaluate before committing to it |

Tickets on different service labels can usually run in parallel; tickets on the same one usually touch the same files.

## Milestones

Each migration phase in `plans/migracion-monorepo.md` is a milestone (`Fase 0 – …` to `Fase 7 – …`). A ticket belongs to exactly one.
