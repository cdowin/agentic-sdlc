---
id: 0.2.0/the-belts-refuse-to-advance/01-ready-for-feature-names-the-stories-that-block-it
feature: 0.2.0/the-belts-refuse-to-advance
milestone: "0.2.0"
name: ready-for feature names every story that is not at reviewing
status: reviewing
owner:
depends_on: []
---

# ready-for feature names every story that is not at reviewing

<!-- What is observable when this ships. A story is an observation, not a task. -->

`agentic-sdlc pm ready-for feature <feature-id>` exits 0 when every story under that feature
is at `reviewing`, and exits 1 naming the ones that are not, with the status each holds:

```
s/foo is building, s/bar is ready
```

Never `"3 stories not at reviewing"`. **The whole point of a machine-checkable gate is that
the machine already knows the answer; printing a tally throws it away** and sends a reader to
`pm status` to re-derive what was in hand.

## This story opens the verb, so it owns the argument grammar

The three subcommands share one argv grammar and one id resolver. Per SDLC.md §5 the refusal
matrix ships with the surface that introduces it, so **the whole matrix is here**, covering
all three subcommand names — stories 02 and 03 add predicates, not grammar, and neither ships
a second matrix.

Ids resolve through `pm/cli.py`'s existing `_grain_file`, the resolver every other verb uses,
*"so traversal, globs, absolute paths and empty segments refuse identically"* (its own
docstring). Reuse it; do not write a second resolver, which would be a second answer.

## Files this story may touch

- `src/agentic_sdlc/repo/pm/readyfor.py` — new: the three predicates' home, and this story
  writes the first.
- `src/agentic_sdlc/repo/pm/cli.py` — the `ready-for` route and its `USAGE` lines.
  **The only story in this feature that edits `cli.py`.**
- `tests/test_pm_ready_for.py` — new.
- `tests/fixtures/` — PM-tree fixtures. Rule 8: **build the tree as a fixture, never assert
  against this repo's live `pm/roadmap/`**, which changes under the test as the milestone
  proceeds.

## Files it must stay out of

`src/agentic_sdlc/repo/pm/model.py`, `verdict.py`, `report.py`, `ledger.py`,
`src/agentic_sdlc/repo/checks/pm.py`, `src/agentic_sdlc/cli.py`, `pm/roadmap/`.

**Stories 01, 02 and 03 all write `readyfor.py`. They are SERIAL** — 01, then 02, then 03 —
because the file is small enough that splitting it three ways would be a worse module than a
serialized dispatch. Per SDLC.md §2, overlapping work is serialized rather than parallelised.

## Acceptance criteria

1. A fixture feature whose stories are all at `reviewing` exits 0 and prints one line saying
   so, **with the count it checked** (`4 stories, all at reviewing`) — a bare "ready" over a
   set the verb failed to enumerate is a false PASS. Proven by `tests/test_pm_ready_for.py`.
2. A fixture feature with one `building` and one `ready` story exits 1 and names both ids
   with their statuses; the message contains no bare tally. Proven by asserting both ids
   appear and that the output does not match a count-only shape.
3. **A feature with NO stories is ready, and the docstring says why** — an empty set is
   vacuously satisfied, and refusing it would make the verb unusable on doc-only features
   (the feature's ship criterion 3). The output distinguishes it: `0 stories — vacuously
   ready`. Proven by a fixture case asserting exit 0 **and** that distinct wording, because
   *"it passed and I do not know why" is the shape of a false PASS*.
4. A story holding a status outside the vocabulary (the D4 drift `check pm` reports) is
   listed as a blocker with the word it actually holds — the verb reports what the file says
   and never repairs it. Proven by a fixture carrying `wombat`.
5. `pm vocabulary` output is byte-unchanged: these are read verbs, not new states (feature
   criterion 4). Proven by `tests/test_pm_verbs.py` and `tests/test_pm_guidance.py` passing
   unmodified.
6. Nothing is written. Proven by a case comparing the fixture tree's bytes before and after
   a run of each of the three subcommands.
7. `tests/test_fuzz_inputs.py` passes with the new verb routed.
8. Slice command for the loop: `python3 -m pytest tests/test_pm_ready_for.py -q`.

## Refusal matrix — `pm ready-for <kind> <id>` (SDLC.md §5)

Every row exits 2 (usage/config, never 1 — a typo is not a finding), names the offending
value, and writes nothing:

| input | why |
|---|---|
| `ready-for` with no kind | usage |
| `ready-for feature` with no id | must not adopt the building milestone as a default subject |
| `ready-for wombat <id>` | the kind is a closed set of three; an unknown one names the set |
| `ready-for feature <milestone-id>`, `ready-for milestone <feature-id>`, `ready-for tag <story-id>` | **a grain of the wrong kind** — the id resolves to a real file and the wrong question gets answered about it, which is the quietest way this verb could lie |
| `ready-for feature ''`, `'.'`, `'..'`, `'0.2.0/'`, `'/0.2.0/x'`, `'0.2.0//x'` | empty and dot segments, absolute, doubled separator |
| `ready-for feature '../../../etc/passwd'`, `'~/x'`, `'file:///x'` | traversal, home, scheme — hard rule 8 |
| `ready-for feature '0.2.0/*'`, `'0.2.0/**'`, `'0.2.0/?'` | globs — a gate that answers about a SET the caller thought was one grain |
| `ready-for feature '0.2.0\\x'` | backslash separator |
| `ready-for feature '<256+ chars>'` | over-long |
| `ready-for feature $'a\nb'`, an id with a tab or a NUL | line breakers and control characters |
| `ready-for feature 0.2.0/does-not-exist` | a resolvable-looking id naming nothing: exit 2 naming the path it looked for |
| `ready-for feature <id> --json` (or any flag) | this story ships no flags; an unknown one is exit 2, never silently ignored |
| two ids | exit 2 — which of two it should have been is not a thing this verb may pick |

**Adversarial cases against the docstring.** The verb will claim it never writes, that an
empty story set is deliberately ready, and that exit 1 always names blockers. Generate against
each: a run in a read-only checkout (no write attempt anywhere), a feature directory with a
`stories/` dir containing only non-`.md` files (is that empty, or a scan that found nothing?
— rule and prove it), and a fixture with 200 blocking stories (the output still NAMES them,
capped and explicitly truncated with a count of the remainder, never silently shortened).

## Out of scope

- `ready-for milestone` (story 02) and `ready-for tag` (story 03) — this story routes all
  three names and refuses the argv for all three, but only `feature`'s predicate answers.
  02 and 03 must not need a `cli.py` edit.
- `--json`. If a caller wants it, that is a separate decision; the step machine reads exit
  codes.
- Any change to `check pm`'s rules, to `pm status`, or to any status vocabulary.
- Wiring the verb into a gate or a hook.

## Close

done: 6e9388d f7465c2 — pm ready-for feature, naming every blocker rather than counting.
f7465c2 changed the predicate from `reviewing` to `done` on Chris's ruling — the stricter
question, which is the tell it was the right one.
