# Feature review — `0.2.0/the-story-belt-knows-what-verifies-this-edit` — SHIP-WITH-FIXES

Feature-level pass over the five stories' commit range (`6afa35d`, `fb8fa2a`, `6e9388d`,
`cc0569d`), branch `milestone/0.2.0-the-conveyor`, run 2026-09-05. Adversarial by execution:
every claim below came from running `PYTHONPATH=src python3 -m agentic_sdlc.cli verify …`
against `tempfile` scratch repos built for the purpose. No repo-wide git command was run.

The milestone record (`docs/reviews/2026-09-05-0.2.0-release-review.md`) is the reference for
what is already filed; nothing here re-files M1–M5 or L1–L5.

**The most dangerous failure this feature could have — `verify --changed` running LESS than it
claims — was hunted specifically and NOT found.** The miss path is the strongest surface in
the range: every unclaimed path is named, the widest rung runs unconditionally, `--plan` and
`--changed` agree on every tree they were both shown, and the selector's
`matched + missed == changed` invariant makes a silent zero-command pass unreachable rather
than merely unlikely. The reverse direction is equally sound — both zero-census forms are
loud, and prefix matching is segment-bounded as story 03 claims.

**The two findings are on the CHECKER, not the selector**: `verify --check` reports PASS over
a rule that can never fire, and its census counts something other than what it names.

---

## The findings

### S1 — a rule that can never be selected passes `verify --check` clean

`src/agentic_sdlc/repo/verify/select.py:195-209` (`_first_match` — first matching rule wins,
per path) against `src/agentic_sdlc/repo/verify/main.py:629-694` (`_check` — which asks each
rule in isolation whether its glob matches tracked files).

Three rules, all claiming the one file under `src/`:

```toml
[[verify.narrow]]
paths = "src/**"
run = "make narrow"

[[verify.narrow]]
paths = "src/a.py"
run = "make feat"

[[verify.narrow]]
paths = "src/<n>.py"
run = "make wide"
```

```
$ verify --check
[verify:check] PASS — 3 rule(s), 3 matched file(s) scanned of 4 tracked
EXIT=0

$ verify --changed          # after editing src/a.py
verify --story: 1 changed path(s) -> 1 command(s)
  $ make narrow
```

Rules #2 and #3 are unreachable. Every path they could claim is claimed first by #1, so
`make feat` and `make wide` will never run for any diff, ever — and the checker whose entire
job is that the declaration does not rot reports PASS over both.

