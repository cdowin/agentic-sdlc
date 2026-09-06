---
id: 0.4.0/every-row-names-its-grain/02-an-unnamed-grain-resolves-or-is-omitted
feature: 0.4.0/every-row-names-its-grain
milestone: "0.4.0"
name: An unnamed grain resolves from the tree, or is omitted
status: planning
owner:
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

## Out of scope

A session→grain marker written at claim time — **rejected in D2** with its reasoning; do not
re-derive it here. If tree resolution proves ambiguous often enough to matter, criterion 3's
stderr line is the evidence that reopens the decision, and reopening it is a new grain, not a
widening of this one.

## Close

<!-- done: <hash> — what shipped -->
