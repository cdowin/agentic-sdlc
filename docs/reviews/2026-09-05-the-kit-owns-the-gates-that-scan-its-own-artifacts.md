# Feature review — `0.2.0/the-kit-owns-the-gates-that-scan-its-own-artifacts`

Feature-level pass (SDLC.md §0) over the commit range its two stories name in their `## Close`
blocks: `6e9388d`, `14dca39`. Branch `milestone/0.2.0-the-conveyor`, run 2026-09-05.

This feature is the most heavily reviewed range in the milestone: M1, M2 and M3 in
`docs/reviews/2026-09-05-0.2.0-release-review.md` are all against `check grain-shape`, and all
three are landed. None of them is re-filed here. The cross-story question that pass could not
ask: story 01 shipped a gate whose whole contract is *"a walk that kept nothing while leaving
something unexamined must be loud"*, and story 02 shipped a gate whose whole contract is *"a
guard nobody wired is not there"* — so this pass attacked the first gate's zero-census path
through a mechanism the M2 fix does not cover, and asked the second gate what its census is
actually of.

**Verdict: HOLD.** `check hooks` is the strongest thing in the range and survived every attack
tried. `check grain-shape` still has one path where a zero census prints PASS over a subtree it
could not read.

---

## What holds

`check hooks` was attacked in a `tempfile` consumer built by the shipped `install-hooks`, armed
with `core.hooksPath`, and every probe answered correctly:

| probe | verdict |
|---|---|
| corpus installed, not armed | `FAIL — 3 finding(s) across 7 hook(s)`, `UNARMED` first |
| armed, two entries missing exec bits | `FAIL`, both named, remedy named |
| armed and clean | `PASS — armed at tools/hooks; 7 hook(s); 5 fail open …, 2 parse, 2 replay their own --self-test corpus` |
| a hook's `--self-test` made to print `SELF-TEST BROKEN` | `FAIL`, `SELF-TEST` finding quoting the hook's own output |
| a new hook declaring `--self-test` and answering exit 0 with no `SELF-TEST OK` | `FAIL` — the lie is caught, not the exit code |
| a new hook mentioning `--self-test` only in a comment | not a candidate, correctly |
| **every** `--self-test` declaration stripped from the corpus | `FAIL — NO CORPUS … an uninstalled corpus and a passing one print the same word from here` |
| a stray `.bak` file left in `tools/hooks/` | counted as an entry and flagged — git's hook universe, not a filtered one |

Loud on zero works, the census is of the directory rather than of a roster, and candidacy is
derived from each hook's source rather than from a `HOOKS_WITH_CORPUS` list — which is the
specific defect the module docstring says it was written against. This half of the feature is
done.

`check grain-shape` is also fast, in-process and correct on the paths it does see: 48 documents
in 0.086 s on this repo, against the 34.8 s the consumer-authored script took over 683 — the
number the feature was argued on, and it holds. The M1 fix is present and correct in shape: the
census is in **both** verdict lines now (`grain_shape.py:279-306`), and a walk that kept nothing
while leaving something `unexamined()` FAILs. The M2 mechanism is present in
`core/walk.py:282-293` — `descendants()` runs a second `rglob('*')` purely to find symlinked
directories `rglob(pattern)` would never yield, and the disclosure works: with one real grain and
a symlinked `stories/` holding a 901-line story, the verdict line carries
`1 symlinked dir(s) NOT descended (a symlink may leave the checkout)`.

## Findings

### K1 — BLOCKER — a directory `check grain-shape` cannot read is invisible to the census, and the zero path prints PASS

`src/agentic_sdlc/core/walk.py:279` (`path.rglob(pattern)`) and `:289-292` (the symlink sweep),
reaching `src/agentic_sdlc/repo/checks/grain_shape.py:279-306`.

`Path.rglob` swallows the per-directory `OSError` and yields nothing from a subtree it cannot
open. Nothing raises, so `_classify` records no `Skip`, so `Walk.unexamined()` is **0**, so the
`if found.unexamined():` branch the M2 fix installed never fires. `SkipReason` has
`EXCLUDED_PATH` and `SYMLINKED_DIR`; it has no reason for *"the filesystem refused"*, because
nothing is there to name.

Measured, scratch repo in `tempfile`. `pm/roadmap/0.1.0/stories/` at mode `000`, holding a
901-line story, and no other grain in the tree:

```
[check:grain-shape] PASS — 0 PM document(s) under pm/roadmap/; pm/roadmap/ holds no grain
document yet, so there is nothing to measure. `check pm` is the gate with an opinion about a
PM tree being there
EXIT=0
```