`select.py:35-38` is right that first-match-wins is the correct rule (*"A path is not fanned
out across every rule that could claim it; that would make ADDING a rule silently multiply the
work"*) — this is not a selector defect. It is that the CHECKER asks a per-rule question
(*does this glob match tracked files?*) when the property that matters is a whole-set one
(*can this rule ever be first?*). The feature's own third property names the failure exactly:
*"A rule whose glob matches no tracked file … is a finding — same posture as a stale allowlist
entry. **A rule set nobody validates rots into one that quietly matches nothing.**"* A
shadowed rule matches nothing, forever, and validation says it is fine.

This is the shape ship criterion 3 asks for, one level up: `--check` already catches the
zero-tracked-files case with the right words (`matches ZERO tracked files — a rule pointed at
a path that was renamed away rots into a rule that quietly matches nothing, forever`).
Shadowing is the same rot arriving by a different route, and it is the likelier one — nobody
renames a path and then re-adds a rule for it, but everyone adds a specific rule under a
general one.

Minimum fix: `--check` already enumerates the tracked corpus, so it can run `select` over it
once and report any rule with zero paths where it was FIRST.

### S2 — `--check`'s census counts (rule, file) pairs and calls them "matched file(s)"

`src/agentic_sdlc/repo/verify/main.py:629-694`, the verdict line.

Six rules, all `paths = "src/a.py"`, in a repo tracking three files:

```
[verify:check] FAIL — 6 finding(s); 6 rule(s), 6 matched file(s) scanned of 3 tracked
```

**Six matched files scanned, of three tracked.** One file exists that any rule matched. The
number is the sum over rules of each rule's own match count, rendered with a noun that means
distinct files and compared against a denominator that is distinct files.

The same arithmetic is visible in the passing case above — `3 matched file(s) scanned of 4
tracked` where exactly one file matched — and in the milestone review's own evidence for
criterion 7, `PASS — 20 rule(s), 198 matched file(s) scanned of 202 tracked`. That line reads
as a coverage statement (198 of 202 tracked files are covered by a rule) and is not one; on
this repo the two happen to be close because its twenty rules mostly do not overlap, which is
a property of the config rather than of the gate.

CLAUDE.md hard rule 4: *"When scoping/globbing/excluding, prove the file census matches intent
(count what you scanned)."* A census that can exceed its own denominator is not counting what
it scanned. It is not a false PASS — the findings are per-rule and correct — but it is the
census line a consumer reads to decide whether the gate looked at anything, and it can be
argued from and disagree with `git ls-files`.

Minimum fix: count the union of matched paths, or rename the column to say it is per-rule
matches.

## Non-blocking findings

- **S3 (MINOR) — `--check` validates make targets only, so a `run` naming a nonexistent
  executable passes.** Measured: `run = "wombat-does-not-exist --please"` →
  `[verify:check] PASS — 1 rule(s), 2 matched file(s) scanned of 6 tracked`, exit 0, and
  `--plan` prints it as the story rung. Ship criterion 3 asks only for the make-target case,
  so this is a gap rather than a violation — but it is the same gap story 05's own `## Close`
  block records finding by other means: *"15 narrow rules named `python3 -m pytest` and bare
  python3 here has no pytest. **verify --check passed them**; `close story` found it."* The
  story fixed the fifteen rules; the checker that passed them is unchanged, so the sixteenth
  will pass too. Non-blocking because the failure is loud at run time (measured: the same
  spelling under `--changed` exits 1 with `No module named pytest`), and because deciding what
  "this command is runnable" means without booting anything is a real design question under
  hard rule 2.

## The five ship criteria

| # | criterion | verdict |
|---|---|---|
| 1 | N files under one captured directory run the slice **once** | **met** — verified by the milestone review (9 changed paths → 6 deduplicated commands) and by `select.py:170-192`, where dedupe is post-substitution and first-emission-ordered. Re-derived here on a two-file capture |
| 2 | a changed path matching no rule prints that path and runs `wide` | **met**, and it is the best surface in the feature. Mixed diff, one matched and one missed: `verify --story: 1 changed path(s) match no [[verify.narrow]] rule: / tests/test_a.py / falling back to the milestone rung — a narrow run that skipped these would report success for work it never checked / $ make wide`. The matched rule's command is DROPPED rather than run alongside, which is right — the wide rung subsumes it. `--plan` on the identical tree prints `story (falls back: 1 changed path(s) match no rule)` and lists the same path: **the two agree** |
| 3 | `--check` fails a rule whose glob matches zero tracked files, and one whose `run` names a nonexistent target, each with the rule's own index | **caveat** — both cases fire with the index (`[verify.narrow] #1: paths 'nope/**' matches ZERO tracked files`; `[verify.narrow] #3: run 'make narrow2' names make target 'narrow2', which …/Makefile does not declare`). The reverse direction adds two more, both loud: `scan … matched 1 file(s) and NONE declares '## covers:'` and `scan … matches ZERO tracked files — the louder zero`. But see S1 and S3 for what it does not catch, and S2 for what it says it counted |
| 4 | no `[verify]` section: `--changed` says so and exits 2 | **met** — and the deprecation is sharper than the criterion asks: a section still spelling `wide` instead of `milestone` exits 2 on all three flags naming decision D3, rather than silently running the old key |
| 5 | the refusal matrix per `SDLC.md` §5 | **met** — `tests/test_verify_rules.py` carries 112 hostile inputs and passes; `select.py:237-282` refuses absolute, `..`/`.`/empty-segment, control-character, backslash and over-long changed paths, and `substitute` (`:212-234`) refuses a bound capture carrying any of `; \| & $ ` ( ) < > # \` plus whitespace and quotes, naming both the binding path and the rule index. Not re-derived case by case; the module's own suite is green (see below) |

## Cross-story

- **No duplication found across the five.** The capture spelling is deliberately respelled in
  two places (`rules.CAPTURE` a parser's, `select.CAPTURE` a substituter's) and `select.py:96-99`
  states why — that is a documented decision, not drift.
- **No later story weakened an earlier one's guard.** Story 02's dedupe and story 03's reverse
  resolver enter through the same `_first_match`, and `select` is a pure function of
  (rules, paths) with no filesystem access — story 03's `declares.py` does the reading and
  hands in a resolver. The invariant at `select.py:17` holds structurally: every path lands in
  `matched` or `missed`, never neither.
- **One census is asserted in two places and they cannot disagree**, because `_run_story` and
  `_plan` both call `plan_for` rather than each computing a selection — checked at
  `main.py:400-408`, `:437`, `:532`.
- **`## Close` claims — all true as far as tested.** Story 03's *"Segment-bounded, because an
  unbounded prefix is the off-by-one that silently over-selects"*: verified — a header reading
  `## covers: src/a` selects for `src/a/x.py` (`make narrow NAME=one`) and does **not** claim
  `src/ab/y.py`, which falls to `missed`. Story 02's *"proven end-to-end through the verb and
  not only in the selector"*: verified live. Story 04's *"`--plan` prints measured cost from
  the ledger and the word `unknown` where none exists, never an estimate"*: verified, including
  the `ratio unknown` line naming the ledger path. Story 05's *"README carries the table"*:
  true, `README.md:100-107` — though one of its rows is wrong, filed as B2 on
  `the-belts-refuse-to-advance`, whose predicate it misstates.
- **Cross-feature.** This feature's headline claim — *"It reports the ratio, and that is what
  makes the rule obvious"* — is structurally unsatisfiable in the shipped layout, for a reason
  that belongs to `every-gate-reports-its-cost`. Filed there as G3, not double-filed here; the
  rendering side (`_ratio`, `_cost_of`, the `unknown` wording) is correct and honest.

## What was NOT verified

- **`make milestone`, `make gates` and the interpreter matrix were never run.** The ten
  modules covering these three features were: `418 passed, 337 subtests passed in 62.97 s`, my
  run, 3.11 only. `tests/test_verify_{rules,select,main,declares}.py` are all in that set.
- **The 112-input refusal matrix was not re-derived case by case** — criterion 5 rests on that
  module being green, not on my own probes, which covered only the path and capture classes.
- **No `verify --story` was run on this repo to completion**, the same gap the milestone review
  records. My end-to-end runs were all in scratch repos with `make` stubs.
- **`declares.py`'s scan cost on a large corpus was not measured**, and `_scans` reads the whole
  tracked list whenever any reverse rule exists.
- **A capture binding a leading-dash value was probed and not filed.** `src/-rf.py` →
  `python3 -m pytest tests/test_-rf.py -q`; the dash is never token-leading in any shipped
  spelling, and `run` is a tracked file the repo owns (the feature's own risk 1). A
  `run = "make unit <sys>"` where `<sys>` binds `-j99` would put a bare flag on the command
  line; not constructed, not filed.
- **Windows / case-insensitive path behaviour of the selector** was not exercised beyond the
  backslash refusal.

Reviewer's token cost: ~120k across all three feature records.

```
verdict: SHIP-WITH-FIXES
| id | severity | disposition |
| S1 | MAJOR | landed 3935205 |
| S2 | MAJOR | landed 3935205 |
| S3 | MINOR | landed 3935205 |
```
