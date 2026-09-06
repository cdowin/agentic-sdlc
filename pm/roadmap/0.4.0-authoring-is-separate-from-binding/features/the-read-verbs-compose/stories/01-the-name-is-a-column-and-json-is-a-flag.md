---
id: 0.4.0/the-read-verbs-compose/01-the-name-is-a-column-and-json-is-a-flag
feature: 0.4.0/the-read-verbs-compose
milestone: "0.4.0"
name: pm list emits the name, and the listing verbs speak JSON
status: building
owner: claude
depends_on: []
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

## Out of scope

Adding filter flags — the behaviour this story exists to make unnecessary.
