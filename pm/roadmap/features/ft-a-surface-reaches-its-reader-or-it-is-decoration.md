---
id: ft-a-surface-reaches-its-reader-or-it-is-decoration
kind: feature
milestone: "ms-the-rule-reaches-the-work"
name: a surface reaches its reader, or it is decoration
status: done
reviewed: docs/reviews/2026-09-08-0.6.0-a-surface-reaches-its-reader.md
depends_on: []
consumed_by: []
changelog: Every shipped agent definition now names the verbs its role reaches for — the question each answers, never a restatement — and a test resolves all 71 citations against the live CLI, so a definition naming a verb this package does not route fails by file, line and verb; `pm cli.commands()` exposes the router's own table for it. `check hooks` stops calling the whole corpus armed: `core.hooksPath` arms the git hooks and a new REGISTERED line counts what a settings file registers for the `cc-*` half, saying in the same breath that registration is not in force.
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

## What landed, and what did not — 0.6.0

All four ship criteria are met. Sweep 4 is not, and is scoped in writing rather than left silent.

**Criterion 1 — every shipped definition names its role's verbs, and a test resolves each one.**
Landed. **Sweep 1's table says 15 and the tree ships 12** — 12 was already 12 when the work began,
so nothing was dropped; read every `n / 15` there as `n / 12` (review S11). The measurement that
opened this feature is closed: `ready-for` went 0/12 to named wherever
a role opens a rung, and `close story`/`close feature`, `pm ledger report` and `lesson record` each
reached the role that needs them. Twelve `role-verbs` blocks, no two the same — a block pasted into
all twelve would be the decoration this feature is named against — and each line is the QUESTION the
verb answers, never a restatement of it. All twelve grew, by +7 to +14 (review S7 corrected an
earlier claim that two shrank). **Two are the only ones with DELETIONS**, which is the fact worth
keeping: `pm-operator`'s roster was an unfindable prose run-on inside a checklist item and
`tech-writer`'s changelog verbs sat in its project-config block, which is the project's to edit and
these are not. Both are +9 net after the prose came out.

The test is the load-bearing half: it scans the whole file, not the block, and resolves 71 citations
against the CODE at seven roster positions. It needed one src change — `pm/cli.py`'s router table
hoisted to a public `commands()`, because a test re-deriving a roster is the second scoreboard this
milestone kept finding.

**Criterion 2 — `CLAUDE.md` through the four questions.** Landed, and the honest result is that
almost nothing moved. 100 facts inventoried mechanically; the split is CUT 5, POINTER 1,
TRIGGERED 0 and KEEP 94, of which one is FIX-IN-PLACE — a fact that stays and was WRONG. The
buckets sum to 100 with FIX-IN-PLACE inside KEEP, and saying so is review S10's correction. All 53
facts inside the hard rules are KEEP. Every
derivation claimed was RUN: `make help` prints the tier compositions and the `.gate-reports/`
verdict sentence near-verbatim, so those left; `agentic-sdlc --help` does NOT print the exit-code
triple, so rule 6 stayed. Rule numbers 1-11 untouched — no renumber, no merge, no reorder.

Four rosters left the file and one wrong answer did. **The line-count outcome is 0 for the pass and
+2 for the feature** (169 lines before, 171 at close; the four-questions commit is 6 insertions and
6 deletions, and the +2 is the path fix). Review S6 corrected an earlier claim of -1 here. The
number is not the point and never was: each cut removes a line a normal feature forces somebody to
edit, not a line of prose, and the file was already under its target before any of this.

**FIX-IN-PLACE is the finding worth naming.** L93-94 named `cli.py` inside the bullet whose subject
is `src/agentic_sdlc/repo/`, and `src/agentic_sdlc/repo/cli.py` does not exist. An agent resolving
the bare name against the stated directory lands on `src/agentic_sdlc/repo/pm/cli.py` — a real file,
a real router, holding no `KNOWN_GATES`. The wrong answer was available, plausible and silent, in
the section whose entire job is placement.

**POINTER is 1 and it did NOT land**, because "move before you cut" forbids it: the installer roster
would become `install-gates --help`, which covers five of six — `pm install-skills --help` exits 2
on an unknown flag, so the doc roster is the only place the sixth describes itself. Filed to the
pool as `bg-the-sixth-installer-cannot-describe-itself`, where the fix is a flag, not a doc edit.

**Criterion 3 — measured, and the answer is not what the brief assumed.** A controlled A/B in this
harness, repeated in three sessions by three agents: the same file, back-to-back calls, only the
tool differing, with the Bash call FIRST so it had the earlier chance at a one-shot load. Bash
`sed -n` on a file under `pm/roadmap/` injects nothing; `Read` on that same file, the very next
call, injects the rule in full. **A `paths:`-scoped rule fires on `Read` and not on a Bash `sed -n`.**

**The ruling that follows is D8: TRIGGERED is 0, and nothing moves into `.claude/rules/`.** The
reasoning, the third session's divergence and the rejected alternative are there rather than here,
because a rejected alternative belongs in a decision record.

**What was NOT controlled, and it is owed:** whether the guard hooks fire when the project root IS
the checkout — neither session ran that. `Edit`, `Grep` and `Glob` were untested. Every probe is n=1.

**Criterion 4 — one repeated correction, converted from prose into a gate.** Met by
`test_every_verb_an_agent_definition_names_resolves_against_the_cli`. The repeated correction is the
one sweep 1 measured: six agents dispatched during this milestone, and every brief hand-pasted the
role's verbs because no definition carried them. That was prose an orchestrator retyped six times.
It is now a gate with two assertions — a definition naming none of its role's verbs, and a
definition naming a verb this package does not route — and it FAILS, by file, line and verb, on
7 of 7 planted probes.

**And the REGISTERED line is NOT that gate, which review S1 is right about.** It contributes nothing
to `findings` and exits 0 in every case, including *"NONE of the 5 registered"* — a named line under
rule 11, not a gate, and claiming criterion 4 with it was this milestone's own sentence used against
itself. D6 gives the reason it must stay a count. **Its finding is still the sharp one**:
`check hooks` printed `PASS — armed` over seven entries while `core.hooksPath` armed two, and the
guard for *"commit by explicit pathspec"* was installed, self-tested and not running. Named where
somebody stands, not gated, and this says so rather than counting it twice.

**NOT landed — sweep 4, the README, whole.** It carries no ship criterion; the feature says the
sweeps are independently landable. The finding is real — its `## Verbs` table restates `--help` for
25 verbs, exactly the kind this milestone exists for — but acting on it is a rewrite of the file a
consumer meets first, proposed at the close of a 21-grain milestone by the session that had already
landed five changes. `ft-a-read-verb-is-a-declaration` warns against the grand unification in one
pass. Named rather than dropped; sweep 4 above is the brief for whoever takes it.

**The larger half of the northstar is still unfixed, and it is not this package's.** All four
surfaces this feature is about — the always-loaded file, the path-scoped rule, the guard hooks, the
ledger couriers — reach the work only if the session's project root is the checkout, and all four
failed to reach this one for that single reason. The package can NAME it (U4 does; REGISTERED now
does) and cannot fix it. The milestone that says an instruction which does not reach the work is not
an instruction measured exactly that, on itself, four times.
