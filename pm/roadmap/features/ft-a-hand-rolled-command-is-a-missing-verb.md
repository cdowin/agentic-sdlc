---
id: ft-a-hand-rolled-command-is-a-missing-verb
kind: feature
milestone: "ms-nothing-is-hand-rolled"
name: a hand-rolled command is a missing verb
status: planning
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# a hand-rolled command is a missing verb

**Rule 11's test, extended one word.** The rule asks: *could someone hand-roll a thing this package
already does, and would anything have stopped them?* This feature asks the harder version — could
someone hand-roll a thing this package SHOULD do, and did they?

The answer was measured on 0.6.0's own close. **The CLI is the service layer or it is not**, and
eight times in one afternoon it was not.

## The census, and the control that makes it evidence

Three things the operator needed WERE verbs, and were used without hesitation: `install-* --diff`,
`changelog <id>`, `verify --plan`. That is the control. The other eight were `python3 -` and `bash`:

| what | why it is the tool's question | today |
|---|---|---|
| prose/code census over `src/` | the ratio a gate already enforces | only `test_prose_census.py` knows it; ran by hand 6x |
| prose/code census over `tests/` | 36,295 lines, 10,830 of them English | nothing measures it |
| hard-rule citation count | a documented constraint argues from it | `bg-the-brief-undercounts-the-coupling-it-argues-from` |
| AST-guard vs behaviour split | 8,075 lines nobody has sorted | `ft-a-source-shaped-guard-is-named-as-one` |
| per-module test growth in a range | the `[tests] cases` argument needs it every close | git diff + regex |
| candidate agent transcripts | the ledger's own missing input | `ft-the-record-is-harvested-not-pushed` |
| which milestone declares a version | found a live bug in `semver-gate.yml` | simulated the workflow in bash |
| test-case count | three numbers, all called "the count" | pytest, static, and the ceiling disagree |

Four already have a home in another grain of this milestone. **This feature owns the remaining four
and the RULE**, not a scatter of verbs.

## The rule, which is the deliverable

A measurement a document quotes must be a measurement a command produces. The failure mode is not
inconvenience — it is `bg-the-brief-undercounts-the-coupling-it-argues-from`: a number computed once
by hand, quoted forward through three milestones, wrong by 2x in the flattering direction, in the
sentence that exists to stop somebody renumbering the hard rules.

## What this must NOT become

**A verb per afternoon.** Eight hand-rolled commands is evidence, not a mandate. A verb whose only
caller was one session is worse than the `python3 -` that produced it, because it ships, it is
documented, it is tested, and it is a public API (CLAUDE.md's opening line). Each candidate earns a
verb, a flag on an existing verb, or a written reason why not — and the written reason is a
legitimate, expected outcome for most of them.

**A metrics surface.** These are census questions the tree can answer about itself, in the shape
`check <gate>` already uses: a verdict line naming what was scanned. Not a dashboard, not a trend,
not a number with an opinion attached.

## Ship criterion

Each of the eight is a verb, a flag, or a written reason why not — stated per row, in this file.

The hard-rule citation count is one of the ones that became askable, and the number quoted in
`ms-the-rule-reaches-the-work` is corrected from its output.

Every new surface names its columns in order in `--help` (rule 11's read side) and composes with the
shell rather than growing a filter flag.

No verb added here has zero callers outside its own test.

## Proof budget

  cases: 3
  tier: pyunit
  lands in: `tests/test_cli_surface.py` — the routed/documented census and the column declarations
    already live there, and a new read verb is a row on both
  what already covers this: `test_every_routed_verb_is_documented` (rewritten in 0.6.0 to read the
    router by AST) catches an undocumented addition for free; `test_every_read_verb_names_its_columns`
    is the floor a new read verb raises.

## Out of scope

Anything the tool would RUN. A census reads git, markdown and Python as text (rule 2). The moment a
candidate needs to execute something, it is a make target declared in `[verify]`, not a verb.
