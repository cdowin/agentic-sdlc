# Feature review — `0.2.0/every-gate-reports-its-cost` — HOLD

Feature-level pass over the four stories' commit range (`6afa35d`, `6e9388d`), branch
`milestone/0.2.0-the-conveyor`, run 2026-09-05. Adversarial by execution: every claim below was
produced by sourcing the shipped `gdk_gate.sh` in `tempfile` scratch repos and reading the rows
it actually filed. No repo-wide git command was run.

The milestone record (`docs/reviews/2026-09-05-0.2.0-release-review.md`) is the reference for
what is already filed; nothing here re-files M1–M5 or L1–L5.

**Three blockers, and the shape they share is the one the milestone review named for M5: the
contract fails open on OUTCOME and does not hold on the axis it claims.** M5 was the time
bound; G1 is the same bound defeated by a different mechanism, G2 is the verdict column, and
G4 is a story that filed close evidence for work that was never done.

The clock, the sidecar keying, the six fail-open paths, the `PASS`/`FAIL`/`HANG` derivation
from `GDK_GATE_EXIT`, and `pm ledger record`'s refusal grammar all held under everything tried.

---

## The blockers

### G1 — a `GDK_LEDGER_CMD` carrying a command substitution runs OUTSIDE the recorder's bound

`src/agentic_sdlc/repo/installables/gdk_gate.sh:337` —
`if ! eval "prefix=($GDK_LEDGER_CMD)" 2>/dev/null; then`.

The bound is applied by `_gdk_ledger_run` (`:311`), which wraps the recorder in
`gdk_run_bounded "$GDK_LEDGER_TIMEOUT"`. The `eval` that parses `GDK_LEDGER_CMD` into `prefix`
happens **before** that call, in the gate's own shell, with no timeout anywhere near it — so
any `$(…)` or backtick in the value is executed unbounded.

Measured, `GDK_LEDGER_TIMEOUT=3`, wall clock per probe, whole gate through
`gdk_gate_log` → `gdk_gate_capture` → `gdk_gate_verdict`:

