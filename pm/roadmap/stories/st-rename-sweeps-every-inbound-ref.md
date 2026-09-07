---
id: st-rename-sweeps-every-inbound-ref
feature: ft-binding-is-a-field
milestone: "ms-0.4.0"
name: pm rename rewrites the grain and every ref naming it, whole or not at all
status: planning
owner:
depends_on: ["st-set-binds-and-unbinds-and-pm-move-dies"]
kind: story
---

# pm rename rewrites the grain and every ref naming it, whole or not at all
`pm rename <old-id> <new-id>` rewrites the grain and **every reference naming it** — `depends_on`,
`consumed_by`, `reviewed:` and every binding field — whole, or not at all.

An id is stable under re-parenting and not under a deliberate RENAME, and a consumer migrating into
slug uniqueness has to rename real collisions: NullBound has 254 stories with reused names. So the
one ref-rewriting path that must exist is this one, done once, in the verb that needs it — instead
of `pm move`'s version, which did the rename and skipped the sweep.

## Acceptance criteria

1. `pm rename <old> <new>` rewrites the grain's own `id:` and every inbound reference in the tree,
   in one pass, and reports every file it touched.
2. **A rename with any unrewritable reference writes NOTHING and names it.** Whole or not at all:
   a half-swept tree has refs pointing at an id that no longer exists and refs pointing at one
   that does, and no gate can tell which was intended.
3. `<new>` failing the id grammar is refused before anything is read. `<new>` already in use within
   the kind is refused, naming the grain that holds it — the migration never auto-resolves a
   collision (D4) and neither does this.
4. Idempotence: renaming to the id a grain already has is a no-op that says so, exit 0.
5. One case per REF KIND, because each is a different reader: `depends_on`, `consumed_by`,
   `reviewed:`, a binding field, and an `order` entry.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 5 | unit | a fixture holding one of each ref kind; assert every one moved | new — this is most of the budget, and the reason for it |
| 2 | unit | one unrewritable ref; assert `porcelain` is empty afterwards | new |
| 3 | unit | the shared id grammar, REUSED (one case), plus the duplicate refusal | the grammar's matrix exists |
| 4 | unit | run it twice | the idempotence bar every write verb carries |

## Out of scope

Running a migration — `0.4.0/the-migration-is-whole-or-nothing` calls this verb rather than
duplicating the sweep. Suggesting names: `--suggest` belongs to the migration and applies nothing.
