---
id: ft-every-row-names-its-grain
milestone: ms-0.4.0
name: Every automatic row names the grain it came from
status: done
reviewed: docs/reviews/2026-09-06-0.4.0-every-row-names-its-grain.md
phase:
depends_on: []
consumed_by: []
kind: feature
order:
  - "st-the-couriers-carry-the-grain"
  - "st-an-unnamed-grain-resolves-or-is-omitted"
---

# Every automatic row names the grain it came from

The automatic telemetry works and lands **unattributed**. `ledger.ROW_KEYS` carries `grain` as its
third key. Neither courier fills it:

    cc-ledger-session.sh    --from-transcript  --event  --session-id
    cc-ledger-subagent.sh   --from-transcript  --event  --session-id  --agent-id  --agent-type

So every hook-written row lands in the bucket `pm ledger report` prints last — **`rows naming no
grain`** — and the per-grain spend table, the one a human actually reads, shows `0` dispatches
against every feature and story in the milestone. The numbers are captured. Nothing says what they
were spent on.

That is the difference between "we have telemetry" and "an agent picking up a story records what
that story cost", which is the only version anybody wants.

## This is a binding, and this milestone is about bindings

Worth saying plainly, because it decides the shape. 0.4.0's northstar is *the path is where a file
lives; the frontmatter is what it is and what it belongs to* — membership is the child's field.
**A ledger row's membership in a grain is a binding of exactly that kind**, and today it is
neither a field nor derived: it is absent. The row knows its session, its agent and its model, and
not the work.

## How a row learns its grain — decided (D2)

**The dispatch carries `--grain`; when it does not, the verb resolves the grain from the tree;
when that is ambiguous, the key is omitted.** In that order, and the third clause outranks the
other two.

**1. The dispatch carries it.** The agent is told what it is working on in the prompt that starts
it, so the fact already exists at the moment of dispatch and passing it is copying, not deriving.
The couriers already ferry `GDK_LEDGER_*` values through `make` byte-exact — this is a fourth of
the same, not a new mechanism. The hook stays a courier and learns nothing.

**2. The verb resolves it from the tree.** For a session nobody dispatched — the orchestrator, in
which most of this milestone's work happens — there is no prompt to read. `pm ledger record`
already resolves *which ledger* by querying tree state; this is the same shape of query one level
down: which story is `in_progress`, for this owner. Free, and needs nothing new on disk.

**3. Ambiguous resolves to an omitted key.** Two agents on two stories in one milestone is the
workflow this package exists for, and it is exactly when resolution has more than one answer.
`ledger record`'s standing contract already governs this — *"a number not given is a key the row
does not carry, never a zero"* — and it applies to `grain:` too.

**A row filed against the wrong story is worse than a row filed against none**, because the first
is uncorrectable and the second is visible in a bucket that already exists and can be fixed later.

**Rejected: a session→grain marker written by the claim.** It is the only option that is exact for
an undispatched orchestrator under concurrency, and it still loses — new durable state whose only
job is relating two things that both already exist, plus a write in the claim path that can fail
after the status has already moved. Revisit if tree resolution proves ambiguous often enough to
matter; the ambiguous case is not silent, so it can be counted.

**Whatever wins: an unresolvable grain is an omitted key, never a zero and never a guess.** That
is `ledger record`'s standing contract — *"a number not given is a key the row does not carry,
never a zero"* — and it applies to this key too. A row filed against the wrong story is worse than
a row filed against none, because the first is uncorrectable and the second is visible in the
bucket that already exists.

## Ship criterion

A session or dispatch that worked on a claimed grain produces a row naming it, and `pm ledger
report` shows its spend on that grain's line rather than in `rows naming no grain`. An
unresolvable or ambiguous grain omits the key and stays in that bucket, which remains a real,
reported destination and not an error. The resolution rule is documented where an agent claiming a
story will read it.

## Proof budget

  cases: 4-5
  tier: pyunit
  lands in: `tests/test_pm_ledger_record.py` for the resolution, and
    `tests/test_pm_ledger_report_sections.py` for the report moving a row out of the no-grain bucket
  what already covers this: the no-grain bucket is already asserted, so the report half extends an
    existing case rather than adding one. New: one story in_progress resolves; TWO in_progress is
    an omitted key (the concurrency case, and the one most likely to be got wrong); an explicit
    `--grain` overrides resolution; a `--grain` naming no grain in the tree is refused, not
    silently dropped.

## Out of scope

Recording being on at all — `0.4.0/recording-is-on-or-the-gate-is-red`. Any new report column: the
grain column exists and is empty.
