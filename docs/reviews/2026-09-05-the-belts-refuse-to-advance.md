# Feature review — `0.2.0/the-belts-refuse-to-advance` — SHIP-WITH-FIXES

Feature-level pass over the three stories' commit range (`6e9388d`, `f7465c2`), branch
`milestone/0.2.0-the-conveyor`, run 2026-09-05. Adversarial by execution: 42 probes through
`PYTHONPATH=src python3 -m agentic_sdlc.cli pm ready-for …` against `tempfile` scratch repos,
plus the three live features. No repo-wide git command was run.

The milestone record (`docs/reviews/2026-09-05-0.2.0-release-review.md`) is the reference for
what is already filed; nothing here re-files M1–M5 or L1–L5.

**These three verbs gate the release, and the code holds.** Sixteen hostile review records
beyond the milestone review's thirteen — a nested fence, a `rejected:` whose prose contains the
word `open`, a deferral to a traversal token, a language-tagged fence, an escaped pipe, a
clean block followed by an open-carrying one, a header-only table, a pointer with a trailing
slash — and nothing got past `ready-for tag`. Twenty-six probes at the feature and milestone
rungs: every refusal exits 2 with the right message, every blocker is NAMED rather than
counted, and both vacuity rulings behave as documented and say so in the output.

**The findings are all documentation.** The feature's own mid-milestone predicate change —
`f7465c2`, story→feature from *"every story `reviewing`"* to *"every story `done`"* — landed in
the code and in `SDLC.md`, and did **not** land in the two places a consumer reads: the verb's
own `--help`, and the README table that publishes the ladder.

---

## The findings

### B1 — `pm`'s own usage text still states the superseded predicate

`src/agentic_sdlc/repo/pm/cli.py:71`. Printed by `agentic-sdlc pm` with no arguments:

```
  ready-for feature|milestone|tag <id>    (the belt-entry condition below that
                                           rung, as an EXIT CODE: 0 ready,
                                           1 not ready — naming every blocker,
                                           never a tally — 2 usage. feature:
                                           every story at `reviewing`.
                                           milestone: every feature done with a
                                           non-empty review record. …
```

The code asks `done`:

```
$ pm ready-for feature 0.1/alpha     # two stories, both `reviewing`
  BLOCKED  0.1/alpha/s0 is reviewing
  BLOCKED  0.1/alpha/s1 is reviewing
[pm] NOT READY — feature 0.1/alpha: 2 blocker(s) named above, across 2 story/ies
EXIT=1
```

`ready_for.py:53-75` narrates the change at length and calls the old question *"wrong"*. The
help text next to it still asks it. An operator who reads `--help`, parks the feature's stories
at `reviewing`, and gets exit 1 has been told by the tool's own contract text that they should
have got 0 — and the two lines below it, for `milestone` and `tag`, are correct, so there is no
tell that this one is stale.

This is a published-API surface: CLAUDE.md rule 6 makes output shapes contract, and this repo
treats the CLI as one. `SDLC.md:61` was updated; `cli.py:71` was not.

### B2 — the README's ladder table asks the old question, in the row that names this verb

`README.md:103`:

```
| closing a story | `pm ready-for feature <fid>` | are this feature's sibling stories at `reviewing`? |
```

The rows above and below it are correct, including `README.md:107`'s `ready-for tag` row. This
is the table the milestone review cited as criterion 8's evidence (*"`README.md:100-107` carries
it"*) — the table was checked for existence and its content was not, which is exactly the gap a
feature-level pass exists to close.

Same defect as B1, different audience: B1 is read by whoever runs the verb, B2 by whoever is
deciding which rung to run.

## Non-blocking findings

