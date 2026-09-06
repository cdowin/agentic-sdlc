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
pm milestone add ft-two-pin-adoption --position 1
pm feature   add st-two-pins-one-make --after st-something
pm milestone remove ft-two-pin-adoption
```

`add` binds AND sequences, because "put this in this milestone, here" is one intent; `pm set <id>
milestone <x>` remains the primitive for binding without caring where. `--position N`, `--before`
and `--after` all place it; no flag appends.

**What may be added to what is declared, not hard-coded:**

```toml
[pm.contains]
milestone = ["feature", "bug"]
feature   = ["story"]
```

So `pm milestone add ms-other` is refused by name — *a milestone contains feature, bug* — from the
mapping rather than from a check written per level. It is also the config stating the model, which
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
