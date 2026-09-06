---
id: 0.2.0/bugs/a-collapsed-milestone-has-no-verb
milestone: "0.2.0"
name:
status: open
caught_in: "0.2.0"
fix_milestone: 0.2.0
caused_by:
---

# `pm retire` assumes a milestone SHIPPED — a collapsed one has no verb

Found 2026-09-05 collapsing 0.3.0 into 0.2.0. `pm retire 0.3.0 --dry-run` offered:

```
[pm] [dry-run] would append to pm/roadmap/ROADMAP.md: | 0.3.0 | the engine has no opinion | … |
```

**`ROADMAP.md` is the permanent index of SHIPPED milestones**, one row per release in ship order.
0.3.0 shipped nothing: its features moved into 0.2.0 and the milestone stopped existing. A row
there would be a lie in the one file whose whole job is being the durable record.

`retire`'s two `noticed:` lines are correct and its refusal posture is right — it reports rather
than blocks, per rule 9. What is missing is that **it only knows one way for a milestone to end.**

## The three endings, and only one has a verb

| ending | index row? | verb |
|---|---|---|
| shipped | yes | `pm retire` |
| **collapsed** into another milestone | **no** — the work is alive under a new id | **none** |
| abandoned | no, or a row that says so | none |

The tree was removed with `git rm` instead, which is defensible — this repo's own doctrine is
*"git history is the archive"*, and `pm validate` already calls a ref into a departed milestone
UNVERIFIABLE rather than a failure. But it is a hand operation where a verb belongs, and the next
person to collapse a milestone will reach for `retire` and get a false row.

## What a fix looks like

Not a fourth verb: an argument. `pm retire <id> --into <id>` writes no index row and says where
the work went; `--abandoned <why>` writes a row that says so. Both keep the one place that decides
what `ROADMAP.md` holds.

Filed rather than fixed because it is a 30-line change to a verb nobody is currently blocked on,
in a milestone already carrying 36 open findings.