Zero census, positive claim about the tree, exit 0, and the directory it could not enter is
disclosed nowhere. That is M1's sentence exactly — *"a walk that kept nothing while leaving
something unlooked-at cannot tell an empty tree from a scope that lost one"* (`grain_shape.py:
292-296`) — surviving through a third mechanism after the first two were closed.

The non-zero half is the same hole, quieter. With one readable milestone beside the unreadable
`stories/`:

```
[check:grain-shape] PASS — 1 PM document(s) under pm/roadmap/; measured … story 0/200
EXIT=0
```

The census reads `1` and carries no narrowing at all, so an operator cannot tell this run from a
tree that genuinely holds one document. Compare the symlink case on the same tree, which does
disclose. Two ways to lose a subtree, one disclosed and one not.

`grain-shape` is `True` in `KNOWN_GATES`, so this is in every consumer's default roster on the
pin bump — and the misplacement argument this whole feature rests on is that fixing a gate *here*
fixes it for everyone. This is the fix that did not fully land.

Minimum shape of a fix, and it belongs in `walk.py` where the other two live: enumerate the
directories under `path` and record a `Skip` with a new reason for each one that cannot be
listed, then include that reason in `is_unexamined`. The existing symlink sweep already pays for
a second `rglob('*')`; this can ride on it.

I did not treat the disclosed-symlink-with-a-non-empty-census case as a finding. It discloses,
and the ruling that a disclosed narrowing may still pass while an undisclosed one may not is
defensible and is written down. It is a caveat, not a miss.

### K2 — MINOR — story 01's `## Close` names the wrong commit for the M1 fix

> *"Release review M1/M2 landed in 14dca39: the census goes in both verdict lines, and a walk
> that kept nothing while leaving something UNEXAMINED is loud."*

`git show --name-only 14dca39` is two files: `pm/roadmap/0.2.0-the-conveyor/milestone.md` and
`src/agentic_sdlc/core/walk.py`. It does not touch `grain_shape.py`. The second clause — the
`unexamined()` mechanism — is genuinely there. The first clause, the census going into both
verdict lines, is a `grain_shape.py` change and it landed in **`cc0569d`**
(`feat(0.2.0/the-inner-levels-are-belts-too): closing a story and closing a feature are belts`),
32 added lines in that file, a commit belonging to a **different feature**.

`git log -- src/agentic_sdlc/repo/checks/grain_shape.py` is two commits: `6e9388d` and `cc0569d`.
A future session following this Close block to `14dca39` finds no change to the module the
sentence is about. The milestone record's own disposition row (`| M1 | BLOCKER | landed
14dca39 |`) carries the same error and is where the Close block copied it from; that record is not
mine to amend, but the propagation is worth naming — a wrong hash in a verdict row becomes a
wrong hash in every close block that trusts it.

### K3 — MINOR — the self-test replay covers only the two hooks that never block

In a stock consumer, `install-hooks` writes seven files and exactly **two** declare a
`--self-test` corpus: `cc-ledger-session.sh` and `cc-ledger-subagent.sh`. Both are the ledger
couriers. Per `CLAUDE.md` they *"judge nothing, and every path out is exit 0"*.

The three hooks that actually block — `cc-commit-pathspec.sh`, `cc-stop-gate.sh`,
`cc-write-confine.sh` — declare no corpus, and neither do `pre-push` or `prepare-commit-msg`. So
the gate's fifth question, `STILL SAYS NO`, has **zero** blocking-hook coverage in the shape this
kit ships. The verdict line reads:

```
[check:hooks] PASS — armed at tools/hooks; 7 hook(s) under tools/hooks/; 5 fail open on a
payload they cannot read, 2 parse, 2 replay their own --self-test corpus
```

Every number in that line is true. `2 replay their own --self-test corpus` nonetheless reads as
coverage of the guards, and it is coverage of the couriers. The module docstring's own worked
example for why the replay matters is `cc-godot-sandbox.sh` — *"it is on disk, it is executable,
it looks installed, and it stops nothing"* — and that hook left with the engine half in
`8f4e9c1`, taking the only block/allow corpus in the kit with it. What is left is a gate whose
strongest question ships pointed at nothing that says no.

This is a coverage finding, not a correctness one: the gate reports honestly and fails loudly
when the count reaches zero. The gap is that three shipped guards are one deletion away from
being disarmed with the gate still green — which is the failure mode this feature's own title is
about. Either the three blocking hooks grow a corpus, or the verdict line should distinguish
hooks that *can* block from hooks that cannot.

## Ship criteria

`feature.md` states no numbered ship criteria; its `## Scope` table is read as the criteria.