- **B3 (MINOR) — `pm feature reviewing`'s advisory still uses the old set, and is silent
  exactly where the belt blocks.** `src/agentic_sdlc/repo/pm/cli.py:414`:
  `pending = [… for p, st in _story_states(cfg, fid) if st not in (model.REVIEWING, 'done')]`.
  A feature whose stories are all at `reviewing` flips with no advisory printed, and then
  `ready-for feature` names every one of them. Two surfaces answering *"is this feature's work
  finished"* with two different sets. The advisory is deliberately non-refusing
  (`:418-420`: *"Reported, never refused"*) and that ruling is right — but after `f7465c2` the
  set it reports is the pre-change one. `README.md:225` documents it as *"REPORT the stories
  that are not there"*, which is still true of the flip's own target state, so this is a
  judgement call rather than a plain bug; filed because "nothing still asks the old question"
  is the property the change was supposed to establish.

- **B4 (MINOR) — `ready-for tag` deduplicates records by unresolved pointer, so one file
  reached by two spellings counts twice.** `ready_for.py:426`,
  `records.setdefault(record.path, record)`, where `record.path` is `cfg.root / pointer`.
  `_record` already computes `os.path.realpath` for the containment check (`:275-278`) and
  throws it away. Measured on a case-insensitive filesystem, two features pointing at
  `docs/reviews/r.md` and `docs/Reviews/r.md`:

  ```
    RECORD   docs/reviews/r.md — 1 finding(s), none open
    RECORD   docs/Reviews/r.md — 1 finding(s), none open
  [pm] READY — tag 0.1: 2 record(s), 1 finding(s) x2, none open
  ```

  reported as `2 record(s), 2 finding(s)`. Not a false pass — an `open` finding would be found
  twice, not zero times — but the census over-counts both records and findings, and the census
  is what the verb prints as its proof of what it read. Keying on the realpath it already has
  fixes it.

## The five ship criteria

| # | criterion | verdict |
|---|---|---|
| 1 | three subcommands, exit `0`/`1`/`2` per the contract, each printing the **named** blockers | **met** — every blocker line I produced named the grain and its actual status word (`0.1/alpha/s0 is reviewing`, `0.1/alpha/s0 is wip`, `0.1/alpha/s9 is (no status:)`), never a tally. The `MAX_NAMED` cap discloses its own truncation. The `  BLOCKED  ` label is distinct from `  DRIFT  ` as the module argues it should be |
| 2 | a milestone with an open finding exits 1 from `ready-for tag` and names the finding ids, on a BUILT tree | **met** — `F1 open in docs/reviews/r.md`, exit 1; also on `OPEN` uppercase, on `open: <note>`, and on an open row in a SECOND block after a clean first one (`F2 open in …`, census `2 finding(s)`). Verified live on this milestone too, where the belt correctly reports all three of these features NOT READY |
| 3 | a feature with no stories is **ready**, stated in the docstring | **met** — `READY — feature 0.1/alpha: 0 story/ies — vacuously ready: an empty set is satisfied, and refusing it would make this verb unusable on a doc-only feature`. The `stories/`-holds-only-a-README case discloses the filter rather than the directory: `0 story/ies, 1 note(s) skipped (no frontmatter — not a grain) — vacuously ready`. The opposite ruling one rung up is equally loud and shares no phrase with it: `0.1 has no features — an empty feature set does not satisfy this belt; a mis-typed id looks exactly like this` |
| 4 | `pm vocabulary` is unchanged: these are read verbs | **met** — `ready_for.py` writes nothing on any path; `DONE` is derived from `model.LIFECYCLE[-1]` rather than respelled, and a project whose `story_states` omits `done` gets exit 2 naming the key rather than a silent answer |
| 5 | refusal matrix — nonexistent id, wrong grain kind, traversal in the id | **met** — all exit 2: a milestone id to `ready-for feature` (`'0.1' is a milestone, not a feature — 'ready-for feature' asks about a feature's stories`), a story id to the same, a feature id to `ready-for milestone`, `../../etc`, `/etc/passwd`, `0.1/*`, the empty id, no id, two ids, `--all`, and `wombat` as the kind. Pointer payloads are refused by SHAPE before any stat: trailing slash, `./`-prefixed, symlink, absolute, `~`, backslash, glob, URL, over-long |

