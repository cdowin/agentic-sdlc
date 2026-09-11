Append with `agentic-sdlc pm decide <grain-id>` — never by hand; the command stamps the date and the next ordinal.

# ms-nothing-is-hand-rolled  — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-09-10 — the citation rule resolves the qualified form and says nothing about the bare one

`bg-a-decision-citation-resolves-to-the-wrong-milestone` asked for a rule where
**a bare `D<n>` outside its own decisions file is a finding.** Measured before
implementing, that rule is wrong far more often than it is right, and the
measurement is the whole argument.

    [doc] scope     33 bare `D<n>`, of which 32 are `check pm` GATE RULE IDS
                    — D12 (a belt is its checks), D4 (an undeclared status),
                    D9/D10 (the branch rules). Bare is CORRECT there: the gate
                    ids are one flat namespace that never restarts.
    pm/roadmap/     343 bare, ~273 with no gate context — decision citations,
                    against 20 in the qualified `<version>/D<n>` form.

**The two namespaces are indistinguishable by shape.** `check pm` declares
D1, D2, D4, D5, D6, D9, D10, D11, D12; milestone decisions run D1–D12 as well.
A gate that flagged the bare form would fire on 32 of 33 correct citations in
the always-loaded docs — rule 4's first sin inverted, a gate that reports drift
where there is none, which is the gate somebody deletes.

**Rejected: flag the bare form anyway and allow-marker the gate ids.** That is
32 `<!-- doc-scan:allow -->` markers in the surface an agent reads every
session, to catch a defect class that has bitten once. The marker exists for a
deliberate exception, not for the majority reading.

**Rejected: gloss-matching.** The original defect carried its own tell — ``D1
(`emit`, never execute)`` against a D1 titled *a parent does not close over
unresolved children* — so a rule could compare the parenthetical against the
decision's title. It is a heuristic over prose, it fails open on any citation
with no gloss, and a fuzzy gate is the one whose failures get re-run rather
than read.

**Taken:** the qualified form is resolved and the bare form is not read at all.
21 citations are graded today. What this does NOT catch is the exact defect
that filed the bug — a bare `D1` resolving to a real ruling that says something
else — and that is stated in the grain rather than implied away. Closing that
needs the tree to adopt `<version>/D<n>` as mandatory in grains, which is a
273-site migration and a decision of its own, not a line in this close.

## D2 — 2026-09-11 — a trailing telemetry row is expected, not drift, and the belts already say so

`bg-the-push-gate-dirties-the-tree-it-just-cleaned` is real and four fixes were
listed for it, each losing something: drop the row (loses cost data for the runs
that happen most), amend inside the hook (forward-only forbids it), untrack the
ledger (loses the history three verbs read), `.gitignore` the root file (deletes
the destination `0.4.0` designed for unattributed rows).

**None is taken, because the repo's own checks already hold the correct
position.** `close story`'s `committed` check reads *"no modified path outside
`pm/roadmap/`"* — `steps.py:106` carries the full argument for that exclusion,
and leg (ii) is this one: N builders share one worktree, so a bare `git status
--porcelain` is dirty during any real inner-loop call, and *"a rung that cries
wolf is one an agent learns to ignore, and the ignoring generalises to the rungs
that do work."*

So: **a pending `gate` or `session` row under `pm/roadmap/` is machine-written
telemetry, it is `merge=union`, and it is not uncommitted work.** The belts are
right and nothing in this package reports otherwise. What complains is tooling
OUTSIDE the repo that asks `git status` the coarse question — and the answer to
that is the same as leg (ii): ask the narrower question, which `close story`
already does.

**Rejected: make the hook silent.** The pre-push gate is the run that happens
most, so its cost row is the most valuable one in the file. Deleting a real
measurement to keep `git status` quiet trades the thing this package is for
against a cosmetic.

What survives as a genuine cost, and is recorded rather than fixed: the residue
is always the same uninteresting file, which trains the blind `git add` that
`tools/hooks/cc-commit-pathspec.sh` exists to block. That guard fired on this
session's own orchestrator once, correctly, and is the mitigation already in
place.

## D3 — 2026-09-11 — the case ceiling is on the suite, not the tier

`[tests] cases` was `{ unit = 1140, integration = 430 }` and is now `{ test = 1575 }`: one
ceiling, on the run that collects the whole suite. `[tests] budget` stays per TIER.

**What forced it: a per-tier COUNT measures tier MEMBERSHIP, not growth.**
`bg-the-integration-tier-counts-fixtures-not-integration` moved 62 cases from `integration` to
`unit` by deleting a dead function-local `import subprocess` and one `git_tree as tree` alias.
Nothing was written, nothing was deleted, and no assertion changed. The suite went 1,571 → 1,586
collected — real growth of 15 — while the `unit` ceiling read **+72 over** and the `integration`
one gained 56 of headroom it had not earned. A gate that reddens hardest when the tier boundary
is CORRECTED teaches people not to correct it, which is the shape of a gate that makes the tree
worse.

**Rejected: drop the count and keep only the clock.** Chris put this directly — unit tests are
pure function checks, so what we care about there is time. The clock cannot carry it: `unit` went
706 → 1,212 cases, **+72%, for 8.2s → 9.6s, +17%**, because xdist absorbs the rest. A tier really
can double inside its time budget. So the split is: **time per TIER**, because that is what a
human waits for and it differs per tier; **count per SUITE**, because that is what grows and it
does not care which side of the mark a case sits on.

**Also rejected: keep both, per tier and per suite.** Three numbers to re-argue at every close,
two of which move when nothing grows.

`test` is the whole suite in one run (`$(PYTEST) $(PYTEST_N)`, no `-m`), so its census IS the
number — and `GDK_MILESTONE_TIERS` gained `test` in the same change, because a limit graded from
a measurement the gate never takes is exactly the hole
`bg-an-uncounted-tier-passes-the-case-ceiling` records.

The number carries no headroom on purpose: growth is argued, not absorbed, and it is re-set once
at each close with the reason. The full working is in `devkit.toml` beside the key, where the
next author stands; this record is the durable half, because a config comment dies with its key.
