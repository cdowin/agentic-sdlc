# Feature review — `0.2.0/the-code-knows-entry-and-exit` — HOLD

Feature-level pass over `7209b9b`, branch `milestone/0.2.0-the-conveyor`, run 2026-09-06. Every claim
was produced by copying this tree to scratch, planting the input, running the verb and diffing the
bytes — nothing was concluded from reading a diff. **The tree moved under me:** my first copy was
`a7c5598`; `2fee466` and `7209b9b` landed mid-pass, one deleting `HANDOFF.md` and changing what
`make unit` asserts. All below is re-measured at `7209b9b`, story 07 — the close pass — still in flight.

## The blockers

- **E1 MAJOR** `CLAUDE.md:87` — the ladder row says closing a feature runs `make test`, both tiers;
  `close feature` runs 3 checks in 0.8 s and spawns no test. Shown by `close feature` on a scratch
  copy: `stories-done`, `review-recorded`, `findings-landed`, then the write.
- **E2 MAJOR** `pm/roadmap/0.2.0-the-conveyor/bugs/` — criterion 6 is false: four bugs name 0.2.0 not
  three, one is `fixed` not `closed`, one names 0.3.0, one names nothing. Shown by `pm ready-for
  milestone 0.2.0` → exit 1, and by `release 0.2.0` refusing on that check.

## The criteria

| # | criterion | verdict | proof |
|---|---|---|---|
| 1 | per-kind states echoed; `[pm.transitions]` and its reader gone | MET | `pm vocabulary` — 4 kinds, no transitions section; a planted `[pm.transitions]` refused at exit 2 by `pm vocabulary`, `pm status`, `pm list`, `check pm` and `close story` alike |
| 2 | `ready` is a stamp; readiness gaps WARN, exit unchanged | MET | `pm story ready` → `planning -> ready`, one line; all four gap classes WARN at exit 0 (no stories, empty `## Ship criterion`, no `branch:`, unphased feature, empty `## Acceptance criteria`) |
| 3 | D2/D3/D5/D6 disagreements are WARN lines, never findings | MET | four planted classes, exit 0, tree hash equal |
| 4 | every belt is D12; `close feature` takes any `done` word | NOT MET | belt runs below; **E1** |
| 5 | `ready-for milestone` names open bugs, `release` asks it | MET | `steps.py:630-631`; measured blocker line |
| 6 | the three 0.2.0 bugs `closed`; no bug names another milestone | NOT MET | **E2** |
| 7 | no record naming 0.2.0 has a finding at `open` | MET | `pm ready-for tag 0.2.0` → READY, 104 findings |
| 8 | the tree closes through the belts; status rows say so | NOT MET (in flight) | 39/40 stories, 15/16 features, 0/1 milestone |

