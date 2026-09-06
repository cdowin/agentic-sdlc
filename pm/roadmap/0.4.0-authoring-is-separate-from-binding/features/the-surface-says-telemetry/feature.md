---
id: 0.4.0/the-surface-says-telemetry
milestone: "0.4.0"
name: The surface says telemetry, at the moment of need
status: planning
reviewed:
phase:
depends_on: []
consumed_by: []
---

# The surface says telemetry, at the moment of need

**The trace, and it is this milestone's own thesis happening to this milestone.**

`0.4.0/the-read-verbs-compose` opens with an agent that reported a missing capability, proposed a
new verb, and was told the capability already existed — `pm list | grep` composes; the payload
just omitted the field. The feature draws the rule: *a read verb that omits a field people filter
on does not just inconvenience them, it teaches them the tool cannot do it.*

Asked for "full telemetry — phasing, timings, token use, tool calls", the agent building this
milestone hand-wrote a markdown table. The package ships `pm ledger`: seven row kinds, automatic
per-session token and tool-call capture off the transcript via an already-installed hook, and
`pm ledger report`, whose columns are
`dispatches | in | out | cache_create | cache_read | tool_calls | duration_s | todo | in_progress
| done | total_s`, per grain.

Same shape, one layer up. **Not a missing column — a missing word.**

## The measurement

`grep -ril telemetry` over the repo returns 15 files. Not one is a discovery surface:

    pm/roadmap/0.2.0/**   the design conversation that BUILT the ledger  (5 files)
    tests/                                                                (4 files)
    docs/design/, docs/reviews/                                           (3 files)
    .venv/                a pygments lexer for perl                       (1 file)

The count in `pm --help`, `CLAUDE.md`, `.claude/rules/pm-execution.md`, and both shipped
SKILL.mds is **zero**. An agent searching the user's word finds only archaeology — the record of
the feature being designed — and never the verb that shipped from it.

Two more, each independently sufficient to cause the miss:

**`pm-execution.md` enumerates the read verbs and omits the ledger.** § "Keeping the tree honest"
is a five-item list: `pm status`, `pm list`, `pm validate`, `check pm`, `pm vocabulary`.
`pm ledger show` and `pm ledger report` are not in it. The word "ledger" appears twice in the
whole rule, both times as **a side effect of a different verb** — "`--force` writes anyway and the
ledger's `deviation` row names the checks that were false", and "the cost it last took, read from
your ledger". Read cover to cover, that file teaches you a ledger exists as a passive byproduct.
It never teaches you that you can write to it or read it. **This is the file that auto-loads on
every tree edit.**

**Neither skill covers it.** Two ship. `pm-operations`'s own description bounds its scope — "the
grain schemas, scaffolding a milestone/feature/story/bug, decomposing work into stories, and
reading `pm status` and `pm validate`". `release` is the other. A skill is selected by its
description, so a skill about the ledger that never says "telemetry", "spend", "cost" or "how long
did this take" does not get chosen when someone asks for any of those.

## What changes

Three edits, none of them a capability:

1. **The word, in `pm --help`.** The ledger verbs' help lines say what they do and not what they
   are. One clause naming telemetry/spend/cost as what this is, so the grep that misses today
   hits.
2. **The verbs, in `pm-execution.md`'s read list.** Two lines, in the five-item list that is
   already there, in the file that already auto-loads.
3. **The vocabulary, in a skill description.** Either extend `pm-operations` or ship a third
   skill. The test is not whether the words appear in the body — it is whether they appear in the
   `description:`, which is the only part a selector reads.

## The general shape, now three for three

`the-read-verbs-compose` already named two instances — a hand-rolled adoption checklist because
`adopt` was never found, an invented search verb because `pm list` withheld a field — and called
them one shape. This is the third, and `0.4.0/telemetry-arrives-with-the-bump` turns up a fourth:
every courier ships `--self-test` and `adopt` does not call it.

Four instances is not a coincidence, it is a **class**, and it deserves the same treatment
`the-read-verbs-compose` gives its rule: stated once in the package's CLAUDE.md so it decides the
next case instead of being rediscovered. The proposed statement:

> **A capability nobody can find is a capability you do not have.** When a request is met by
> hand-rolling something the package already does, the defect is the surface, not the requester.
> The fix is a word, a column or a line in the file that already loads — never a new verb.

## Ship criterion

`grep -ri telemetry` over the package hits `pm --help`, `pm-execution.md` and a skill description.
`pm ledger show` and `pm ledger report` are in `pm-execution.md`'s read-verb list. The class above
is stated once in CLAUDE.md. No new verb, no new flag, no new capability is added by this feature —
if one is, the feature has misunderstood itself.

## Proof budget

  cases: 2
  tier: pyunit
  lands in: `tests/test_cli_surface.py`, which already asserts help text, and
    `tests/test_pm_guidance.py`, which already asserts the shipped rule and skill text
  what already covers this: both files already pin the text they govern, so both cases extend an
    existing assertion rather than adding a module. New: the ledger verbs appear in the read-verb
    list of the shipped `pm-execution.md` (which is a template in the wheel, so a consumer gets it
    on bump), and the help text names the vocabulary. Deliberately cheap — this is a documentation
    feature and a large proof budget would be the wrong signal.

## Out of scope

Any new verb or flag. Making recording work — the other three telemetry features. Rewriting
`pm-operations` beyond what its description needs to say.
