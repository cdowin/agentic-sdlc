---
id: bg-the-push-gate-dirties-the-tree-it-just-cleaned
kind: bug
milestone: ms-nothing-is-hand-rolled
name: the pre-push gate files a ledger row, so a pushed tree is never clean
status: fixed
caused_by:
changelog: none
---

# the push gate dirties the tree it just cleaned

Found by running the loop: an agent session in this repo cannot reach a clean
tree, and the stop-hook check that asks for one fires on every turn.

## Symptom

    $ git status --short          # clean
    $ git push origin <branch>
    [CHECK] 5 check(s) PASS
    ...  <branch> -> <branch>
    $ git status --short
     M pm/roadmap/ledger.jsonl    # dirty again, from the push that just ran

Every push leaves an uncommitted `gate` row behind. Committing it and pushing
that produces another one. **There is no sequence of commands that ends with
the tree pushed and clean.**

## Root cause

`tools/hooks/pre-push` declares `PUSH_GATE=(make check)` and runs it before a
branch push lands. `check` files a `gate` row into `pm/roadmap/ledger.jsonl` —
that is `every-gate-reports-its-cost` working exactly as designed. The row is
written during the hook, so it lands in the WORKING TREE after the commit being
pushed was made, and therefore never travels with it.

The two features are individually correct and nobody put them together: the
gate must run before the push, and running the gate is a write.

## Why it is worth a record rather than a shrug

**It trains people to `git add` blindly.** The residue is always the same file
and always uninteresting, which is exactly the habit `tools/hooks/cc-commit-pathspec.sh`
exists to prevent — the shared-worktree sweep the 0.6.0 handoff records. A repo
whose normal state is one boring dirty file teaches the reflex the guard blocks.

It also makes "the tree is clean" useless as a precondition, and `close story`
has a `committed` check that asks exactly that.

## Fix — not chosen, because each has a real cost

  * **Do not file a `gate` row when the gate runs from a hook.** Cheapest;
    loses the cost data for the runs that happen most.
  * **Amend the row into the commit being pushed.** Rewrites a commit inside a
    hook, on a branch, mid-push. Forward-only says no.
  * **Let the ledger be untracked and reconstructed.** Loses history, and the
    ledger is the telemetry surface three verbs read.
  * **`.gitignore` the root ledger and keep the per-milestone ones.** The root
    file is where unattributed rows go by design (`0.4.0`), so this deletes a
    designed destination.

**A decision, not a defect to patch** — and it was taken: `0.7.0/D2`.

## Out of scope

The `session` row `cc-ledger-session.sh` writes at Stop. That one is a courier
doing its job at the end of a session, not a loop.

## Decided — `0.7.0/D2`, and the grain's own framing was wrong

**No fix is taken and the behaviour is correct.** `close story`'s `committed` check already reads
the narrower question — *"no modified path outside `pm/roadmap/`"* — and `conveyor/steps.py:106`
carries the argument: N builders share one worktree, so a bare `git status --porcelain` is dirty
during any real inner-loop call, and *"a rung that cries wolf is one an agent learns to ignore, and
the ignoring generalises to the rungs that do work."* A pending `gate` or `session` row under
`pm/roadmap/` is machine-written telemetry, it is `merge=union`, and it is not uncommitted work.
What complains is tooling OUTSIDE this repo asking the coarse question.

**Two things this grain got wrong about itself**, corrected here rather than silently:

  * It said it was *"filed to the pool rather than bound to a milestone"*, and it is bound to
    `ms-nothing-is-hand-rolled` — correctly, because the decision that settles it is recorded
    under that milestone. The sentence described an intention nobody carried out.
  * It sat at `fixed` while its own `## Fix` section said *"not chosen"*. `fixed` and
    *"we decided not to"* are different answers and the tree held both at once.

What survives as a genuine cost, recorded rather than fixed: the residue is always the same
uninteresting file, which trains the blind `git add` that `tools/hooks/cc-commit-pathspec.sh`
exists to block. That guard fired on this session's own orchestrator once, correctly.