On 1 and 2 the refusal is a reader refusing a malformed declaration (rule 9's exit-2 side), and on the
unmodified tree `check pm` ends `PASS … 11 warning(s)` — counted, exit code untouched.

**3 — MET.** Each class planted in its own copy; each produced a `  WARN  ` naming both grains **and
both categories**, at **exit 0**, counted in the summary, with the SHA-256 of every file in the tree
identical before and after — D2 `all stories done, feature still planning (todo) … (D2)`; D3 `milestone
0.2.0 is 'done' (done) but feature … is 'building' (in_progress) … (D3)`; D5 `story … is 'done' but its
feature … is still 'planning' … (D5)`, nine lines; D6 `… all 16 features are done … (D6)`. D2 is silent
over an `in_progress` feature, which `model.py:1003-1006` intends.

**4 — NOT MET (E1).** The D12 shape holds everywhere I measured it. `close story` with **one false
check**: all four checks ran and printed, the false one as `error: evidence-written: …`, then `error — 1
check(s) false; nothing written`, **exit 1**, story file byte-identical. **All true**: exit 0, sole change
`-status: planning` / `+status: done` — one line, the FIRST word of the story kind's `done` list (`done
obe`) — plus one row `{"kind":"status","from":"planning","to":"done"}`; run again, a no-op at
exit 0. **`--force`**: exit 0, `forced — … over 1 false check(s)`, same one-line write, plus
`{"kind":"deviation","step":"evidence-written","outcome":"forced","reason":…}` quoting the false check
in full. `close feature` over two stories at **`obe`**: `ok: stories-done — [pm] READY … all done`.

`release 0.2.0` on a scratch copy, `gate` substituted with `true` in `[release.commands]` since
`make milestone` is out of scope: all 7 checks ran and printed even after a false one; with all true it
stamped one line on `milestone.md` and **printed** a 10-line after-list — retitle, commit, push, PR,
merge, `git tag v0.2.0`, prove the artifact, open the next milestone — doing none of it. After:
`git tag -l` empty, HEAD unchanged, `pyproject.toml`, `src/agentic_sdlc/__init__.py` and `CHANGELOG.md`
byte-identical. Across every belt run the only files touched were the grain's record and
`ledger.jsonl`. `docs/sdlc-protocol.md:35-41` renders all seven release steps in
`DEFAULT_RELEASE_STEPS` order with command and postcondition; `:80`/`:95-97` do the story and feature.

**E1** is what fails. `DEFAULT_FEATURE_STEPS` (`steps.py:56-60`) is three steps; `feature-verified`
exists at `steps.py:1117` but its docstring says *"not in the shipped list"*, and this repo's
`devkit.toml` adds no `[feature] steps` to put it back, so `close feature` never runs the feature rung.
`docs/sdlc-protocol.md` is honest — three checks. `CLAUDE.md:87` is not. It is the failure
`devkit.toml:186-192` already records: *a ladder is only true while every rung names what it still
runs.* Fifteen features closed through it at `a7c5598`.

**6 — NOT MET (E2).** Of six bug records, three are `closed` at 0.2.0 — the three the criterion names.
But `the-deprecation-window-must-close` names 0.2.0 and is **`fixed`**, an `in_progress` word, making
four not three; `the-gate-census-column-is-always-absent` carries `fix_milestone: "0.3.0"`, against both
"no bug names another milestone" and the record's *"no 0.3.0"*; and `the-repo-forks-the-framework-it-ships`
is `fixed` with an **empty** `fix_milestone`, so no milestone owns it and nothing can see it.

**8 — NOT MET, in flight.** Every 0.2.0 grain in a `done` category carries a matching `status` row —
39/40 stories, 15/16 features, 3/6 bugs — and the milestone has none. The two missing are this feature
and story 07, the close pass under review, so the criterion is unfinished, not contradicted.
`pm status 0.2.0` shows phases 1-8 complete, `phase 9 (0/1 done)`; 147 status rows, 0 deviation rows.

**The story rung is what it declares.** `devkit.toml` `[verify] story = "make unit"`, and the belt
prints what it ran: `ok: story-verified — … the story rung [verify] names: verify --story: make unit $
make unit [UNIT] 655 passed, 2 skipped, 380 deselected, 395 subtests in 6.95s`. A full `close story`
took 8.3-8.6 s against 6.95-7.0 s for `make unit` alone — the gap is process start, so it runs that
target and nothing wider.

**E3 — a refused belt still leaves ledger rows — MINOR.** `close story` at exit 1 reported `nothing
written` and the story file was byte-identical, but `ledger.jsonl` gained 6 rows, all `kind: test` /
`kind: gate` costs from the `make unit` the check spawned; the belt wrote no `status`, no `deviation`.
D11's accepted cost — raised only because "nothing written" reads as "no byte changed".

**E4 — a comment names the wrong consumer — NIT.** `pm/model.py:61-62` says *"`LIFECYCLE`, `BUILDING` and
`REVIEWING` survive for `conveyor/steps.py`"* — those three appear nowhere under `repo/conveyor/`; the only
reader is `pm/cli.py:1356-1372`, the deprecated D7 `_tree_snapshot` exception.

**The seed-word census is clean.** Every string literal under `src/agentic_sdlc/` equal to a declared
word, by AST walk: `model.py:28` and `:63-80` — the category names and the `DEFAULT_FLOWS` seed, the config
reader — plus `verdict.py:56`, where `open` is a review disposition. No belt, check or CLI module spells a
state word; the belts' only write sites are `driver.py:443` and `pm <kind> done`. `make check`: 5/5 PASS.

## What I did NOT verify

- **`make milestone`, `make matrix`, `make test`** — out of scope by instruction; `release`'s gate step
  was substituted with `true`, so the belt's write path is measured and the gate is not. **`adopt`**,
  D12's fourth belt, had its step list read but never executed.
- **Whether `close feature` SHOULD run the feature rung.** E1 is claim-versus-behaviour; which side
  moves — `CLAUDE.md:87` or `[feature] steps` — is not mine to rule.
- **Criterion 8 at completion**; the **1 UNVERIFIABLE ref** `check pm` reports every run; and any
  **consumer install** — no `install-*` verb was run, so the doc census is this checkout alone.
- **I dirtied this repo's `ledger.jsonl`**: two `uv run pytest` invocations appended 17 rows, all
  `kind: test` / `kind: gate` and no `status` or `deviation`, so no PM state moved. Left in place since
  git writes are outside my remit — but `release`'s `tree-clean` will see it.

Reviewer's token cost: ~190k.

```text
verdict: HOLD
| id | severity | disposition |
| E1 | MAJOR | landed 693d409 |
| E2 | MAJOR | landed 693d409 |
| E3 | MINOR | landed 693d409 |
| E4 | NIT | landed 693d409 |
```
