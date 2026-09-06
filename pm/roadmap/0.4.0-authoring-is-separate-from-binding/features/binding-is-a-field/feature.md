---
id: 0.4.0/binding-is-a-field
milestone: "0.4.0"
name: A binding is a field, and pm move dies
status: planning
reviewed:
phase:
depends_on: ["0.4.0/identity-lives-in-frontmatter", "0.4.0/the-pools-are-the-tables"]
consumed_by: []
---

# A binding is a field, and pm move dies

`milestone:` on a feature and `feature:` on a story become the authoritative binding — and
**optional**. A grain written and not yet bound is a normal, expected state, not an error.

```
pm set ft-two-pin-toolkit-adoption milestone ms-game-polish
pm set st-two-pins-one-make feature ft-two-pin-toolkit-adoption
pm set ft-two-pin-toolkit-adoption milestone ""     # unbind
```

One verb for every level, including the one 0.3.0 already built: a milestone binds to a release by
declaring `version:`, and `pm order --append` schedules it. Same shape, four kinds.

## `pm move` deletes itself

Today it *"re-parents a story: renames its file under the target feature and rewrites
id/feature/milestone — whole, or not at all."* It is that complicated because position is
parentage, so moving a story changes its identity. And it has a defect that follows directly:
**it does not rewrite the refs pointing AT the moved story**, so every `depends_on` naming it goes
stale, silently, at the moment of the move.

Under a field binding, re-parenting touches one line and the id never changes, so there is nothing
to rewrite and nothing to break. `pm move` is `pm set`. The verb is deleted, named in the
CHANGELOG with its replacement.

## Renaming is the operation that still needs care

An id is stable under re-parenting but not under a deliberate RENAME, and a consumer migrating into
slug uniqueness will have to rename real collisions. So the one ref-rewriting path that must exist
is `pm rename <old-id> <new-id>`: it rewrites the grain and **every `depends_on`, `consumed_by`,
`reviewed:` and binding field that names it**, whole or not at all. This is precisely what `pm
move` gets wrong today, done once, in the one verb that needs it.

## Ship criterion

`milestone:` and `feature:` are optional authoritative bindings; `pm set <id> <rel> <target>` binds
and an empty target unbinds. A binding naming no grain is refused by name. `pm move` is gone and
named in the CHANGELOG. `pm rename` rewrites the grain and every inbound reference, whole or not at
all, and a rename with any unrewritable reference writes nothing and names it.

## Proof budget

  cases: 5
  tier: pyunit
  lands in: `test_pm_verbs.py`, and the ref-resolution module for the rename sweep
  what already covers this: `pm set` exists and is covered for scalar fields; binding extends it.
    `pm move`'s cases are deleted with the verb. Genuinely new and the reason for most of the
    budget: `pm rename`'s inbound sweep, which needs a case per ref kind and one for the
    all-or-nothing refusal.

## Out of scope

Reporting what is unbound — that is `the-unbound-census`. This feature makes binding a field and
gives it a verb.
