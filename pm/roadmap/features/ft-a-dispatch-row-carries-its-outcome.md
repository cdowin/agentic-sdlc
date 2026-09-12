---
id: ft-a-dispatch-row-carries-its-outcome
kind: feature
milestone: ms-the-ledger-is-a-stamp
name: a dispatch row carries its outcome, and spend rolls up by role
status: done
reviewed: docs/reviews/2026-09-12-0.10.0-features.md
depends_on: ["ft-work-is-stamped-with-its-issue-and-agent"]
consumed_by: []
changelog: `pm ledger record --outcome landed|superseded|stopped:<reason>` stamps what became of a dispatch; each unit prints its outcome, `by agent` gives each agent's tokens and share, and a `superseded spend` line totals the tokens and names the grains of rows for grains the milestone no longer holds (#41).
---

# a dispatch row carries its outcome, and spend rolls up by role

Issue: #41. Scheduled for 0.10.0 (`ms-the-ledger-is-a-stamp`): it is ledger work, it depends on that
milestone's stamp feature, and it changes the report that milestone reshapes. Its data depends on #39,
whose double-count half ships in 0.9.0.

A consumer asked "where did this milestone's time go?" and had to hand-write a pass over the ledger
to answer it. About 13% of agent time was code that landed; the rest was superseded plans, a deleted
pilot, re-plans and stopped builders. `pm ledger report` could not say so, for three reasons:

1. **A dispatch row has no outcome.** A run that stopped and was re-dispatched looks the same as one
   that landed, so `rework` reads `no data`.
2. **Superseded spend disappears.** Spend on removed grains shows only as a count of arrival rows
   naming a grain the milestone does not hold, with no total and no ids.
3. **Role totals exist only as sub-rows per grain.** There is no milestone-level split into planning,
   building and reviewing, and no share column, including in the comparative form.

**Open question for 0.10.0's scout. Rule 9 bounds the issue's proposal.** An outcome someone STAMPS
(`ledger record --outcome landed|stopped:<reason>|superseded`, or a belt writing `landed` on the
dispatch it closed) is a stamp. "A later dispatch on the same grain with the same role marks the
earlier one stopped" is the tool deciding what a move means. The role→category map is a
`devkit.toml` declaration, so reading it is fine. And the milestone's own risk applies: *"simple"
may mean trimming as much as adding*. Two new blocks go into a report that already prints 23.

## Ship criterion

`pm ledger record --outcome landed|superseded|stopped:<reason>` (and `stamp stop --outcome`) writes
the outcome someone STAMPED, and nothing infers one (rule 9). A later dispatch on the same grain does
not mark an earlier one stopped. `pm ledger report <milestone>` prints each unit's `outcome`, a
`by agent` table with each agent's tokens and `share`, and one `superseded spend` line totalling the
tokens and naming the grains of rows for grains the milestone no longer holds. A hand record joined
to its courier twin keeps its outcome. (Written at review, 2026-09-12: 0.10.0 W4.)

## Proof budget

  cases:
  tier:
  lands in:
  what already covers this: the `rework` block, which has no data to read.
