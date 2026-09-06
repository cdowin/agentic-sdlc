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

**Order is a decision, so it is declared** — in `pm/roadmap/releases.md`, which is grain-shaped
like everything else: frontmatter carries the sequence, the body carries the plan's goal.

```yaml
---
order:
  - "0.1.0"
  - "0.2.0"
  - "0.3.0"
---
```

**Why not sort the versions.** It needs a comparator, so the engine acquires opinions about
schemes — and it cannot sort `0.90.3.2`, which is not semver. Worse, it re-couples the two facts
`a-milestone-declares-its-version` just separated: if order comes from the number, every insertion
must either renumber the tail or invent a component, and `0.90.4.1` is what gets invented under
pressure. Order and version are different decisions.

**Why a grain and not TOML.** This file changes constantly — it is a living list, rewritten every
time something ships, is inserted or is re-sequenced. That is exactly the file you want the
CLI's byte-preserving frontmatter writer to touch: one line rewritten, every comment and every
other line untouched, and a diff that shows what MOVED. `tomllib` is read-only anyway, so a TOML
`order` would have meant hand-rolled append surgery; frontmatter needs none, and TOML stays where
it belongs — config, not content.

**One new primitive.** The frontmatter reader handles scalars (`cmd_set`: *"a frontmatter scalar
is one line"*). `order` is a list, in BLOCK style — one entry per line, because reordering is the
main edit and a block diff shows what moved where an inline `[a, b, c]` rewrites the whole line.
That is a list-aware sibling to `set_field`, and it is the only new machinery here.

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

**Two reads fall out.** `release` with no argument takes the current milestone from the order
rather than making the human retype a version the plan already knows — a version given explicitly
is honoured, and one that is not current is refused naming both, because shipping out of order is
what a belt should stop. And `pm next` prints the first unshipped entry with the milestone that
claims it.

## Ship criterion

`releases.md` carries `order` as block-style frontmatter and a goal body, read by the same reader
as every grain. A list-aware writer appends, inserts and removes one entry, preserving every other
byte. `pm order` appends, inserts, removes and prints, refusing only duplicates and empty input.
`release` with no argument resolves the current milestone from the order and refuses an
out-of-order version naming both. `pm next` prints the first unshipped entry and its milestone.
Nothing sorts, compares or parses a version string.

## Proof budget

  cases: 5
  tier: pyunit
  lands in: a new `test_pm_order.py` for the verb and the list writer; the release-belt module for
    the no-argument resolution
  what already covers this: the frontmatter reader and `set_field` are covered for scalars, so the
    list writer extends them — and its byte-preservation case is the one that matters, because
    this file is edited constantly. The belt's checks and refusal shape are covered, so the
    no-argument path extends those rather than arriving.

## What 0.4.0 does to this, so nobody over-invests

`0.4.0/the-order-is-one-mechanism` generalises `order` to every container, and two things here are
transitional by design:

- **`pm order --append` retires into `pm add <parent-id> <child-id>`** — it is that verb against
  the root, and once every level has an order it should not have its own spelling. Build it as the
  thin thing it is.
- **The list holds VERSIONS here and child IDS there.** In this milestone a milestone's id IS its
  version, so the two are the same string; `a-milestone-declares-its-version` separates them and
  the order follows the id. Nothing to migrate — the strings do not change, only what they mean.

**The list-aware frontmatter writer is NOT transitional.** It is the one new primitive, every level
uses it, and it is the piece worth building carefully.

## Out of scope

The rules that hold the plan and the tree to each other — a dangling entry, an unscheduled
milestone, history out of order. Those are `the-plan-and-the-tree-agree`.
