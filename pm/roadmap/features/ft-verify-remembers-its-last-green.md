---
id: ft-verify-remembers-its-last-green
kind: feature
milestone: "ms-a-move-is-an-event"
name: verify remembers its last green
status: done
reviewed: docs/reviews/2026-09-07-0.5.0-verify-remembers-its-last-green.md
depends_on: []
consumed_by: []
---

# verify remembers its last green

GitHub issue #10. **The gate already knows, and it has no way to say so — which is this milestone's
northstar with a different subject.**

`[verify] feature = "make test"`, tree-wide by design; the `[[verify.narrow]]` glob engine was
removed deliberately on 2026-09-06 and that decision is not reopened here. The consequence is that
`feature-verified` verifies the TREE, and a tree has one state at a time. So closing seven features
runs one 90s suite seven times, and runs 2..N answer a question whose input did not change.

    story      make unit        17803 ms (census 845)
    feature    make test        90170 ms (census 1254)
    milestone  make milestone  124207 ms

Ten and a half minutes per seven-feature milestone, of which nine are repetition.

## The shape

`verify --story|--feature|--milestone` records its verdict against the TREE STATE it ran on — git
HEAD plus a hash covering the working tree, tracked and untracked. A later run whose state is
byte-identical reports the recorded verdict **with its provenance** — when, what target, what census
— instead of re-running.

This is a read, not a decision. `verify --plan` already reads each rung's last COST from the ledger;
this reads its last VERDICT from the same rows. Rule 9 holds: nothing is inferred about a tree that
changed, because any difference at all re-runs.

## What makes it safe, stated as the rule it could break

Hard rule 4: *a gate that misses drift and prints PASS* is the first cardinal sin. A reused verdict
is exactly that shape if it is ever wrong or ever quiet. So:

- **The state hash covers untracked files.** A new file that breaks collection must invalidate.
- **A reuse is PRINTED, always**, naming the run it came from and its age. A reused green that looks
  like a fresh green is the sin; loudness is the fix, not re-running.
- **`--no-cache` re-runs unconditionally**, and CI uses it — a cold tree in CI has no rows anyway,
  but the flag makes that explicit rather than incidental.
- **A malformed or unreadable row re-runs.** Never trust the record over the tree.

## Ship criterion

A second `verify --feature` on an unchanged tree reports the recorded verdict without running the
target, prints that it did and where the verdict came from, and exits with the recorded code. One
byte changed anywhere in the working tree — tracked, untracked, or HEAD — and it re-runs.

Asking one rung twice about one tree costs one gate run and one read: a bare `verify --feature`
repeated, and `close feature` run straight after a green standalone `verify --feature`.

**Closing N features on an unchanged tree still costs N runs, and that is recorded here rather than
claimed away.** A belt is its checks then ONE write (D12), and that write is the grain's `status:`
line — a tracked byte inside the state the next close computes, so close #1 is precisely what
invalidates close #2. Attribution, measured: restoring only that line returns the digest to its
pre-close value. Making it free means the BELT handing its rung a state computed before its own
write is planned, which is a design question about the belt and not a setting on this cache; a
feature document is also input to `check pm` inside `make milestone`, so simply dropping grain
documents from the state would be the same cardinal sin one level down. See
`docs/reviews/2026-09-07-0.5.0-verify-remembers-its-last-green.md` (E3).

## Proof budget

  cases: 7
  tier: pyunit for the trust boundary, shell for the wiring
  lands in: `tests/test_verify_cache.py` (pure) and `tests/test_verify_main.py` (end to end)
  what already covers this: the rung-resolution cases exist in `test_verify_main.py`; the reuse
    cases are rows on that harness, because only a sentinel file can prove a target did not run.
    `_verdict`, `ledger_digest` and the reuse lines are pure functions and are proven by CALL, in
    the tier `make unit` runs — the trust boundary is the one piece that can commit rule 4's first
    sin, and a `shell`-marked module is deselected by the story rung. The untracked-file
    invalidation case is the one that must exist, because it is the cheapest way to make a green
    tree red without touching a tracked byte.

## Out of scope

Caching across machines or checkouts. The rows are this tree's ledger and stay local; a shared cache
is a distributed-consistency problem this package has no business having.

Narrowing what a rung runs. That engine was removed on purpose. This makes the SAME tree-wide run
cost once instead of N times; it does not make it smaller.
