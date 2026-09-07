---
id: bg-retire-drops-the-summary-it-accepts
kind: bug
milestone: "ms-a-move-is-an-event"
name: `pm retire` accepts a summary and writes it nowhere
status: fixed
caught_in: "ms-a-move-is-an-event"
fix_milestone:
caused_by:
---

# `pm retire` accepts a summary and writes it nowhere

GitHub issue #5. `pm retire <id> "<summary...>"` takes the one piece of prose a human would want to
keep and drops it. In `_retire` the summary is joined into `ended`, interpolated into `kept`, and
`kept` is only ever printed — and on the branch actually taken (the id IS on the plan) it does not
even include it.

Only the **id** survives a retire. `version:`, `name:` and the summary go with the document.

## Why it blocks the outcome 0.4.0 was aiming at

A consumer adopting 0.4.0 wants to delete their hand-maintained `ROADMAP.md`, because its
upcoming-table half is exactly the second scoreboard `order:` replaces. But the other half — one row
per shipped milestone: version, name, one sentence — is **not derivable from the tree after a
retire**. On the tree that surfaced this, 27 shipped milestones had been retired; their versions and
names exist in exactly one place, the file 0.4.0 is trying to retire.

So the file survives carrying 10% of its content: still hand-maintained, now almost always stale.
That is the worst of both.

## Fix

The data already arrives at the verb. Somewhere durable for a retired milestone's
`{version, name, summary}` — the `order:` entry becoming a mapping, or a row in the tree's own
`ledger.jsonl`, which `retire` explicitly does not touch and which already carries rows naming no
grain. Either makes `pm roadmap` able to print a shipped release fully.

**The smaller fix, if the larger one does not land here: REFUSE `<summary...>` rather than accept and
discard it.** An argument the CLI takes and ignores is worse than one it does not have, because it
reads as recorded — rule 4's second sin, a write that looks legitimate and is not.

## Not asking for

A resurrect anchor. `git log` finds the deletion commit; version, name and summary are the three the
tree has no other copy of.
