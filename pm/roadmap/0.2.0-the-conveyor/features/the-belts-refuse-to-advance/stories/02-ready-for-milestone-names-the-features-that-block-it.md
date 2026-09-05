---
id: 0.2.0/the-belts-refuse-to-advance/02-ready-for-milestone-names-the-features-that-block-it
feature: 0.2.0/the-belts-refuse-to-advance
milestone: "0.2.0"
name: ready-for milestone names every feature that is not done with a record
status: reviewing
owner:
depends_on: ["0.2.0/the-belts-refuse-to-advance/01-ready-for-feature-names-the-stories-that-block-it"]
---

# ready-for milestone names every feature that is not done with a record

<!-- What is observable when this ships. A story is an observation, not a task. -->

`agentic-sdlc pm ready-for milestone <milestone-id>` exits 0 when every feature under that
milestone is `done` **and** each one's `reviewed:` pointer resolves to a file that is not
empty. Exit 1 names each blocker and says which of the two conditions it failed:

```
0.2.0/the-extraction-finishes is reviewing
0.2.0/the-middle-tier-splits is done, reviewed: names no file (docs/reviews/x.md)
0.2.0/the-kit-owns-… is done, reviewed: is empty
```

`check pm`'s D1 already asserts a `reviewed:` pointer resolves; this verb asks the same
question with an exit code, and adds the one D1 does not ask — **is the record actually
non-empty**. A zero-byte review record satisfies "the file is there" and proves nothing.

## The empty-milestone case is the loud one

The feature's risk 1: *"Vacuous truth is a false PASS wearing a bow."* Criterion 3 of the
feature makes an empty STORY set vacuously ready — that is story 01's ruling and it stands.
**A milestone with zero features is the opposite ruling and it is deliberate:** it is far
more likely a mis-typed id than a real state, so it exits 1 and says so. Both rulings live in
the docstring next to each other, because a reader who finds only one of them will assume the
other is a bug.

## Files this story may touch

- `src/agentic_sdlc/repo/pm/readyfor.py` — the second predicate.
- `tests/test_pm_ready_for.py`.
- `tests/fixtures/` — PM-tree fixtures, built here (rule 8), never this repo's live tree.

## Files it must stay out of

`src/agentic_sdlc/repo/pm/cli.py` — story 01 routed all three names and shipped the argv
refusal matrix; needing an edit here means 01 routed it wrong, and that is a finding for the
report rather than a fix in this story. Also out: `model.py`, `verdict.py`, `report.py`,
`ledger.py`, `checks/pm.py`, `src/agentic_sdlc/cli.py`, `pm/roadmap/`.

**SERIAL after story 01** — same module.

## Acceptance criteria

1. A fixture milestone whose features are all `done` with resolving, non-empty records exits
   0 and prints the count it checked (`5 features, all done with a record`). Proven by
   `tests/test_pm_ready_for.py`.
2. Exit 1 names each blocker **and the reason it blocked** — not-done, pointer-resolves-to-
   nothing, or record-is-empty — one line each, no tally. Proven by a fixture carrying one of
   each of the three, asserting all three ids and all three reasons appear.
3. **A milestone with zero features exits 1**, naming the milestone and saying the set was
   empty. Proven by a fixture case, and by a second case asserting the message differs from
   story 01's vacuously-ready wording so the two cannot be confused in a transcript.
4. A `reviewed:` pointer that is present but blank, and one naming a directory rather than a
   file, are each blockers with distinct messages. Proven by two fixture cases. *A pointer
   naming a directory is the case that would otherwise pass an `exists()` check.*
5. **Bugs are not features.** A milestone's `bugs/` grains do not enter this predicate, and
   the docstring says so — otherwise an open bug silently blocks a milestone whose features
   are all closed, and nobody would find out why from the output. Proven by a fixture with a
   `building` bug and all features done, asserting exit 0. *If the orchestrator wants bugs to
   block, that is a ruling, not a defect — raise it in the report rather than deciding it
   here.*
6. A feature holding a status outside the vocabulary is a blocker with the word it holds; the
   verb reports and never repairs. Proven by a fixture case.
7. Nothing is written; the fixture tree is byte-identical after the run. Proven by a case.
8. Story 01's cases still pass unmodified — the shared module gained a predicate and changed
   no behavior. Proven by the whole file being green.
9. Slice command for the loop: `python3 -m pytest tests/test_pm_ready_for.py -q`.

## Refusal matrix

No new input surface: the argv grammar and the id resolver are story 01's, and its matrix
already covers `ready-for milestone` with a feature id, a story id, traversal, globs, dot
segments, absolutes and over-long ids. **What this story adds is a payload it reads** — the
`reviewed:` pointer value out of a feature's frontmatter — so those cases ship here, each
proven to refuse or contain without reading outside the checkout and without writing:

| `reviewed:` value | expected |
|---|---|
| `../../../etc/passwd`, `/etc/passwd` | blocker naming the feature; **nothing outside the checkout is opened** (hard rule 8) |
| `~/notes.md`, `file:///x`, `https://x/y.md` | blocker; no expansion, no fetch |
| `docs/reviews/*.md` | a glob is a blocker, not a set to resolve — a pointer matching two records proves neither |
| `.`, `..`, `docs//x.md`, `docs/./x.md` | blocker |
| `docs\\reviews\\x.md` | backslash is not a separator |
| a symlink pointing outside the checkout | blocker; not followed |
| a 4096+ character path | blocker |
| a path whose file is 0 bytes, or whitespace only | blocker (criterion 2) |
| a path that is not UTF-8 decodable | blocker naming it, never a crash and never a skip |

**Adversarial cases against the docstring.** The predicate will claim it never opens a file
outside the checkout, never follows a symlink out, and never writes. Generate against each,
plus the claim in criterion 5 that bugs do not participate — a fixture whose `bugs/` directory
contains a file shaped exactly like a feature must still not be counted.

## Out of scope

- `ready-for tag` — story 03. This predicate stops at "done with a non-empty record" and
  never parses the record's contents.
- Parsing verdict blocks. That is story 03, through `verdict.parse`.
- Changing `check pm` D1, or adding a D-rule for the empty-record case. If D1 should tighten,
  say so in the report; the gate is a different surface with different consumers.
- `--json`, and any flag.

## Close

done: 6e9388d — names each feature and its state. Bugs do not block a milestone; a milestone
with zero features is LOUD, since that is likelier a mistyped id than a real state.
