---
id: bg-the-prose-census-subtracts-a-docstrings-blank-lines-twice
kind: bug
milestone: "ms-nothing-is-hand-rolled"
name: a blank line inside a docstring is counted as prose AND as blank, so code is understated on both roots
status: closed
caused_by:
changelog: The prose census counts a partition over line numbers, so a blank line inside a docstring is no longer subtracted as both prose and blank. Code was understated and every ratio overstated on both roots; the ceilings are unchanged and the arguments quoting them are re-derived.
---

# the prose census subtracts a docstring's blank lines twice

Found by the agent setting `tests/`'s ceiling, which noticed that DELETING prose
RAISED the code count. It declined to fix it — changing what a census counts to
move its own number is the move `0.6.0/D7` was careful not to be — so it is a
bug, and it is bound here because both ceilings in the tree are quoted off it.

## Symptom

`tests/test_prose_census.py::prose_and_code` returns
`(prose, len(lines) - blank - prose)`. A blank line INSIDE a docstring is in
both terms — `prose` counts it because `ast.get_docstring().count('\n') + 1`
spans it, and `blank` counts it because the line is empty — so it is subtracted
twice and `code` is understated.

Minimal reproduction, a five-line module whose docstring holds one blank line
and whose only statement is `x = 1`:

    total=5  prose=4  blank=1  ->  code=0

`code` should be 1. Measured on the real suite: deleting 29 docstring lines from
`test_fuzz_inputs.py` moved its code count **339 -> 343**, upward.

## Why it matters more than the size of the error

**Every prose ratio this project has ever quoted is overstated**, on both roots,
because the denominator is too small. That includes the `src/` figure the 1/3
ceiling has been graded against since 0.2.0, the eight rounds of comment
trimming 0.6.0 paid to `test_comments_and_docstrings_are_under_a_third_of_the_code`
(`bg-the-prose-ceiling-has-no-headroom`), and `TESTS_CEILING = 0.55` as landed.

It is conservative in the safe direction — the gate has been STRICTER than it
claimed, so nothing shipped that the honest number would have caught. The defect
is the claim, not the guarding.

## Root cause

One expression, and it reads correctly: *total, minus the blanks, minus the
prose.* It is wrong only because the two subtrahends overlap, and they overlap
only for a blank line inside a docstring — the one case a reader does not
picture. A comment cannot contain a blank line; a docstring usually does.

## Fix

Count the three classes over a partition of the lines rather than as independent
sums — mark each line number once as prose, blank, or code. A docstring's own
blank lines are then prose, which is the right answer: they are part of the
paragraph, and `0.6.0/D7` already treats a printed docstring as output by the
line.

**Then re-derive every number quoted against it, in the same commit**: `src/`'s
ratio and its headroom, `TESTS_CEILING`'s measurement and the dated argument
block that cites it. A fix that moves the ratios and leaves the arguments quoting
the old ones is this milestone's own defect class.

## Out of scope

Changing either ceiling to take advantage of the correction. The numbers move
because the measurement was wrong; what each ceiling SHOULD be is the argument
each already carries, re-run.

## What landed

`prose_and_code` counts a PARTITION over line numbers instead of three
independent sums: a set of prose line numbers (comment tokens, plus each
docstring node's `lineno..end_lineno`), blanks are the empty lines NOT in that
set, and code is the remainder. The five-line probe now reports `code=1`.

Both ratios moved, in the safe direction, because code grew:

    src     0.3206 -> 0.3157   ceiling 0.3333
    tests   0.5265 -> 0.5106   ceiling 0.55

**And every number quoted against it was re-derived in the same commit**, which
is the half that makes this a fix rather than a new drift:

    the measurement             0.5267  ->  0.5106
    the derivation              0.5106 rounded up to the next twentieth is
                                STILL 0.55 — the ceiling does not move
    relative headroom           4.4%    ->  7.7%   (874 prose lines)
    src's own headroom          4.0%    ->  5.6%
    tests at 1/3 would be over  58%     ->  53%    (3,933 lines to delete)
    the like-for-like src       0.3415  ->  0.3362
    collected cases             1,588   ->  1,595

A line carrying code AND a trailing comment stays PROSE, as the old arithmetic
had it. That is a judgement about which half of a mixed line counts, not the
overlap this fixes, and moving it is a different argument with a different
number.

`make unit` 1225 passed, `make check` 5 PASS.
