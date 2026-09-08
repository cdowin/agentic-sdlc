---
id: ft-a-surface-reaches-its-reader-or-it-is-decoration
kind: feature
milestone: "ms-the-rule-reaches-the-work"
name: a surface reaches its reader, or it is decoration
status: planning
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# a surface reaches its reader, or it is decoration

**The milestone's northstar, turned on the surfaces that carry it.** Four sweeps, each independently
landable, in the shape `ft-a-read-verb-is-a-declaration` and `ft-the-vocabulary-is-constants-not-literals`
already use. If only sweep 1 lands, the measurement below is closed and the milestone still profited.

## The measurement, and it is worse than the brief assumed

A probe agent was dispatched into this checkout and asked what was in its context **before it ran
anything**:

    CLAUDE.md                        169 lines   reached it: NO
    .claude/rules/pm-execution.md    224 lines   reached it: NO
                                     393 lines   reached it: ZERO

It got the user's GLOBAL `~/.claude/CLAUDE.md`, the auto-memory INDEX, the skill LISTING (names and
one-line descriptions, no bodies), and the tool schemas. Nothing this project wrote.

**And absence is not the defect — a partial signal is.** The probe, in its own words: *"It will not
know that it doesn't know — the memory index gives just enough vocabulary ('belt', 'rung', 'D1') to
make confident-sounding reconstruction feel available."* That is rule 4's shape wearing an
instruction's clothes. It declined to reconstruct only because it was told accuracy mattered more
than helpfulness; **nothing in the shipped surface says that.**

Published doctrine claims a subagent gets a snapshot of the always-loaded file and none of the rules.
**In this harness it gets neither.** Measure, do not inherit.

## Sweep 1 — a shipped agent names the verbs its role reaches for

15 definitions, 1,075 lines. Which name the verbs an agent in that role needs:

    agentic-sdlc pm            0 / 15        lesson record              1 / 15
    ready-for                  0 / 15        close story | close feature 2 / 15
    pm ledger                  0 / 15        agentic-sdlc check         3 / 15
    agentic-sdlc changelog     0 / 15        verify --                  6 / 15

A dispatched `developer` is never told `ready-for story` exists. The `changelog-writer`, whose whole
role is release prose, does not name the `changelog` verb that renders it. Rule 11's test: *could
someone hand-roll a thing this package already does, and would anything have stopped them?* Six agents
were dispatched this milestone and every brief hand-pasted the verbs, because the definitions carry none.

Each definition names **its role's own** verbs and what each answers — a pointer, never a restatement
of what the verb does (that is `ft-prose-that-restates-a-verb`'s rule, and five sentences drifted in a
day the last time this package restated). `ft-the-dispatch-carries-the-contract` is the CARRIER and
this is the PAYLOAD: the preamble renders the ladder and vocabulary from `devkit.toml` and cannot know
what a REVIEWER needs versus a TEST-WRITER.

## Sweep 2 — the always-loaded surface is tiered

    CLAUDE.md            169 lines   under the documented 200 target
    pm-execution.md      224 lines   LONGER than the file it supplements
    `rule N` citations   ~850        rule 4 alone: 229 (the brief estimated 600 / 194)
    CLAUDE.md churn      17 of the last 150 commits

**`CLAUDE.md` is not too long and it is not rotting** — the tell for a roster-heavy file is nearer
78-of-150. So length is not the work; **tiering and the pointer index are.** Run the four-question
placement test, first yes decides: derivable → cut; lives elsewhere → pointer; most sessions do not
need it → path- or task-triggered; **would an agent get it WRONG without it → keep.**

**Move before you cut**: write the destination, verify the fact landed, then trim the source. A
mechanical fact-inventory diff, not a read.

**The rule NUMBERS do not move.** ~850 citations; trimming happens INSIDE a rule.

**One thing to measure, not assume:** doctrine says path-scoped rules fire on `Read`/`Edit` and NOT on
a Bash `cat`/`sed`/`grep`. This session read almost everything with `sed -n` and the rule DID fire —
injected in full, 224 lines, after a Bash command touching the pm tree. Establish which is true here
before moving one more contract into that tier; its whole value turns on it.

## Sweep 3 — the hooks, and what a gate is owed

7 hooks, 1,326 lines. **A gate beats a sentence**: an instruction asks an agent to remember, a check
makes it impossible to forget. The audit asks, per repeated correction this milestone paid for:
is there a hook or a check that would have made it unnecessary?

Live candidates, each with evidence from today: `git add -A` on a shared worktree swept three agents'
in-flight work into commits that did not name it (the `committed` check says "commit by explicit
pathspec" and nothing enforced it); `make test` does not include `matrix`, so four agents reported
green against a gate the release belt actually runs.

## Sweep 4 — the README

401 lines, and the file a consumer meets first. Same question, different reader: what does an adopter
need, and what is derivable from `--help` and `pm config --seed`?

## Ship criterion

Every shipped agent definition names the verbs its role reaches for, and a test asserts each named
verb EXISTS — a definition citing a retired verb is this milestone's own defect.

`CLAUDE.md` has been through the four questions; anything cut has a destination written FIRST, proven
by a fact-inventory diff. Rule numbers untouched.

Whether a path-scoped rule fires on a Bash read is MEASURED in this harness and written down.

At least one repeated correction from this milestone is converted from prose into a gate.

## Proof budget

  cases: 4
  tier: pyunit
  lands in: `tests/test_install.py` (it already holds installed copies to their sources and sweeps
    them for retired names) and `tests/test_check_doc.py` (landed 0.6.0; a pointer index is worth
    what its links resolve to)
  what already covers this: `test_no_installable_names_a_retired_thing_except_as_a_migration_note` is
    ALREADY half of sweep 1 — it proves no definition names something RETIRED. That a definition
    names the verbs its role NEEDS has never been asked.

## Out of scope

A line-count gate on `CLAUDE.md`. The budget is a smell test; being over after removing all rot is a
legitimate outcome to state, not to satisfy. `check budget` and the prose census already own the two
numbers that earn their place.

Renumbering, merging or reordering the hard rules. ~850 citations.

Choosing a consumer's roles. The 15 definitions are a starting roster; a project edits them after
install, and rule 8 says this package knows nothing about which they keep.
