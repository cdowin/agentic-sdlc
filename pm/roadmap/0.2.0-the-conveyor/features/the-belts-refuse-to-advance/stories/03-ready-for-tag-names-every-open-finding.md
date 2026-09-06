---
id: 0.2.0/the-belts-refuse-to-advance/03-ready-for-tag-names-every-open-finding
feature: 0.2.0/the-belts-refuse-to-advance
milestone: "0.2.0"
name: ready-for tag names every finding still at open
status: done
owner:
depends_on: ["0.2.0/the-belts-refuse-to-advance/02-ready-for-milestone-names-the-features-that-block-it"]
---

# ready-for tag names every finding still at open

<!-- What is observable when this ships. A story is an observation, not a task. -->

`agentic-sdlc pm ready-for tag <milestone-id>` exits 0 when every finding in every review
record the milestone points at sits at a disposition other than `open`. Exit 1 names the
finding ids and the record each came from:

```
M1, M2 open in docs/reviews/2026-09-05-x.md
m1, m2, m3, m4 open in docs/reviews/2026-09-05-y.md
```

**This is the one that would have caught this package's own worst habit.** 0.24.0's release
ran `make milestone` before the reviewer, twice, and both runs were void the moment the
review asked for fixes; the reviewer had filed M1, M2 and m1-m4 at `disposition: open`.
SDLC.md's close protocol now says the gate goes LAST — `ready-for tag` is that sentence with
an exit code.

## Where the records come from

The features' `reviewed:` pointers — the same set story 02 resolves — **plus** any record the
milestone document itself points at. The feature file does not say this; it is ruled here so
a milestone-level cross-cutting review (close protocol step 1, which is exactly the pass that
files the findings this verb reads) is not invisible to the verb that gates on it. If the
orchestrator prefers a `[pm] review_dir` sweep instead, that is a ruling to raise in the
report — but a directory sweep would also read records belonging to other milestones, which
is why it is not the default here.

## UNVERIFIABLE is never a pass

The feature's risk 2: a review record is prose. `verdict.parse` raises `NoVerdict` when a
record carries no verdict block and `MalformedVerdict` when it carries a broken one. **Both
are blockers**, reported as `UNVERIFIABLE` with the record path and the parser's own message
— precision over reach, exactly as the gates already rule. A record whose verdict block does
not parse is the single easiest way to get a false green out of this verb, and it is the
reason `parse`'s two exception types are handled separately from a clean parse returning zero
findings.

A record that parses to **zero findings** is a pass for that record, and the output says
`0 findings` for it rather than staying silent — a record contributing nothing must be
visibly counted, or a record the verb never opened looks identical to a clean one.

## Files this story may touch

- `src/agentic_sdlc/repo/pm/readyfor.py` — the third predicate.
- `tests/test_pm_ready_for.py`.
- `tests/fixtures/` — PM-tree fixtures plus vendored review records carrying verdict blocks.
  Rule 8: **build the tree as a fixture; do not assert against this repo's live
  `docs/reviews/`**, which this milestone is actively adding to and deleting from (close
  protocol step 5).

## Files it must stay out of

`src/agentic_sdlc/repo/pm/verdict.py` — **consume `verdict.parse`, never extend it.** A
parser change is a change to every consumer's review record and belongs in its own story.
Also out: `src/agentic_sdlc/repo/pm/cli.py` (story 01), `model.py`, `report.py`, `ledger.py`,
`checks/pm.py`, `src/agentic_sdlc/cli.py`, `pm/roadmap/`.

**SERIAL after story 02** — same module.

## Acceptance criteria

1. A fixture milestone with an open finding exits 1 and names the finding **ids** and the
   record path (feature criterion 2, which requires the tree be a fixture rather than this
   repo's live state). Proven by `tests/test_pm_ready_for.py`.
2. A fixture where every finding is `landed`, `rejected` or `deferred` exits 0 and prints the
   census it checked: how many records and how many findings. Proven by a case — a bare
   "ready" over records the verb failed to open is the false PASS this feature exists to
   prevent.
3. **`NoVerdict` and `MalformedVerdict` are each exit 1, reported as `UNVERIFIABLE` with the
   record path and the parser's message.** Two fixture records, one of each. Neither may be
   caught as "no findings".
4. A record that parses with zero findings is counted and shown as `0 findings`, and exits 0
   on its own. Proven by a case asserting the record path appears in the output of a passing
   run.
5. **A milestone whose features point at NO records at all exits 1**, saying the record set
   was empty — the same anti-vacuity ruling story 02 made for an empty feature set, and for
   the same reason. Proven by a case.
6. A `reviewed:` pointer that story 02 already treats as a blocker (missing, empty, glob,
   traversal) is a blocker here too, with the same message — the two predicates share one
   resolver rather than each writing its own. Proven by one case per class, and by the
   resolver being a single function with two callers.
7. A record carrying MORE THAN ONE verdict block (`verdict.parse` returns a list) has every
   block's findings considered — not just the first. Proven by a fixture record with two
   blocks where only the second holds the open finding. *An N-pass review record is the
   normal shape; reading only block one is a silent pass over the pass that mattered.*
8. Nothing is written; the fixture tree is byte-identical after the run. Proven by a case.
9. Stories 01 and 02's cases still pass unmodified.
10. Slice command for the loop: `python3 -m pytest tests/test_pm_ready_for.py tests/test_verdict.py -q`.

## Refusal matrix

The argv grammar is story 01's and the `reviewed:` pointer payload is story 02's; neither is
re-litigated. **What this story adds is a document parser's input** — the review record's
bytes — so those cases ship here. Each must be `UNVERIFIABLE` (exit 1) or refused, never a
pass, and none may write:

| record content | expected |
|---|---|
| no verdict block | UNVERIFIABLE (`NoVerdict`) |
| a verdict block with a missing or extra column | UNVERIFIABLE (`MalformedVerdict`) |
| a disposition word that is not in `verdict.DISPOSITION_KINDS` | UNVERIFIABLE, naming the word |
| a verdict block inside a fenced example block, or an unfenced near-miss | handled exactly as `verdict.parse` already rules — this story asserts the behavior, it does not change it |
| a finding id containing `../`, a `/`, or 33+ characters | refused by `verdict`'s own id grammar; assert the verb surfaces it rather than swallowing it |
| a record 10 MB long, or with a 1 MB single line | bounded read; reported rather than consuming memory |
| a record that is not UTF-8 decodable | UNVERIFIABLE naming the path, never a crash and never a skip |
| a record whose verdict block is empty (header and separator, no rows) | ruled explicitly in the docstring and proven — zero rows is not the same fact as zero findings after a real review, and whichever way it is ruled, it must be stated |

**Adversarial cases against the docstring.** The predicate will claim that an unparseable
record is never a pass, that it never writes, that every verdict block in a record is read,
and that it never opens a file outside the checkout. Generate against each — in particular a
record whose FIRST block is clean and whose second is malformed (must be UNVERIFIABLE, not a
pass on the strength of block one).

## Out of scope

- Changing `verdict.py`, its grammar, or its exception types.
- The disposition vocabulary, and any new disposition word.
- Wiring `ready-for tag` into the release step machine — that is
  `0.2.0/the-release-is-a-conveyor` (phase 4), which calls this verb rather than
  reimplementing it.
- `--json`, and any flag.
- Reading `docs/reviews/` as a directory. The pointers are the record set (ruled above).

## Close

done: 6e9388d — reads the review record's verdict block and names every finding still at
`disposition: open`. Proven on this milestone: it named all ten and the conveyor refused.
13 hostile records probed; nothing got past it, malformed ones UNVERIFIABLE with line numbers.
