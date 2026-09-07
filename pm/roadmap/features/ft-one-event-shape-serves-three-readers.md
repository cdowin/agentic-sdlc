---
id: ft-one-event-shape-serves-three-readers
kind: feature
milestone: "ms-a-move-is-an-event"
name: one event shape serves hooks, telemetry and learning
status: planning
reviewed:
depends_on: []
consumed_by: []
---

# one event shape serves hooks, telemetry and learning

Three audiences have been asking for three features. They are one stream with three readers, and the
stream already exists — `ledger.jsonl`, which routes a row to the milestone that owns the row's grain
(D1, 0.4.0) and already carries `status`, `decision`, `dispatch`, `session`, `gate` and `deviation`
rows. This feature adds the row kinds the belts emit and fixes their shape.

## Three taps, and no others

A belt is its checks, then one write. That sentence has exactly three moments worth a row:

    rung.enter      the entry condition was asked
    check.verdict   one check resolved
    rung.leave      the one write happened

    {rung, grain, ready: bool, blockers: [{check, why}]}
    {rung, grain, check, verdict: ok|error|unverifiable, detail, ran}
    {rung, grain, from, to, from_category, to_category, wrote,
     next_rung, next_checks, next_actions}

`ran` is the shipped command the check runs or the literal `reads the tree` — the same two values
`install-sdlc` already renders into the protocol tables. `next_actions` is the arrival breadcrumb's
own derived COMMAND, from the one `arrive.derive_next` — not every `next:` line the belt prints,
because a fact the row wants and the printed line lacks belongs in the line, not here. `deviation` keeps its existing shape and gains the check list; `lesson` is
`ft-a-lesson-is-a-row-bound-to-a-grain`.

**There is no `rung.exit_failed`.** A belt that writes nothing emits `check.verdict` rows with false
verdicts and no `rung.leave`. The absence IS the signal, and inventing a fourth kind to say "the
thing did not happen" is the tool narrating rather than recording.

## Every field is derived, and a test makes that unaddable

`from_category` / `to_category` come from `[pm.states.<kind>]`. `next_rung`, `next_checks` and the
check names come from `registry_for(operation)`. `grain`, `rung` and the ids come from frontmatter
and the invocation. Nothing else is admissible.

The line: `next_checks: ["stories-done", "findings-landed"]` is the engine reading its own registry
back. `suggested_action: "run a review"` is the engine deciding, and rule 9 forbids it. So a test
asserts every key in every emitted payload resolves to `[pm.states.*]`, to the registry, or to a
frontmatter field — a hardcoded next-step fails a test rather than a review, exactly as
`ft-every-move-breadcrumbs-the-next-step` guards its printed sentence.

## Ship criterion

The three taps emit on every belt (`close story`, `close feature`, `release`, `adopt`) with the
payloads above, as ledger rows, routed by the grain the way every other row is. `pm ledger show
<grain>` prints them in the same stream as the status and dispatch rows, because a reader who has to
join two logs has two logs.

A consumer that declares no sink gets exactly today's behaviour and today's exit codes. The prose
the breadcrumb prints does not change: rule 6 makes it contract, and this feature adds a carrier
rather than replacing one.

The emitted schema is RENDERED into `docs/sdlc-protocol.md` by `install-sdlc`, from the same registry
that renders the check tables. A hand-written event table beside a rendered check table is the second
scoreboard this package deletes everywhere else.

## Proof budget

  cases: 5
  tier: pyunit
  lands in: `tests/test_ledger.py` beside the row-kind cases
  what already covers this: the row-routing quartet (D1's `_stamp` rule) covers "a row lands on the
    milestone that owns its grain" — the three new kinds are rows on that harness. The derived-only
    assertion is source-shaped and joins `tests/test_boundaries.py` beside the breadcrumb's.

## Out of scope

The courier and the sink config — `ft-the-tool-emits-and-never-executes`. This feature says what a
row IS; that one says where it goes and who carries it.