| # | scope row | verdict |
|---|---|---|
| 1 | a prose-cap check over grain documents, NEW here, one pass rather than per-file spawns | **met with a caveat** — `check grain-shape` is in-process, 48 documents in 0.086 s; K1 is the caveat |
| 2 | the hooks / runners / sandbox self-tests MOVE into `[checks] all` from per-consumer wiring | **caveat** — two of the four moved, not four. `hermetic-scan` and `runners-self-test` act on engine artifacts and left the kit under D2, which is the right call and is the rule this milestone settled. Story 02's Close reports the true number and the reason; `feature.md`'s table still says four and was not amended (it is not mine to edit) |
| 3 | `[checks] all` default roster GROWS, each addition argued | **met** — `grain-shape` is at `True` with its ownership argument written out in `cli.py:148-157`, and the roster is three names, not five |
| 4 | consumer `[gates] extra` SHRINKs by four in the tree that had them | **not verifiable here, correctly** — hard rule 8; this package cannot gate on another repo's content, and a consumer proves its own integration at its pin bump |
| — | risk 2: the check must be a no-op, not a failure, on a repo with no `pm/roadmap` | **met** — `PASS — no pm/roadmap/ in this repo, so there are no grain documents to measure` (`grain_shape.py:271-277`), and it says it measured nothing rather than staying quiet |
| — | risk 1: ships reporting-only or with the ceiling read from config | **met** — caps come from `[grain_shape] caps` and the verdict line prints the measured-vs-cap table per kind |

## What I ran

- `uv run --python 3.11 --with pytest python -m pytest tests/test_grain_shape.py
  tests/test_check_hooks.py tests/test_gate_roster.py tests/test_cli_surface.py
  tests/test_wheel_payload.py tests/test_fresh_project.py tests/test_makefile_include.py
  tests/test_consumer_independence.py -q` → **152 passed, 1 skipped, 30.20 s**.
- `PYTHONPATH=src python3 -m agentic_sdlc.cli check all` on this repo → five gates PASS,
  `grain-shape` over 48 documents.
- `time … check grain-shape` on this repo → **0.086 s total**.
- Scratch repo in `tempfile`, four grain-shape trees: a real over-cap story (FAIL, exit 1, the
  finding named); the same story behind a **symlinked** `stories/` with one real grain (PASS,
  exit 0, symlink disclosed); the same story inside a **mode-000** `stories/` with one real grain
  (PASS, exit 0, **nothing disclosed**); the same with no other grain (PASS, exit 0, **zero
  census**).
- Scratch consumer in `tempfile`: `install-hooks`, `git init`, eight `check hooks` probes —
  the table above. Each verdict line read in full.
- `git show --name-only 14dca39`; `git log --oneline -- src/agentic_sdlc/repo/checks/
  grain_shape.py`; `git show cc0569d -- …/grain_shape.py`; `git log --oneline 6e9388d..HEAD`.

## What I did NOT verify

- **`make milestone`, `make gates`, `make fuzz` and the interpreter matrix were not run.** Eight
  test modules on 3.11 only.
- **M3's fix was not re-probed.** An absolute and a relative `[pm] roadmap_dir` were not re-run
  against `check grain-shape`; the milestone record's disposition (`landed 6250016`) is taken as
  read, and `6250016` is outside this feature's commit range.
- **`_kind_of`'s hardcoded slot names were not re-examined** — that is L5 in the milestone record,
  deferred to `0.2.0/bugs/the-slot-names-are-spelled-in-six-places`.
- **K1's blast radius outside `check grain-shape` is unmeasured.** `walk.descendants` is shared;
  which other gates lose a subtree the same way through an unreadable directory was not tested,
  and `walk.named` uses `os.walk`, which reports differently again.
- **The unreadable-directory case was produced with `chmod 000`, as the same user.** I did not
  test the shapes that arise from a different owner, an ACL, or a container's mounted checkout;
  the mechanism (`rglob` suppressing `OSError` per directory) is the same, but only one trigger
  was run.
- **`check hooks` was probed against the corpus this kit installs, not against a consumer's.**
  A consumer with its own hooks in `tools/hooks/` was not built.
- **No hook's actual guard semantics were tested** — only arming, executability, fail-open on an
  unreadable payload, and the self-test replay. A hook rewritten to `exit 0` unconditionally would
  pass this gate, which is the gate's documented scope and not a finding.
- **The 34.8 s comparison number was not reproduced.** It is a measurement of a script in another
  repo, which hard rule 8 puts out of reach from here; the 0.086 s half is mine.
- The tree was live during this pass — `check grain-shape` reported 46 documents at one point and
  48 later — so the PM counts are a snapshot. Every source file named was read at HEAD with a
  clean `git status`.

Reviewer's token cost: ~100k for the three-feature pass, of which this record is one part.

```
verdict: HOLD
| id | severity | disposition |
| K1 | BLOCKER | open: walk.py:279 — an unreadable directory records no Skip, so unexamined() is 0 and the zero-census path prints PASS |
| K2 | MINOR | open: story 01's Close credits 14dca39 with the grain_shape.py half of M1; it landed in cc0569d |
| K3 | MINOR | open: only the two ledger couriers declare a --self-test corpus, so the replay covers no blocking hook |
```
