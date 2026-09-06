---
id: 0.4.0/the-order-is-one-mechanism
milestone: "0.4.0"
name: Membership is the child's field, sequence is the parent's list
status: planning
reviewed:
phase:
depends_on: ["0.4.0/binding-is-a-field"]
consumed_by: []
---

# Membership is the child's field, sequence is the parent's list

0.3.0 built `order` for one edge: `releases.md` sequences milestones while each milestone's
`version:` says which release it is. **That split is general, and the tool already has two ad-hoc
answers to the same question that it can retire.**

> **Membership is the child's field. Sequence is the parent's list.**

- root → milestones, sequenced by `releases.md`'s `order`
- milestone → features and bugs, sequenced by the milestone's `order`
- feature → stories, sequenced by the feature's `order`

**This is not a child list.** The list carries SEQUENCE ONLY; membership stays on the child. A
feature bound to a milestone but absent from its `order` is UNSEQUENCED, and an `order` entry for a
feature that is not bound is DANGLING — R1's symmetric pair, one level down, reported by the same
family.

## What it retires

**`<!-- pm:execution -->` and V6.** A feature's execution block is a hand-maintained roster of its
stories, and **V6's whole job is keeping that roster in agreement with the tree** — the identical
defect as V2 and the path, one level down. A list that holds sequence and nothing else has nothing
to drift: a name in it either resolves or is dangling, and that is a fact rather than a copy.

**`phase:`**, where a consumer used it to group features within a milestone. Sequence is now the
milestone's `order`, and grouping — if a project wants it — is a label.

## One verb shape at every level

```
pm add    ms-game-polish  ft-two-pin-adoption --position 1
pm add    ft-two-pin-adoption  st-two-pins-one-make --after st-something
pm remove ms-game-polish  ft-two-pin-adoption
```

**The parent is named, and its kind is not.** An id carries its kind as a prefix
(`identity-lives-in-frontmatter`), so `ms-`/`ft-` is derivable from both arguments and requiring
the caller to repeat it would be redundant. That also makes `add` ONE verb rather than one per
parent kind, which is the thesis of this feature applied to its own surface. `pm set <id> <key>
<value>` is already kind-less for the same reason; the older `pm <kind> <status> <id>` shape is
kind-FIRST only because the kind selects which `[pm.states.<kind>]` to check.

`add` binds AND sequences, because "put this in this milestone, here" is one intent; `pm set <id>
milestone <x>` remains the primitive for binding without caring where. `--position N`, `--before`
and `--after` all place it; no flag appends. `remove` is the symmetric pair — unbind and
unsequence together — and `pm set <id> milestone ""` unbinds alone.

**Both earn their place, and the reason is written here because this family usually rejects two
spellings of one fact.** They are not two spellings: `set` writes ONE field and `add` does
strictly more, so neither subsumes the other. Without `add`, the common intent costs two commands
and a consumer who forgets the second leaves a bound-but-unsequenced child every time. Without
`set`, binding without an opinion about position is unreachable.

The test that separates a legitimate compound from a duplicate name is: **does the compound do
something the primitive cannot, and does the primitive stay reachable?** Yes to both. What keeps
`add` honest is that it must remain exactly `set` plus a list insert — the day it grows behaviour
neither primitive has, it has stopped being a convenience and become a second mechanism, and that
is the thing to catch in review.

**`order` lists child IDS, at every level including the root.** 0.3.0 writes the root's order as
version strings because a milestone's id IS its version there; `a-milestone-declares-its-version`
separates them, and the order follows the id. Two reasons: it is then the same kind of list at
every level — child ids, nothing else — and renaming a version never touches the plan, which is
the same decoupling argument one more time. "What version ships next" becomes
`field_of(<first unshipped milestone>, 'version')`.

That makes `pm order --append` a second spelling of `pm add` against the root, so it retires in
favour of the uniform verb; the root is named by `releases.md`'s own `id:` like any other parent.
Reading the plan stays `pm roadmap`.

**What may be added to what is declared, not hard-coded:**

```toml
[pm.contains]
milestone = ["feature", "bug"]
feature   = ["story"]
```

So `pm add ms-game-polish ms-other` is refused by name — *a milestone contains feature, bug* —
from the mapping rather than from a check written per level, and both kinds in the refusal come
from the ids themselves. It is also the config stating the model, which
is the point of `the-config-is-the-model`: reading `[pm.contains]` tells you the shape of the tree
with no prose at all.

**`order` is optional per container.** A milestone's bugs are not sequenced work, and an
unsequenced child is simply unsequenced — a census line, never a finding.

**And it is the same list in the same place at every level**, once 0.3.0 makes `releases.md` a
grain: `order` is block-style frontmatter on the parent, written by the same list-aware writer,
diffed the same way. `releases.md` is only distinguishable as "the root's grain" — it holds the
order of milestones because the tree itself has no other record. Nothing about it is a special
format, and TOML never appears in the PM layer at all.

## Ship criterion

Every container sequences its children with `order` and nothing else; membership is only ever the
child's field. `[pm.contains]` declares which kinds may hold which, and `add` refuses by name off
that mapping. `--position` / `--before` / `--after` place; bare `add` appends. Unsequenced and
dangling are census lines in the unbound family. `<!-- pm:execution -->`, V6 and
`story_ordinal_prefix` are retired by name, each with its replacement in the CHANGELOG.

## Proof budget

  cases: 5
  tier: pyunit
  lands in: `test_pm_order.py` (0.3.0's, generalised) and `test_pm_gate.py` for the pair
  what already covers this: 0.3.0 builds `order` and its reader for one level; this is the same
    code over a declared mapping, so most cases parameterise rather than arrive. New: the
    `[pm.contains]` refusal, and the unsequenced/dangling pair at a second level.

## Out of scope

Any ordering the tool computes. `depends_on` remains a dependency statement, not a sequence — a
DAG gives partial order, and "what is next" wants a total one somebody decided.
