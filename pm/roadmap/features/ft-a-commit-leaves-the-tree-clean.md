---
id: ft-a-commit-leaves-the-tree-clean
kind: feature
milestone: "ms-the-leader-finishes-the-job"
name: a commit leaves the tree clean
status: reviewing
reviewed: docs/reviews/2026-09-12-0.12.0-features.md
depends_on: []
consumed_by: []
changelog: Gate, test and verify rows land in the gitignored `<roadmap>/ledger.local.jsonl` (and `pm ledger record --gate` says so), so a commit whose hook runs the gates leaves the tree clean; re-run `pm init` to add the `.gitignore` line (#48).
---

# a commit leaves the tree clean

Issues: #48.

A consumer adopting v0.11.0 (5 parallel lanes) hit this, and so did 0.9.0–0.11.0 here: the pre-commit
hook runs `make check`, and its gates append rows to the TRACKED `pm/roadmap/ledger.jsonl`. So every
commit leaves the tree dirty. A lane merge (`git merge --no-ff feat/<lane>`) then fails, and
`agent-worktree.sh done` refuses. The workaround in the wild is `--no-verify` as routine, which hands
the orchestrator a bypass flag.

**Decided. Machine-local telemetry is not tracked.** Rows of kind `gate`, `test` and `verify` are the
cost of a run on THIS machine. They go to `<roadmap>/ledger.local.jsonl`, which is gitignored: the
installer that writes `.gitattributes`' `merge=union` line (grep `merge=union` in
`src/agentic_sdlc/repo/pm/`) also ensures a `.gitignore` entry, idempotently. Every reader of those
kinds reads the local file too: `verify --plan`, `pm ledger report --tree`, the milestone gate
tables, `check pm`'s U-rules if they count them, and `check budget` if it reads rows. Rows written on
purpose (status, decision, disposition, dispatch, session, stamp, deviation, lesson) stay in the
tracked ledgers. **A commit's own hook then writes nothing tracked.** Existing gate rows in tracked
ledgers stay where they are (append-only history) and are still read.

Note the flaky `U4…test_rows_this_checkout_wrote_itself_are_not_evidence_a_courier_ran` (failed once
under xdist on 2026-09-12, passed alone). If this change touches what U4 counts, make it
deterministic; otherwise leave it.

## Ship criterion

In a temp repo with the gates installed and the pre-commit hook armed, `git commit` leaves
`git status --porcelain` empty. `verify --plan` still prints each rung's last cost, read from the
local file. `pm ledger report --tree` still shows the gate table. A second install is a no-op.
Closing #48 cites this feature.

## Proof budget

  cases: 2–3 (routing by kind; readers see local rows; the gitignore entry idempotent)
  tier: unit (+ one integration row if the commit-hook proof needs a process)
  lands in: tests/test_pm_ledger_record.py, the verify-plan and report-tree cases, the install case
  what already covers this: gate rows route to the tree ledger (0.4.0/D3); nothing keeps them untracked.
