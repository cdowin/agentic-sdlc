---
id: ft-every-rung-reuses-a-green-run
kind: feature
milestone: "ms-a-green-run-costs-under-two-minutes"
name: every rung reuses a green run
status: done
reviewed: docs/reviews/2026-09-30-0.18.0-reuse.md
depends_on: []
consumed_by: []
changelog: Every `verify` rung reuses a green run across the `status:` lines and ledger rows a belt writes, so a batch of `close feature <id> <id> …` and `release` run each rung once; `verify --milestone` re-asks the static rung (`[verify] static`, stock `make check`) before such a reuse, so a status flip that breaks `check pm` still fails; `[verify] reuse_ignores_status = false` keys every rung on every byte.
---

# every rung reuses a green run

Measured at 0.17.0: `close feature` on six features of one commit ran `make test` six times
(~2 min each), because every status write moves the feature rung's whole-tree digest. `release`
cannot reuse a green `make milestone`: the gate is asked with the milestone at `done`, which the
recorded run never saw (0.17.0 review C2). 0.17.0 fixed this for the story rung only
(`verify/main.py::rung_state`, `verify/cache.py`: an unscoped story rung leaves out each grain's
`status:` line and the ledger rows a close writes).

## Decided (do not re-plan)

- **Every rung leaves out what a belt writes.** Story, feature and milestone rungs all exclude
  each grain document's `status:` frontmatter line and the belt-written ledger rows (`status`,
  `disposition`, `deviation`, `check.verdict`, `rung.leave`, and any other kind a belt files
  about its own run). Every other byte stays in. One exclusion, one place — generalise the
  0.17.0 story code; do not copy it.
- **This makes `release` reuse**: a `make milestone` green recorded at `building` matches the
  same tree asked at `done`, since only the `status:` line differs. Prove it: green
  `verify --milestone`, then `release` prints the reuse clause and runs no gate.
- **The escape hatch** (0.17.0 green-run review F1): a project whose rung target READS statuses
  (for example a consumer whose story rung is `make check`, and `check pm` grades statuses)
  opts out with a `[verify] reuse_ignores_status = false` gate key (stock `true`, rule 5: the
  seed carries it commented at `true`). With `false`, every rung keys on every byte, as in
  0.16.0. Name the key in the reuse line so an operator can find it (rule 11).
- **`close feature <id> <id> …`**, as `close story` took in 0.17.0: grain-blind checks
  (`feature-verified`) once, per-grain checks per id, one write per id, exit 1 if any refused.
  Reuse the 0.17.0 `GRAIN_BLIND`/`asked_once` machinery; do not build a second one.
- Probes (rule 4): between two closes, an edit under `src/`, a `changelog:` edit, and a body
  edit to a grain each RE-RUN the rung; only a `status:` flip and belt rows reuse. With
  `reuse_ignores_status = false`, a status flip re-runs.

## Ship criterion

- Six `close feature` on one commit run the feature rung once (reuse printed five times, or one
  many-id call).
- `verify --milestone` green, then `release` on the same commit reuses it; no gate re-run.
- The four probes re-run; the opt-out key restores whole-tree keying.

## Proof budget

  cases: about 5 — reuse across feature closes, release reuse at done, the probes, the opt-out, many-id close feature
  tier: temp tree (the belt spawns: integration)
  lands in: tests for verify/cache.py, verify/main.py, conveyor/driver.py
  what already covers this: 0.17.0's story-rung reuse cases; extend them, do not duplicate.
