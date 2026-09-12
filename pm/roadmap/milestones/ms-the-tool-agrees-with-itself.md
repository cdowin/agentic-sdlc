---
id: "ms-the-tool-agrees-with-itself"
kind: milestone
name: the tool agrees with itself
status: planning
depends_on: ["ms-a-consumer-can-take-the-bump"]
branch: milestone/0.9.0-the-tool-agrees-with-itself
version: 0.9.0
changelog:
order:
  - "ft-the-gates-agree-and-a-dispatch-counts-once"
  - "ft-frontmatter-has-one-grammar-and-one-way-in"
  - "bg-the-hard-rule-numbers-are-an-api-nobody-states"
  - "bg-the-rename-verb-carries-a-second-frontmatter-grammar"
  - "bg-the-rename-write-path-never-invalidates-the-document-cache"
  - "bg-the-storage-layers-privates-are-reached-from-outside-it"
---

# 0.9.0 — the tool agrees with itself

**A lean bug and tech-debt release: no new verb, no new capability.** Chris, 2026-09-11: *"lean,
maybe 1-2 features of just bug and tech debt work."* Every grain here is a place where two parts of
the package give two answers to one question. Two gates disagree about the version file (#43). Two
ledger rows describe one dispatch (#39). Two grammars read one frontmatter block. And the package
treats the hard-rule numbers as an API without ever saying so (#15).

## Where this came from

The GitHub issues open on 2026-09-11. Five came from consumers at v0.7.0, and #15 was left open from
0.6.0. The bugs and the debt are here. The feature requests went to the pool:

    #43  R5 vs the semver gate under version_at = start   → st-the-version-file-is-claimed-when-a-milestone-starts
    #39  a hand record double-counts; a snapshot guesses  → st-a-hand-record-joins-its-courier-twin
                                                             st-a-snapshot-places-a-row-only-on-a-story
    #15  consequence 4: rule numbers are a public API     → bg-the-hard-rule-numbers-are-an-api-nobody-states
                                                             (the rest of #15 is pool ft-a-phase-declares-what-it-hands-an-agent)
    #40  preflight                                        → pool ft-the-session-says-what-it-can-do-before-the-first-dispatch
    #41  dispatch outcome, spend by role                  → pool ft-a-dispatch-row-carries-its-outcome
    #42  ship writing-plans / executing-plans             → pool ft-the-kit-ships-its-planning-skills

The tech debt is the frontmatter cluster that `ft-the-module-says-what-it-does` (0.7.0) filed and
did not fix. It is three bound bugs, which `ft-frontmatter-has-one-grammar-and-one-way-in` closes in
one serial lane.

**This displaced the ledger milestone.** `ms-the-ledger-is-a-stamp` was minted as 0.9.0 and is now
0.10.0. It keeps its five features, its parallel-mode experiment and its guards. #39's
"one dispatch is one row" half lands here, because it is a bug a consumer is paying for today. The
ledger milestone's `ft-a-concurrent-dispatch-attributes-itself` keeps the stamp-from-transcript half.

## Mode

**SERIAL**, one builder at a time on the milestone branch (SDLC.md §2). The two features touch
disjoint files (`pm/inventory.py` and the ledger/report path; `core/frontmatter.py` and `pm/rename.py`),
so they could run in parallel. But the guards that make parallel safe are
`ft-the-flow-is-boring-by-construction`, which ships in 0.10.0, and that experiment belongs there.

## Ship criterion

- A `version_at = "start"` consumer can run `release`, push the release commit and merge it without
  `--no-verify`. At every step between `building` and the next milestone's `building`, R5 and
  `ci-semver-gate.yml` name the same version.
- A dispatch recorded by hand after its courier filed a grainless row counts ONCE in `pm ledger
  report`, on the hand record's grain. The report says how many pairs it joined.
- A grainless row is placed on a grain only when its snapshot names exactly one story. A snapshot
  naming only features places nothing, and the row is counted on the `rows naming no grain` line.
- `core/frontmatter.py` is the only grammar for a frontmatter block, and `tests/test_boundaries.py`
  forbids reaching its privates with an empty offender list, not only re-binding them.
- `CLAUDE.md` says the hard-rule numbers are append-only.
- #43, #39 and #15 are closed on GitHub citing their hashes. #40, #41 and #42 each carry a comment
  naming the pool feature that holds them.

## Risks

- **#39 crosses two ledgers.** The courier row sits in `<roadmap>/ledger.jsonl` and the hand row in
  the milestone ledger, and every report reads both (0.4.0 D3). The join has to be by `agent_id`, a
  stamp both rows already carry. It must never match on timing or tool-call counts: the issue
  proposes that match, and rule 9 refuses it.
- **Story 3 amends a recorded decision** (0.4.0 D8, "the finest kind the snapshot names"). It needs
  a `pm decide` entry superseding that clause. Do not change it silently.
- **The frontmatter cache fix has a price nobody has measured.** Dropping the whole parse cache on
  every write may be slow for `pm rename` over about 700 documents. Measure before choosing, as the
  bug file says.
