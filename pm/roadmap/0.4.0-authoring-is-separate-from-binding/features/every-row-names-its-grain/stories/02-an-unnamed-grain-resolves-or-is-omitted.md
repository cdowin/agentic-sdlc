---
id: 0.4.0/every-row-names-its-grain/02-an-unnamed-grain-resolves-or-is-omitted
feature: 0.4.0/every-row-names-its-grain
milestone: "0.4.0"
name: An unnamed grain resolves from the tree, or is omitted
status: done
owner: claude
depends_on: ["0.4.0/every-row-names-its-grain/01-the-couriers-carry-the-grain"]
---

# An unnamed grain resolves from the tree, or is omitted

<!-- What is observable when this ships. A story is an observation, not a task. -->

A row that arrives without `--grain` gets one from the tree when the tree has exactly one answer,
and gets **no `grain` key at all** when it has none or several. It never gets a guess.

This is the orchestrator's path. Story 01 covers the dispatched agent, which is told its grain; an
orchestrator session nobody dispatched has no prompt to read it from, and that is the session type
most of this milestone's work happens in — including the session that wrote this story.

## The resolution, and the one rule that outranks it

The tool already answers the same shape of question one level up: `in_progress_milestones(cfg)`
is "which milestone is live". This is `holds(cfg, 'story', …, IN_PROGRESS)` — which stories are
live — narrowed by `owner:` when the caller supplies one.

> **Exactly one candidate → use it. Zero or more than one → omit the key.**

**Two agents on two stories in one milestone is the workflow this package exists for**, and it is
precisely when resolution has more than one answer. `ledger record`'s standing contract already
governs the outcome — *"a number not given is a key the row does not carry, never a zero"* — and
`grain` is no different. A row filed against the wrong story is uncorrectable; a row filed against
none is visible in a bucket that already exists and can be fixed later.

**Say so out loud.** When resolution is ambiguous, print which candidates it was torn between, on
stderr, before writing the row without the key. The couriers pass hook output through verbatim, so
this is visible when someone looks — and it is what makes "revisit if ambiguity turns out to be
common" (D2) a countable claim rather than a hope.

## Precedence, stated once

    --grain given            use it; refuse if it names nothing (story 01)
    --grain absent, 1 live   use the live story's id
    --grain absent, 0 live   omit the key
    --grain absent, N live   omit the key, and name the N candidates on stderr

`--grain` always wins. A caller who said what they meant is never overridden by a lookup.

## Files this story may touch

- `src/agentic_sdlc/repo/pm/cli.py` — the resolution helper and its use in `cmd_ledger_record`.
- `src/agentic_sdlc/repo/pm/model.py` — only if `holds` needs an owner-narrowed sibling. **Prefer
  filtering `holds`' result at the call site** over a new resolver; this milestone is deleting
  ~20 of those, and adding one back the same week needs an argument in the close.
- `tests/test_pm_ledger_record.py`.

## Files it must stay out of

`tools/hooks/**` — the couriers pass what they have and know nothing about resolution; that is the
whole point of them being couriers. `report.py`, `ledger.py`, `skills.py`.

## Acceptance criteria

1. One story `in_progress`, no `--grain`: the row carries that story's id. Proven in
   `tests/test_pm_ledger_record.py`.
2. Zero stories `in_progress`, no `--grain`: the row carries **no `grain` key** — asserted on
   `sorted(row)`, not with a membership check, so a row carrying `grain: ""` or `grain: null`
   fails the case.
3. **Two stories `in_progress`, no `--grain`: no `grain` key, and both candidate ids on stderr.**
   The most important case in this story; it is the one that would otherwise mis-file silently.
4. `--grain` supplied while two stories are live: the flag wins, no stderr complaint. The lookup
   must not run when it is not needed.
5. Resolution never changes an exit code. A row that could not be attributed is a successful write
   with a key absent, not a failure — the fail-open promise the couriers depend on lives here now.
6. `tests/test_fuzz_inputs.py` still passes unchanged.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | `test_pm_ledger_record.py::…one_story_in_progress_resolves_and_routes` | new |
| 2 | unit | `…no_story_in_progress_omits_the_key_entirely` — asserted on `sorted(row)`, so `grain: ""` fails | new |
| 3 | unit | `…two_stories_in_progress_omit_the_key_and_name_the_candidates` — both ids on stderr, and the fix named | new; the case this story exists for |
| 4 | unit | `…the_flag_wins_over_the_lookup_and_the_lookup_stays_quiet` — asserts the complaint is ABSENT, so the lookup did not run | new |
| 5 | unit | `…resolution_never_changes_an_exit_code`, both ambiguity shapes | new |
| 6 | integration | `make fuzz` unchanged | existing, unamended |

## Out of scope

A session→grain marker written at claim time — **rejected in D2** with its reasoning; do not
re-derive it here. If tree resolution proves ambiguous often enough to matter, criterion 3's
stderr line is the evidence that reopens the decision, and reopening it is a new grain, not a
widening of this one.

## Close

done: 2dd13e7 — `_grain_from_tree` reads the row's OWN snapshot; a resolved grain routes as well as
names. `_resolved_grain_file` holds the deliberate asymmetry: a grain the VERB guessed at never
refuses a row, while `--grain` still does.
finding: 4f4e3cd's M1 belongs here as much as to the other feature — a row this story leaves
unattributed can still NAME a grain through its snapshot, which is why `ledger show` had to learn
about the tree's ledger.
review M2: the open finding above was CONFIRMED, in scope, and is now fixed — a snapshot places a
row only when it names one candidate at its finest kind (D8). **And the reason I gave for raising
rather than fixing it was void**: I cited "0.2.0's D5" for *"a row naming several grains is added
to each whole"*. 0.2.0's D5 is about D8/D9/D10 reporting over every `in_progress` milestone. The
no-weighting phrase lives in `report.py`'s docstring and nowhere else; no decisions log in the tree
records it, and 0.1.0's was retired with its milestone. **A dangling citation reads as settled and
stops an argument that was never had** — it cost this finding a review cycle. The bare `(D5)` is
gone from all three sites in `report.py`, replaced by the rule itself.
review M1: `_resolved_grain_file` caught `Usage`, and `model.story_file` raises `AmbiguousStory`, a
plain `Exception` — so a tree with two files claiming one id turned this story's convenience into
exit 2 with NO ROW WRITTEN, which is AC5 inverted. Caught now, and the proving case gained its
third shape: one live candidate that will not resolve.
review M3: a STATED grain this milestone cannot place fell through to the snapshot, so a row naming
a story since renamed away was billed to whichever other story was live, with nothing disclosing
it. It now names nothing here and is counted on its own `stated_elsewhere` line — the opposite of
"named no grain", and the ordinary case since every report reads the tree's shared ledger.
review W4: a single candidate that would not resolve was the silent third case. It speaks now, the
way the ambiguous branch already did.
review S1/S2: `stories_in_progress` is `ledger.STORIES_IN_PROGRESS`, named once for its three
readers; the docstring says stories-only and why a live FEATURE is not promoted.
review S3: the Proof budget said `cases: 4-5` and ten functions landed across the two stories, plus
two amended self-test corpora and four more from this review. Over, and named rather than excused —
the previous feature reconciled its overrun and this one did not, which is the habit slipping one
feature later.