| GDK_LEDGER_CMD | elapsed | verdict line | note |
|---|---|---|---|
| (unset — baseline) | 30 ms | `[PROBE] done — full log: …` | — |
| `true` | 49 ms | unchanged | — |
| `sh -c 'sleep 120'` (direct child) | 3056 ms | unchanged | `recorder exited 124` |
| `sh -c 'sleep 120 & exit 0'` (M5's case, landed) | 52 ms | unchanged | — |
| **`true $(sleep 20)`** | **20062 ms** | unchanged | none |
| **``true `sleep 20` ``** | **20074 ms** | unchanged | none |
| `true <(sleep 20)` | 50 ms | unchanged | — |

The mechanism, isolated from the library:

```
GDK_LEDGER_CMD='true $(sleep 5)'; eval "prefix=($GDK_LEDGER_CMD)"
  -> 5031 ms, prefix=(true)
```

A 6.7× overrun of a 3 s deadline, on the path of every gate in every consumer, and it is
**quieter than M5**: M5 at least left `recorder exited 124` behind on the stderr note, while
this one produces no note at all — the eval succeeds, `prefix` is well-formed, and nothing in
the output says a second passed. The same file's comment block (`:287-290`) is the standard
this fails against: *"A broken recorder that hangs would otherwise hang every gate in a
consumer's pre-push hook, which is the one failure mode worse than a missing row."*

M5's table probed twelve values including `unparseable quoting`; none carried a substitution,
which is why the landing at `6250016` (moving the capture off a pipe onto a scratch file) does
not reach it. The fix is a different one: either do the parse under the bound, or refuse a
`GDK_LEDGER_CMD` containing `$(`, `` ` `` or `${` **by shape, before evaluating** — the posture
`ready_for._pointer_defect` already takes for the pointer payload three modules away.

Reachability is narrower than M5's: the stock spelling is a make variable, and `$(…)` in a
Makefile is expanded by make before the environment sees it. It is a consumer whose `DEVKIT`
spelling reaches the shell unexpanded that pays. The bound is claimed unconditionally, though,
and criterion 1 is what claims it.

### G2 — a runner that captures more than once per slot files the LAST command's exit code as the gate's verdict

`src/agentic_sdlc/repo/installables/gdk_gate.sh:436-450` (`gdk_gate_capture` assigns
`GDK_GATE_EXIT` on every call) and `:269-285` (`_gdk_ledger_verdict` reads whatever
`GDK_GATE_EXIT` holds when `gdk_gate_verdict` runs).

Measured, in exactly the shape this repo's own `matrix:` target uses — one `gdk_gate_log`, N
`gdk_gate_capture`, one `gdk_gate_verdict`:

```
recipe decided: fail=' first'   GDK_GATE_EXIT after loop=0
[MATRIX] FAIL on first — full log: …/.gate-reports/matrixlike.log
row filed: {"kind":"gate","gate":"matrixlike","verdict":"PASS","duration_ms":17}
```

**The console says FAIL and the cost row says PASS.** The duration is right; the one column
the ledger carries about correctness is inverted.

This is reachable in this checkout, not only in principle: `Makefile:204-232`'s `matrix` recipe
opens one slot at `:206`, calls `gdk_gate_capture` once per interpreter at `:221` under
`|| true`, accumulates failures into `$fail`, and publishes `gdk_gate_verdict MATRIX "FAIL
on$fail"` at `:229`. A matrix failing on `PY_FLOOR` and passing on the last interpreter in
`PY_MATRIX` files `PASS`. The five `matrix` rows in
`pm/roadmap/0.2.0-the-conveyor/ledger.jsonl` are all `PASS` at 220–273 ms, which is not a
plausible duration for that target; what those runs actually did was not separately
established, but the ledger cannot be used to find out, which is the finding.

The library's own docstring (`:170-178`) shows the case was anticipated on the other axis:
*"THE FUNNEL IS THE PAIR, KEYED ON THE LOG SLOT … not `gdk_gate_verdict` alone (a runner with
five alternative exits calls that more than once)."* Multiple **verdicts** were solved — first
one wins. Multiple **captures** were not, and `GDK_GATE_EXIT` is last-write-wins.

Hard rule 4, read side: this is a durable record that prints the opposite of what the gate
found, in the table whose stated purpose (feature.md, *"What it makes possible"*) is that
*"the gate set becomes arguable from data"*. Minimum fix: make `GDK_GATE_EXIT` sticky per slot
(first non-zero wins until the slot closes), or have `gdk_gate_verdict` take the status the
runner already computed.

### G4 — story 04 shipped nothing, and its `## Close` block names a commit that touched none of its files

`pm/roadmap/0.2.0-the-conveyor/features/every-gate-reports-its-cost/stories/04-a-dispatch-names-both-commands.md`,
`## Close`:

> `done: 6e9388d — the stock agent roster names the narrow command and the wide one.`

`6e9388d` touches exactly three files under `installables/`: `Makefile.devkit`, `gdk_gate.sh`
and `sdlc-template.md`. **It touches no agent definition.**

The story names five (`## Files this story may touch`): `architect.md`, `po.md`,
`developer.md`, `verification-builder.md`, `test-writer.md`. All five were last modified by
`f504ab5`, which belongs to a different feature (`0.2.0/the-middle-tier-splits`) and predates
the story:

```
architect.md            f504ab5 feat(0.2.0/the-middle-tier-splits): the installables stop describing one engine
po.md                   f504ab5  (same)
developer.md            f504ab5  (same)
verification-builder.md f504ab5  (same)
test-writer.md          f504ab5  (same)
```

Its acceptance criterion 1 — *"Each of the five named installables carries the block, and the
five copies are byte-identical to one another. Proven by an assertion in
`tests/test_install.py` that extracts the block from each and compares"* — has no such
assertion; `tests/test_install.py` contains no reference to it. The rule's own phrasing
(`narrow command` / `both commands` / `the wide one`) appears **nowhere** under
`src/agentic_sdlc/repo/installables/`. The four `narrow` hits across the fifteen installables
are unrelated: `verification-builder.md:71` is a heading about narrowing a gate's SCOPE (the
opposite subject), and `developer.md:19` / `project-CLAUDE.md:34` are pre-existing "test
slice" / "narrowest tier target" lines from `f504ab5`, and `project-CLAUDE.md` is explicitly
in the story's `## Out of scope`.

This is the finding a feature review exists to catch. The story is at `reviewing` with close
evidence that is not true, and a future session reading that block would take criterion 4 as
delivered.

---

## Non-blocking findings

- **G3 — the narrow-vs-wide ratio is unreachable by construction, so criterion 3 cannot be
  met by any project following the shipped layout.** `verify/main.py:515-527`: `_cost_of`
  joins a rung's command to a ledger row by MAKE TARGET NAME, and `gate_costs` (`:472-511`)
  only ever holds names passed to `gdk_gate_log`. The wide rungs are prerequisite-only targets
  — `Makefile:235` `precommit: gates hooks-self-test test`, `:239` `milestone: gates
  hooks-self-test matrix` — with no recipe, so they never open a slot and `costs` can never
  carry a key `precommit` or `milestone`. `_ratio` needs both ends, so it returns `unknown`
  forever. Measured on this repo, which has 47 gate rows across four gate names:

  ```
  story      make gates                 57 ms (FAIL)
  feature    make precommit             unknown
  milestone  make milestone             unknown
  ratio      unknown — no `gate` rows with these targets in …/ledger.jsonl
  ```

  The honesty is the strength — it says `unknown` rather than inventing the number, exactly as
  designed. But criterion 3 is *"The row makes the narrow-vs-wide ratio derivable"*, and the
  join makes it underivable for the wide half in every configuration this package ships. This
  is a different column from the milestone review's L3 (`GDK_GATE_CENSUS` set by nothing):
  that one is the census, this one is the ratio's denominator. Fix shape is a ruling, not a
  patch — sum a composition's prerequisites' rows, or open a slot for the composition itself.

