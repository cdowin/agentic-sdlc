---
id: bg-a-read-verb-names-three-of-its-thirteen-sections
kind: bug
milestone: ms-nothing-is-hand-rolled
name: pm ledger report prints 13 sections and --help names 3
status: fixed
caused_by:
changelog: `pm --help` names every block `pm ledger report` prints — twenty-three of them, with each block's columns in order — where it named three.
---

# a read verb names three of its thirteen sections

**This grain was filed WRONG and is rewritten rather than deleted.** Its first
version claimed `pm ledger report` does not surface `session` rows and that
`tokens_total: null` was a defect. Both are false, and the record of the error
stays because the error IS the finding: the author had read `--help`, read the
first six sections of the output, and concluded the rest did not exist.

## Symptom

`pm ledger report` prints **THIRTEEN** sections. Its `--help` names **three** —
`spend per grain`, `time per state`, `time per actor` — and declares those
three's columns in order, as rule 11 requires. It says nothing about the other
ten:

    gate cost                      runs, first_ms, last_ms, delta_ms, census
    session deltas                 per-row delta for a cumulative courier
    yield / rework / escapes       review arithmetic
    overhead                       tool calls before first write, per story
    decisions per grain            and `decision to next status row`
    bugs naming a cause            the caused_by census
    rows this section could not use

**The worked example is the author of this bug.** Asked "where are we on
telemetry, compared to the previous milestone, how are we improving" — the exact
question this verb exists for — they: read `--help`; ran the report piped to
`head -60`, which is what one does with a long report; saw six sections; and
then hand-rolled six Python censuses over the raw `.jsonl`. Two of them
reproduced, worse, what the report already computes:

  * A gate-cost trend, by hand — `gate cost` already gives `runs`, `first_ms`,
    `last_ms`, `delta_ms` and both censuses, with a `*` when the census moved.
  * A session aggregation, by hand, which then nearly reported 1.1 BILLION
    tokens by summing cumulative rows — while `session deltas` already
    differences them correctly.

Then they filed a bug saying the tool could not do either.

## Root cause

Rule 11's read side is explicit: *"every read verb names its columns in order in
`--help`."* This verb obeys it for the three sections it documents and has grown
ten more since, each one a real capability nobody advertised. The rule was
applied once and not maintained, which is the same shape as the rule it polices
— a surface that stopped reaching its reader.

**`--json` is not the mitigation.** Its top-level keys are the index the text
output lacks (`gates`, `yield`, `rework`, `escapes`, `overhead`, `totals`,
`unattributed`), so a reader who thinks to ask for JSON discovers the sections a
reader of the human surface cannot. The human surface is the one an operator is
standing in.

## What is NOT wrong, recorded because this grain claimed it was

  * **`session deltas` exists and is correct.** The courier fires on `Stop`,
    which fires every turn, so each row is the running total; the section
    differences consecutive rows per `session_id`. The tool already knew.
  * **`tokens_total: null` is correct.** `ledger.py:514` makes it a SEPARATE
    measurement from `usage`, on purpose: *"a caller who was told '1234 tokens'
    cannot say which way they split, and a reader must be able to tell the two
    apart rather than see a guess."* A row carrying a measured split has no
    hand-recorded total, and `total_rows: 0` correctly counts the rows that do.

## Fix

Name every section in `--help`, with its columns in order, as the three
documented ones already are. A section list is the cheapest layer — rule 11 says
a word, a column, a warning, a caller, never a new capability — and there is no
new capability to add here: all thirteen already work.

The test that bites: assert the set of section headers the report PRINTS equals
the set `--help` names. It fails today at 3 of 13, and it fails again the day
someone adds a fourteenth.

## Out of scope

A comparison across milestones, which is a real absence rather than an
undocumented presence — `bg-the-telemetry-verb-cannot-compare-two-milestones`.

Shortening the report. Thirteen sections of arithmetic nobody has to hand-roll
is the verb working.

## Fixed

`pm --help`'s `ledger report` entry now carries a ROSTER: every block the verb
prints, in print order, each with its columns in order. A `(heading)` carries a
census rather than a table, and those same words are its row in the comparison
— so it is one roster and not two.

The gate is the SET, not the roster. `tests/test_pm_ledger_report_sections.py`
parses the roster out of `pm --help` (never restates it — a roster written down
in a test goes stale exactly the way the one it guards did), scrapes the block
titles the verb actually PRINTS from four seeds, and compares the two sets BOTH
ways: a block that prints and is not named fails, and a block named that no
longer prints fails. A census case holds the count above 20 so neither
direction can pass over an empty scrape.

### What the brief got wrong: it undercounted again, by nine

The brief says thirteen sections and lists them. **The verb prints twenty-two
distinct block titles in the one-id form**, twenty-three with the comparison
this milestone added. The nine the brief missed, having named the other
thirteen correctly:

    story  feature  bug                 section 1's three per-kind tables
    rows naming no grain                the second home's bucket
    verdict                             the row per review pass
    findings by severity
    deferred to
    verdict distribution
    gate                                the cost table INSIDE `gate cost`

So the grain that was filed wrong, rewritten because *"the error IS the
finding"*, was still wrong: the author counted the sections they could see in
the output they had read and stopped. **Thirteen was never the denominator.**
Run against HEAD, the gate reads: *"`pm --help` names 2 of 22 blocks"* — 2, not
3, because the reader takes a block as named only when the roster names it in
the parseable shape, and HEAD's two `columns IN ORDER:` paragraphs named `time
per state` and `time per actor` that way and `spend per grain` only in prose.

`time per actor` needed a seed of its own. The existing fixtures have no
disposition rows, so that block only ever printed its `(0)` heading — a block
whose columns had never been printed at all, which is how a column roster goes
stale with no table changing.

### How this is proven

| claim | case |
|---|---|
| every block printed is named in `--help` | `tests/test_pm_ledger_report_sections.py::TestTheHelpNamesEveryBlockItPrints::test_every_block_printed_is_named_in_help` |
| `--help` names no block that stopped printing | `…::test_help_names_no_block_that_stopped_printing` |
| the block census is not zero, so neither direction passes over nothing | `…::test_the_census_of_blocks_is_not_zero` |
| every column named is a column printed | `…::test_every_column_named_is_a_column_printed` |

**Red at HEAD, watched**: the same two set comparisons over the three seeds
HEAD already has (the comparison seed removed, so what reddens is the roster
and nothing else) fail with *"`pm --help` names 2 of 22 blocks; unnamed:
['bug', 'bugs naming a cause', 'decision to next status row', 'decisions per
grain', 'deferred to', 'escapes', 'feature', 'findings by severity', 'gate',
'gate cost', 'overhead shape', 'rework', 'rows naming no grain', 'rows this
section could not use', 'session deltas', 'spend per grain', 'story', 'time per
actor', 'time per state', 'verdict', 'verdict distribution', 'yield per review
pass']"*. Green after.

Fixed in `8ffcbeb`.
