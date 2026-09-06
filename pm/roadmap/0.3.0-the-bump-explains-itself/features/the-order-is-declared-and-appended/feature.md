---
id: 0.3.0/the-order-is-declared-and-appended
milestone: "0.3.0"
name: The order is declared, appended by a verb, and read by the belt
status: planning
reviewed:
phase:
depends_on: ["0.3.0/a-milestone-declares-its-version"]
consumed_by: []
---

# The order is declared, appended by a verb, and read by the belt

There is no order. `pm list --kind milestone` walks directories and prints them in STRING order,
which is wrong twice on this very tree: `0.1.0` sorts first while `0.2.0` has shipped, and
`0.90.10` would sort before `0.90.4` on a consumer at 0.90.5 today. There is no `next` verb.

**Order is a decision, so it is declared.** `pm/roadmap/releases.toml`, one key:

```toml
order = ["0.1.0", "0.2.0", "0.3.0"]
```

**Why not sort the versions.** It needs a comparator, so the engine acquires opinions about
schemes — and it cannot sort `0.90.3.2`, which is not semver. Worse, it re-couples the two facts
`a-milestone-declares-its-version` just separated: if order comes from the number, every insertion
must either renumber the tail or invent a component, and `0.90.4.1` is what gets invented under
pressure. Order and version are different decisions.

**Authoring and SCHEDULING are separate acts.** A milestone is created, and declares a version,
without joining the plan — so a draft is not accidentally on the roadmap. Scheduling is its own
verb:

```
pm order --append <version>              append to the plan
pm order --insert <version> --before <v> put it somewhere
pm order --remove <version>              unschedule it
pm order                                 print the plan
```

**`--append` does not interrogate the tree**, and that is deliberate: a version string is a fact
about the INPUT and it is valid whether or not a milestone claims it yet. The tool does what it is
asked and the GATE reports the contradiction — the package's own stated split. It refuses only
facts about the input: a duplicate entry is a no-op that says so, an empty string is exit 2.

**Two reads fall out.** `release` with no argument takes the current milestone from `order` rather
than making the human retype a version the plan already knows — a version given explicitly is
honoured, and one that is not current is refused naming both, because shipping out of order is
what a belt should stop. And `pm next` prints the first unshipped entry with the milestone that
claims it.

**Appending is bounded line surgery, not serialisation.** `tomllib` is stdlib and read-only, and
this package is stdlib-only; inserting one string before a TOML array's closing bracket is the
same class of write the CLI already does on a frontmatter line, and needs no writer.

## Ship criterion

`releases.toml` declares `order` and the engine reads it. `pm order` appends, inserts, removes and
prints, refusing only duplicates and empty input. `release` with no argument resolves the current
milestone from `order` and refuses an out-of-order version naming both. `pm next` prints the first
unshipped entry and its milestone. Nothing sorts, compares or parses a version string.

## Proof budget

  cases: 5
  tier: pyunit
  lands in: a new `test_pm_order.py` for the verb and the reader; the release-belt module for the
    no-argument resolution
  what already covers this: nothing — the order does not exist. The belt's checks and refusal
    shape are covered, so the no-argument path extends those rather than arriving.

## Out of scope

The rules that hold the plan and the tree to each other — a dangling entry, an unscheduled
milestone, history out of order. Those are `the-plan-and-the-tree-agree`.
