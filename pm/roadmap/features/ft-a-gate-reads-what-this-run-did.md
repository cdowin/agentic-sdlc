---
id: ft-a-gate-reads-what-this-run-did
kind: feature
milestone: "ms-the-last-line-tells-the-truth"
name: a gate reads what this run did
status: planning
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# a gate reads what this run did

Two issues where a gate grades a record that is not this run's: #67 grades a frozen tracked row,
#74 ignores a fresh green run and pays 18 minutes to make it again.

## Decided (do not re-plan)

- **#67 — `check budget` never grades the tracked ledger.** Gate rows went to
  `ledger.local.jsonl` in 0.13. `budget.py` `_rows()` falls back to the tracked `ledger.jsonl` when
  the local file has no rows, so on a CI runner it grades rows frozen days ago and fails every PR.
  Remove the fallback for gate rows. A budgeted tier with no local row prints
  `UNMEASURED <tier> — no run recorded in <local ledger>` and does not fail. The check's census
  line says how many tiers it graded: `budget: graded 0 of N tier(s) — no local gate rows (a fresh
  checkout or a CI runner)`. That is rule 4 held by naming the zero, not by failing on it: the
  runner is ephemeral and has no history to grade. A stale LOCAL row is graded as today.
- **#74a — the release `gate` reuses a green milestone rung.** `check_gate`
  (`repo/conveyor/steps.py`) runs `[release.commands] gate` with no cache. When `gate` is the
  stock default, read its verdict through the verify cache the way the story step does
  (`_own_verdict(ctx, 'verify', '--milestone')`): a green `verify --milestone` recorded on the
  same tree state and graded-rows digest is reused and the step says so (`reused — green at <ts>
  on tree <short>`). A declared non-default `gate` command runs as today. The loop's skill text
  (`run-the-sdlc` step 10) is edited by `ft-an-arrival-names-what-it-starts`, not here.
- **#74b — a story's changelog is answered by its feature.** In `repo/pm/changelog.py`
  `unanswered`, a done story whose feature carries a non-empty `changelog:` counts as answered.
  `changelog <id>` renders nothing new for it. A story with its own line still renders it.

## Ship criterion

- `check budget` with no local ledger and a tracked ledger of old FAIL rows exits 0 and prints
  `graded 0 of N`.
- `release` after a green `verify --milestone` on the same tree does not run `make milestone`
  again; after one tracked edit it does.
- `release` on a milestone whose stories are blank under answered features passes
  `changelog-unreleased-nonempty`.

## Proof budget

  cases: 4-5
  tier: unit
  lands in: existing budget / conveyor steps / changelog test modules
  what already covers this: search first (rule 10); amend before adding
