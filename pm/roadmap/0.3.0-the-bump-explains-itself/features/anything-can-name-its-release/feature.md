---
id: 0.3.0/anything-can-name-its-release
milestone: "0.3.0"
name: Any grain names the release it ships in, and absence means unscheduled
status: planning
reviewed:
phase:
depends_on: ["0.3.0/a-release-is-a-grain"]
consumed_by: []
---

# Any grain names the release it ships in, and absence means unscheduled

A grain gets one new optional frontmatter field:

```yaml
release: "0.3.0"
```

**The direction is the whole design.** The release does NOT list what it contains. A first draft
of this work had `covers = ["0.2.0", "0.3.0"]` on the release row, and that is a hand-maintained
child list — the thing `pm-execution.md` already forbids one grain down: *"do not hand-maintain a
story list in a feature file — that is a second scoreboard and it will lie."* The tree's grammar
is child-names-parent everywhere: a story names its feature, a feature names its milestone. A
release is one more level and takes the same shape.

**What that buys.** `release:` is not a milestone field — it is a GRAIN field. A milestone targets
a release by default, and so can a feature that ships early, a story, or a bug that is a hotfix.
Multi-milestone releases and non-milestone work fall out with no extra concept, because the
pointer was never on the release.

**And reassignment is a one-line edit in the thing that moved.** Pulling a feature out of 0.3.0 is
an edit to that feature. Nothing central needs updating, which is the property a central list
cannot have.

**Absence is the parking lot.** A grain with no `release:` is unscheduled. That is the default and
the majority state, it requires no declaration, no directory and no special status word, and it is
the honest answer for work nobody has committed to a version. The tool reports unscheduled grains
as a named, counted line — never a failure, because a healthy tree has plenty and a gate that
reddens on planning is a gate people switch off.

**Inheritance is deliberately absent.** A story under a feature that targets 0.3.0 does not
inherit 0.3.0. The tree already answers parentage; a second, implicit answer to "which release is
this in" is how two sources of truth start. A grain is in a release when it says so.

## Ship criterion

`release:` is read on every grain kind, resolves to a release grain or is refused by name, and
`pm set <id> release <version>` writes it like any other field. A grain without one is
unscheduled, reported in a counted line and never a finding. Nothing infers a release from a
parent.

## Proof budget

  cases: 3-4
  tier: pyunit
  lands in: the frontmatter-field module and `test_pm_verbs.py`
  what already covers this: `depends_on` and `reviewed` are both refs read off frontmatter and
    validated, so the read path has cases to extend. New: the unscheduled census line, and a
    `release:` naming no release grain.

## Out of scope

Whether the tree AGREES with the plan — a done milestone with no shipped release, a shipped
release with unfinished work. Those are rules, and they are `the-plan-and-the-tree-agree`.