## Cross-story

- **No duplication across the three.** `_record` is the single resolver both `ready-for
  milestone` and `ready-for tag` read a `reviewed:` pointer through (`ready_for.py:257`,
  called at `:376` and `:422`), which is story 03's own criterion 6 and holds. `_features`
  is the single feature walker for both. `_answer` is the single place the 0/1 contract is
  spelled, so the three predicates cannot disagree about which code means what.
- **The two rungs do not answer each other's question.** A feature with a BLANK `reviewed:`
  blocks `ready-for milestone` (`0.1/alpha is done, reviewed: is blank — no review record is
  named`) and is skipped by `ready-for tag` (`ready_for.py:418-421`), which is the documented
  split and is right: answering it twice is how two answers drift.
- **Bugs do not block a milestone** — verified live with an `open` bug under `bugs/`; the
  blocker list named only the feature. `model.feature_files` walks `features/` and nothing
  else.
- **The predicate change did not weaken anything.** `done` is strictly stricter than
  `reviewing`, and no other module reads `ready_for`'s answer except `conveyor/steps.py:2243`,
  whose `stories-done` step delegates rather than re-implements (asserted by
  `tests/test_conveyor_close.py:327`). `docs/sdlc-protocol.md:94` and `driver.py:447` both
  state the new predicate correctly.
- **`## Close` claims — all true.** Story 01's *"f7465c2 changed the predicate from `reviewing`
  to `done`"*: true, and the code asks `done`. Story 02's *"Bugs do not block a milestone; a
  milestone with zero features is LOUD"*: both verified. Story 03's *"Proven on this milestone:
  it named all ten and the conveyor refused"* — not re-derived (the ten findings have since
  been dispositioned), but the same shape was reproduced on a built tree. No untrue claim
  found in this feature.

## What was NOT verified

- **`make milestone`, `make gates` and the interpreter matrix were never run.** The ten
  modules covering these three features were: `418 passed, 337 subtests passed in 62.97 s`, my
  run, 3.11 only. `tests/test_pm_ready_for.py` is in that set.
- **`verdict.parse` was attacked only through `ready-for tag`**, never directly; the sixteen
  hostile records exercised the disposition grammar and the fence detection, not the verdict
  or severity closed sets.
- **`landed <hex>` is not checked against git.** `landed deadbeefdeadbeef` for a commit that
  does not exist passes, as does `deferred: 0.9/bugs/does-not-exist` for a grain that does not
  exist. Both are inside the documented grammar (`verdict.py:126-134` bounds the hash by LENGTH
  and the deferral by SHAPE) and neither is filed — but a deferral pointing at nothing is a
  disposition nobody can follow up, and `ready-for tag` will pass it.
- **A record whose CONTENT reviews a different milestone passes** when pointed at from this
  one (probed: a record headed `# 9.9.9 review` was accepted as `0.1`'s). The pointer is the
  tree's assertion and the verb trusts it by design; not filed, but it is the same class as
  the milestone review's noted `review_dir` bypass.
- **The `MAX_RECORD_BYTES` and `MAX_POINTER_LEN` bounds were read, not exercised.**
- **B4 was measured on a case-insensitive filesystem only** (macOS default). Whether a
  case-sensitive tree can produce the same double-count by another spelling was not
  established; `tests/support/pm.py:23-38` shows the harness already knows this distinction.
- **No consumer install was performed.** These verbs were exercised from source, per
  CLAUDE.md's never-through-`uvx` rule.

Reviewer's token cost: ~120k across all three feature records.

```
verdict: SHIP-WITH-FIXES
| id | severity | disposition |
| B1 | MAJOR | landed f4a9d6a |
| B2 | MAJOR | landed f4a9d6a |
| B3 | MINOR | landed f4a9d6a |
| B4 | MINOR | landed f4a9d6a |
```
