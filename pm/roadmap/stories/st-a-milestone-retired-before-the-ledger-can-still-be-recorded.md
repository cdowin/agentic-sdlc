---
id: st-a-milestone-retired-before-the-ledger-can-still-be-recorded
kind: story
feature: ft-the-pm-surface-has-no-dead-ends
milestone: "ms-a-consumer-can-take-the-bump"
name: a milestone retired before 0.5.0 can still get its retire row
status: building
owner: agent
depends_on: []
changelog:
---

# a milestone retired before 0.5.0 can still get its retire row

Issue: #31 (the remainder of #5, which was fixed going forward in 0.5.0).

Since 0.5.0, `pm retire <id> [<summary...>]` files a `retire` row (version, name, summary), and
`pm roadmap` prints a retired release from it. A milestone pruned BEFORE 0.5.0 has no path.
`cmd_retire` refuses an id that is not in the tree (`pm/cli.py:1037-1041`), and `pm ledger record`'s
forms are transcript, dispatch and gate. One consumer holds 27 shipped milestones (0.1–0.27) in a
hand-maintained `ARCHIVE.md` and 0 `retire` rows. It was meant to delete the file the day #5 landed.

## Rule-4 care

The backfill writes facts the caller supplies and the tree cannot check. That is close to the second
cardinal sin, *a write that looks legitimate and is not*. So:

- it is accepted ONLY when the id resolves to no grain. An id in the tree takes the normal path and
  the backfill form is refused by name;
- the row says it was backfilled (a field, or its `source`), so a reader can tell a recorded
  retirement from a reconstructed one;
- `version` and `name` are required, because they are the two facts nothing else holds.

## Acceptance criteria

1. `pm retire <id> --version <v> --name <name> [<summary...>]` files one `retire` row marked as
   backfilled, for an id not in the tree.
2. The same form on an id IN the tree exits 2 and names the normal path.
3. The form without `--version` or `--name` exits 2.
4. `pm roadmap` prints the backfilled release as retired, with all three facts, once the id is in
   `releases.md` `order`. If it is not, the verb says so, the way `pm retire` already does.
5. Idempotent: the same backfill twice files one row.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 4, 5 | unit | temp tree with an ordered-but-absent id | amend the retire-row case from #5 |
| 2, 3 | unit | the refusals | amend |

## Semver

Minor: new flags on an existing verb.
