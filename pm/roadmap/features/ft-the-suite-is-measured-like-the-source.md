---
id: ft-the-suite-is-measured-like-the-source
kind: feature
milestone: "ms-nothing-is-hand-rolled"
name: the suite is measured like the source
status: planning
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# the suite is measured like the source

The prose half of the tech debt, and the reason it is a FEATURE and not an afternoon of trimming:
**a cut nobody gates comes back.**

## The measurement

|  | total | code | prose | blank |
|---|---|---|---|---|
| `src/` | 21,519 | 14,000 (65%) | 4,689 (22%) | 2,830 |
| `tests/` | 36,295 | **20,604 (57%)** | **10,830 (30%)** | 4,861 |

The honest ratio is **20,604 lines of test code to 14,000 of source code — 1.47:1**, which for a
tool whose cardinal sins are a lying gate and a corrupting write is the high side of normal and not
the problem.

**The problem is that 30% of `tests/` is English.** 19% docstring, 11% comment, against `src/`'s
22% for both combined. The essay style is deliberate in `src/`, where `test_prose_census.py` gates
it and the reader is an agent with no memory of last week. Nothing measures `tests/`. The style
leaked into the one place with no ceiling and grew there.

## Why a ceiling and not a cut

0.6.0 spent **eight rounds** on the src census — six during the build, two more as placement moves
at the close — and the milestone brief had to say *"no comment trimming to buy census margin"* out
loud because the gate kept demanding it. That fight produced `0.6.0/D7`, which fixed what the census
COUNTS rather than what it allows.

The lesson transfers: a number somebody hits is worthless; a number somebody has to ARGUE is the
whole mechanism. So `tests/` gets its own declared ceiling with its own written argument, set from
what the suite looks like after the rot comes out — not before, and not at src's ratio because the
economics differ.

**Where the prose should GO, rather than die.** 0.6.0 established three placements that are not
trimming, and they apply here unchanged: help text belongs in a `USAGE` constant (a string
assignment is code); a rejected alternative belongs in `pm decide`; and the story of a defect
belongs in the grain that fixed it, which is where a reader looking for it will be. A test docstring
should say what this case pins and why it can fail — not retell the incident.

## Ship criterion

`tests/` is measured by the same census as `src/`, with its own declared ceiling in `[tests]` and the
per-module argument for that number written beside it, in the shape 0.4.0/0.5.0/0.6.0's case-count
arguments already use.

The ceiling is set from the suite AFTER the rot is out, and the cut is reported per module rather
than as one number.

`0.6.0/D7`'s exclusion carries over correctly or is deliberately not carried — a test docstring is
not printed as `--help`, so the published-output argument does not apply and the difference is
stated rather than assumed.

Nothing in `src/` is trimmed to pay for this.

## Proof budget

  cases: 2
  tier: pyunit
  lands in: `tests/test_prose_census.py` — it is the census, it already holds `src/`, and a second
    root is a parametrize row rather than a module
  what already covers this: `test_comments_and_docstrings_are_under_a_third_of_the_code` IS this
    feature for one root; `test_a_new_module_at_this_repos_own_ratio_fits_under_the_ceiling` is the
    guard that stops the new ceiling becoming a growth gate, and it generalises to both roots.

## Out of scope

A line-count target. Being over after removing all rot is a legitimate outcome to STATE, not to
satisfy — the same ruling the 0.6.0 brief made about `CLAUDE.md`.

Deleting tests. The suite is 1.47:1 and that is defensible; this feature is about the English.
