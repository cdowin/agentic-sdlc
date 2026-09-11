---
id: ft-the-pm-surface-has-no-dead-ends
kind: feature
milestone: "ms-a-consumer-can-take-the-bump"
name: the pm surface has no dead ends
status: done
reviewed: docs/reviews/2026-09-11-0.8.0-the-pm-surface-has-no-dead-ends.md
depends_on: []
consumed_by: []
changelog:
order:
  - "st-every-verb-answers-its-own-help"
  - "st-pm-new-bug-takes-a-name"
  - "st-a-milestone-retired-before-the-ledger-can-still-be-recorded"
---

# the pm surface has no dead ends

Issues: #25 #24 #31.

Each of these is an obvious spelling that gets an operator nowhere, and rule 11's failure mode is the
operator concluding the tool cannot do the thing:

- `pm set --help`, `pm new --help` and `pm get --help` exit 2 and print the whole ~480-line usage.
  `pm add --help` answers "unknown flag". The router handles `--help` only as `argv[0]`
  (`pm/cli.py:3174`).
- `adopt --help` describes a grain write the belt never makes (`conveyor/driver.py:400-423`). Its run
  line then reads as though it would write if a milestone existed.
- `pm new bug <ms> <slug> --name '…'` exits 2. The bug is the only scaffold with no name, and three
  consumer docs carried that spelling as an instruction that could not run (`pm/cli.py:1949-1968`).
- `pm retire` refuses an id that is not in the tree, and `ledger record` has no retire form, so a
  milestone pruned before 0.5.0 can never get the row `pm roadmap` reads. One consumer keeps 27
  shipped milestones in a hand-maintained ARCHIVE.md because of this.

The work is all in `pm/cli.py` plus `conveyor/driver.py`'s help renderer. The stories touch the same
file, so they run serially.

## Ship criterion

`--help` on every `pm` verb prints that verb's block and exits 0. `adopt --help` describes a
checks-only belt. `pm new bug <ms> <slug> <name...>` writes `name:`. A milestone that is not in the
tree can be given a `retire` row that `pm roadmap` prints, and an id that IS in the tree is refused
that path.

**Accepted means closed on GitHub:** #25, #24 and #31 are each closed with a comment citing this
feature and its commit hash(es) (SDLC.md §2).

## Proof budget

  cases: 4–6
  tier: unit (router and cmd_* are functions), plus one temp tree for the retire row
  lands in: the existing pm CLI test module(s). Search before adding one (rule 10)
  what already covers this: the top-level `--help` exit-0 case. It can probably be parametrised over
    the router table rather than adding one case per verb.