- **G5 (NIT)** `--plan` renders a cost read from a FAILING run as `57 ms (FAIL)`. It does mark
  the verdict, which is right; worth noting only that 57 ms for `make gates` is the cost of a
  gate that stopped early, and a reader skimming the column for "what got slower" will read it
  as the gate's cost.

## The four ship criteria

| # | criterion | verdict |
|---|---|---|
| 1 | one row per run carrying name, duration, verdict and census, through the one funnel, **failing open** | **caveat** — the row lands on every path tried and fail-open on OUTCOME is solid (verdict line and gate exit code never moved across 12 probes). The **verdict** column is wrong in the multi-capture shape (G2) and the **bound** does not hold (G1). Census is structurally absent, which is the milestone review's L3, already deferred |
| 2 | `pm ledger report` grows the *what got slower* view | **met** — verified by the milestone review (criterion 5) and not re-derived here; the sixth section renders `runs/first_ms/last_ms/delta_ms/census` with `*` marking a moved census |
| 3 | the row makes the narrow-vs-wide ratio derivable | **not met** — G3. `ratio unknown` on the repo that self-hosts both halves, with 47 gate rows present |
| 4 | the stock agent definitions carry the name-both-commands rule | **not met** — G4. No installed agent definition carries it |

## Cross-story

- **No duplication found.** Stories 01 (`ledger.py` row + refusal grammar) and 02
  (`gdk_gate.sh` funnel) meet at exactly one seam, `pm ledger record`'s argv, and the shell
  side builds it in one place (`:344`). Story 03's report section reads the rows it does not
  write.
- **Story 02 did not weaken story 01's guard.** The row grammar is enforced in Python; the
  shell can only produce a refusal, never a malformed row. Confirmed: a non-numeric
  `GDK_GATE_CENSUS` is dropped with a note (`:346-350`) rather than passed through.
- **`## Close` claims.** Story 01's *"68 refusal cases"* — `tests/test_pm_ledger_record.py` is
  82 tests / 76 subtests, so the claim is conservative, not false. Story 02's *"`make gates`
  writes a real row"* — true, 39 `gates` rows in the ledger. Story 03's claim — not
  re-derived; the milestone review verified the section. **Story 04's is untrue (G4).**

## What was NOT verified

- **`make milestone`, `make gates` and the interpreter matrix were never run.** The ten
  modules covering these three features were: `418 passed, 337 subtests passed in 62.97 s`, my
  run, 3.11 only.
- **G2's blast radius outside `matrix`.** Only this repo's `Makefile` was read for
  multi-capture slots; `Makefile.devkit`'s `runners-self-test` open-codes the three calls
  (per feature.md) and was not checked for the same shape, and no consumer runner exists here
  to check.
- **The 50 MB `GDK_LOG_CAP_BYTES` boundary.** A gate printing past the cap would take SIGPIPE
  from `head -c` and land a non-zero `GDK_GATE_EXIT`; whether that files a `FAIL` row for a
  passing gate was NOT tested — 3 MB was as far as I went, and the cap is 52428800.
- **Unbounded bytes through a forked writer.** Probed (`dd` 2 GB behind `& exit 0` into the
  unlinked scratch fd); free space moved −152 KB over 4 s, i.e. not reproduced. Filed as
  nothing rather than as a theory.
- **The five `matrix` rows' 220–273 ms durations were not explained**, only shown to be
  unusable as evidence either way because of G2.
- **No consumer install was performed** — `install-agents` was not run into a temp repo; G4
  rests on the source tree and the commit range, which is where the block would have to be.

Reviewer's token cost: ~120k across all three feature records.

```
verdict: HOLD
| id | severity | disposition |
| G1 | BLOCKER | open: the eval at gdk_gate.sh:337 runs before the bound — parse under it, or refuse $( ` ${ by shape |
| G2 | BLOCKER | open: make GDK_GATE_EXIT sticky per slot, or pass the runner's status to gdk_gate_verdict |
| G3 | MAJOR | open: criterion 3 needs a ruling on how a composition rung gets a cost |
| G4 | BLOCKER | open: story 04 never landed; criterion 4 undelivered and its Close evidence is false |
| G5 | NIT | rejected: --plan already marks the verdict beside the cost, which is the honest rendering |
```
