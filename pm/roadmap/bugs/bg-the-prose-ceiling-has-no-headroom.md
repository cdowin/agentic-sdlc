---
id: bg-the-prose-ceiling-has-no-headroom
kind: bug
milestone: 
name:
status: open
caused_by:
changelog:
---

# the prose ceiling has no headroom, so it gates growth rather than ratio

**Measured at the start of this milestone: `4393/13183 = 0.33325` against a ceiling of `1/3`. One
line of headroom.** Not a round number — one line.

## Symptom

`tests/test_prose_census.py` fails on nearly every feature in this milestone, and the failure has
nothing to do with the feature. Landed count, this session alone: **six separate rounds of trimming**
across four features, each one shaving comments off code that had just been written, none of it
improving the codebase.

The trims were real work with no value: condensing a three-line why into two, moving a rejected
alternative out of a docstring, deleting a `# Rule 4.` marker. Every one of them made the source
slightly worse to read, and the ratio moved by one or two lines each time.

## Root cause

**A fixed ratio with no headroom is a growth gate wearing a quality gate's clothes.** The rule's
intent — *a docstring says what, a comment says why*, and prose should not dominate — is right, and
the census is the correct measurement of it. But at exactly 0.3332 the derivative is what bites: any
new module that documents its own WHY lands above 1/3 on its own (a new gate rule with a retirement
path is documentation-heavy by nature), so it must be paid for by deleting somebody else's
reasoning.

The milestone brief already saw this and said the opposite of what the gate enforces:

> **No comment trimming to buy census margin.** The census sits at ~0.333 with a handful of spare
> lines, and a sweep that pays for itself by deleting reasoning has done the opposite of this
> milestone.

**So the brief forbids the only action the gate leaves available.** That is the defect: not the
ceiling's value, but that it has become unsatisfiable without doing the thing the project says not
to do.

## What is NOT the fix

**Raising the number because the work failed it.** That is turning a rule off to make today green,
and CLAUDE.md is explicit that a rule failing when pointed at this repo gets the finding fixed.

**Deleting reasoning.** Named above; it is what has already happened six times.

## Fix — candidates, none chosen here

  * **Grade the DELTA, not the total.** A change's own prose/code ratio is the thing an author
    controls; the repo-wide total is a fact about four milestones of accumulated history. A gate on
    the diff bites the right person at the right moment.
  * **Exclude the surfaces that are contractually prose.** A `USAGE` constant is already code
    (that is why help text moved out of docstrings, twice, this milestone). A module docstring that
    IS the gate's published contract — `checks/pm.py` declares every rule id in its — is read by
    `check <gate> --help` and is nearer to a data table than to a comment.
  * **Raise the ceiling WITH a recorded reason and a re-measured target**, if the honest conclusion
    is that ~0.35 is what a package whose whole thesis is *write down the why* actually costs. That
    is a `pm decide`, not an edit.

**This bug does not pick one.** Picking it inside the milestone that keeps failing it would be the
same shortcut from the other side.

## Verification

Whatever lands: a feature that adds a well-documented module must go green without any comment in
any OTHER file changing. That is the property, and it is assertable — land a scratch module at the
repo's own average ratio and the gate must pass.
