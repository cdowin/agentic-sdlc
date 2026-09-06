---
id: 0.4.0/the-surface-says-telemetry/01-the-word-is-where-you-are-standing
feature: 0.4.0/the-surface-says-telemetry
milestone: "0.4.0"
name: The word telemetry is in every discovery surface
status: planning
owner:
depends_on: []
---

# The word telemetry is in every discovery surface
`grep -ri telemetry` over the package hits a discovery surface. Today it hits five design
documents, four tests and a pygments lexer, and **no surface at all** — so an agent searching the
user's own word finds the archaeology of the feature and never the verb that shipped from it.

Three edits, none of them a capability. If this story adds a verb or a flag it has misunderstood
itself.

## Acceptance criteria

1. `pm --help`'s `ledger show` and `ledger report` lines say what they ARE — telemetry, spend,
   cost, how long something took — and not only what they do.
2. `pm ledger show` and `pm ledger report` are in `pm-execution.md`'s § "Keeping the tree honest"
   five-item read-verb list. That file auto-loads on every tree edit and currently mentions the
   ledger twice, both times as a side effect of a different verb.
3. A shipped skill's **`description:`** carries the vocabulary — telemetry, spend, cost, how long.
   The body is not the test: a selector reads the description.
4. The class is stated ONCE in this package's `CLAUDE.md`, as hard rule 11's read-side sibling:
   *a capability nobody can find is a capability you do not have; the fix is a word, a column or a
   line in the file that already loads, never a new verb.*
5. **No new verb, no new flag, no new config key, no new capability.** The diff is help text,
   guidance text and one rule.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | `test_cli_surface.py` already pins help text | amend |
| 2, 3 | unit | `test_pm_guidance.py` already pins the shipped rule and skill text | amend |
| 4 | unit | the CLAUDE.md prose census, if one covers it; otherwise no case — a rule in a doc is not code | — |
| 5 | unit | `test_cli_surface.py`'s verb roster is unchanged | existing, unamended |

Deliberately cheap. A large proof budget on a documentation feature would be the wrong signal.

## Out of scope

Any new verb or flag. Making recording work — the other three telemetry features. Rewriting
`pm-operations` beyond what its description needs to say.
