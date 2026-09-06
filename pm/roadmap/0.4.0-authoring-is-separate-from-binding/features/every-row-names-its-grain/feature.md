---
id: 0.4.0/every-row-names-its-grain
milestone: "0.4.0"
name: Every automatic row names the grain it came from
status: planning
reviewed:
phase:
depends_on: []
consumed_by: []
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

## Three ways to answer "which grain", and the argument for each

The hook cannot know; it is a courier by design and must stay one. So the answer is the verb's or
the tree's.

1. **The verb resolves it from the tree.** `pm ledger record` already resolves *which ledger* by
   asking which milestone is `in_progress`. The same question one level down — which story is
   `in_progress`, for this `owner`/`agent_type` — is the same shape of query against data that
   already exists. Cheapest, and it needs nothing new on disk. Fails when two stories are open at
   once, which is normal with parallel agents, and an ambiguous answer must be an ABSENT key
   rather than a guess.
2. **The claim writes a session→grain marker.** `pm story building <id>` learns the session id and
   records it, so the hook's `--session-id` joins to a grain at report time rather than at write
   time. Exact, survives concurrency, and costs a new piece of state — which this package is
   rightly hostile to.
3. **The dispatch carries it.** The agent is told its grain and passes `--grain`, and the hook
   reads it from the environment the way it already reads `GDK_LEDGER_*`. Exact and free for
   subagents, useless for the orchestrator session nobody dispatched.

**A defensible answer is probably 1 for the common case with 3 as the override**, and 2 only if 1
proves ambiguous in practice. Decide it here, in writing, against the concurrency case: two agents
on two stories in one milestone is the workflow this package exists for, and an attribution scheme
that silently mis-files under it is worse than one that honestly omits.

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
