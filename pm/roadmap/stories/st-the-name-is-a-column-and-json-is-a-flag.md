---
id: st-the-name-is-a-column-and-json-is-a-flag
feature: ft-the-read-verbs-compose
milestone: "ms-0.4.0"
name: pm list emits the name, and the listing verbs speak JSON
status: done
owner: claude
depends_on: []
kind: story
---

# pm list emits the name, and the listing verbs speak JSON
`pm list | grep "cost row"` returns rows. Today it returns nothing, because the payload omits the
name — which is how an agent concluded composition was impossible and proposed `pm list --grep`.

## Acceptance criteria

1. `pm list` emits the **name** column. The existing columns keep their order and their positions,
   because consumers cut on them.
2. Every read verb's `--help` names its columns **in order**, and states the rule: read verbs emit
   lines, composition is the shell's job; if you cannot pipe it, the missing thing is a column.
3. `--json` on the listing verbs, matching `pm vocabulary --json`, which set the precedent. The
   JSON carries the same fields as the columns and no others — the one thing that can silently
   diverge.
4. The rule is in this package's `CLAUDE.md`, so the next filter request is answered by policy.
5. **No filter flag is added.** The existing ones (`--status`, `--owner`, `--milestone`,
   `--kind`, `--category`) all stay: removing them breaks consumers for a purity nobody asked for,
   and the rule governs the NEXT one.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2 | unit | `test_cli_surface.py` already asserts the listing verbs' columns and help | amend |
| 3 | unit | one case round-tripping `--json` to the same field set the columns carry, both kinds | new — it is the only thing that can diverge unseen |
| 5 | unit | the flag roster is unchanged | existing, unamended |

## Close

done: 05c8364 — `LIST_COLUMNS` names the columns once; `_emit_rows` zips them onto the same tuples
for both views, so rows and `--json` cannot diverge. The rule is in CLAUDE.md as rule 11's read
side.
finding: **the column broke a consumer, in this repo.** `agent-worktree.sh` read the milestone rows
with a trailing catch-all variable, so `branch` absorbed the new `name`. Fixed with one variable,
and the CHANGELOG names the idiom — a trailing column is not free, and that is worth more than the
column.
finding: `name` is free text, so a tab in it would forge a column. Substituted with a space in the
tab-separated form; `--json` keeps the byte.

## Out of scope

Adding filter flags — the behaviour this story exists to make unnecessary.
review M1: the criterion says EVERY read verb, and `pm next`, `pm roadmap` and bare `pm order`
did not name their columns. They do; the case that asserted exactly two occurrences reddened on its
own fix and now counts against the verbs that emit rows.
review M2: the shipped `pm-operations` roster still listed the four old columns and never mentioned
`--json`. Fixed. Everything below MAJOR is recorded in the review and CARRIED (0.3.0's severity
rule) — the three worth picking up are `dict(zip)` wanting `strict=True`, `--json`'s missing
refusal row, and `\r` / non-ASCII in a `name`.
