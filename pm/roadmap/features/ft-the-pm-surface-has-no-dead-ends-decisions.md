Append with `agentic-sdlc pm decide <grain-id>` — never by hand; the command stamps the date and the next ordinal.

# ft-the-pm-surface-has-no-dead-ends the pm surface has no dead ends — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-09-11 — pm new bug keeps its no-name form and names the empty name

`st-pm-new-bug-takes-a-name` criterion 2 said to match `pm new feature` exactly. That meant refusing a
create with no name at exit 2. The builder stopped on a committed contract:
`tests/test_replay_migration.py:61-80` runs `pm new bug ms-0.1 a-bug` with no name and expects exit 0
on a fresh tree, then exit 1 on the replay ("a bug is ONE authored file").

**`<name...>` is optional on `new bug`.** Given, it is stamped. Omitted, `name:` stays empty and one
`next:` line on stderr names the write that fills it (`pm set <bug-id> name '<name>'`), silenced by
`[pm] breadcrumbs = false` like every other breadcrumb. A second `new bug` for an existing id stays
refused at exit 1, unchanged. So criterion 4 ("re-run is a no-op") is superseded by that refusal.

**Rejected: refuse the no-name form (match `new feature`).** It is the only form that existed before
0.8.0, so a consumer script calling it would start failing. By rule 7 that is a MAJOR bump, bought for
a consistency nobody reported missing. #24's own second fix, "name the missing `name:` at scaffold
time as a `next:` line", is rule 11 at the cheapest layer.

Orchestrator decision under Chris's standing "go with the recommendations" for 0.8.0.
