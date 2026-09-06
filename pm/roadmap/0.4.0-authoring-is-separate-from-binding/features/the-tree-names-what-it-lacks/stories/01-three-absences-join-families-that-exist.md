---
id: 0.4.0/the-tree-names-what-it-lacks/01-three-absences-join-families-that-exist
feature: 0.4.0/the-tree-names-what-it-lacks
milestone: "0.4.0"
name: owner, the Proof budget and an unrun gate are named where they are missing
status: planning
owner:
depends_on: ["0.4.0/every-row-names-its-grain/02-an-unnamed-grain-resolves-or-is-omitted"]
---

# owner, the Proof budget and an unrun gate are named where they are missing
Three things the tool can already see and does not say. Each is one line in a family that exists —
**no new rule id, no new verb, no new gate module.** If this story adds any of those it has misread
rule 11's "cheapest layer" clause.

## Acceptance criteria

1. **A story in an `in_progress` category with no `owner:` is a READY-family WARN**, beside "no
   `branch:`" and "no `phase:`". This is a live bug, not a tidy-up: D2's fallback resolves a
   session's grain by narrowing live stories on `owner:`, so a blank `owner:` makes two open
   stories permanently ambiguous and degrades the fallback to "omit the key" **exactly when it was
   supposed to work**. `execlist.py` and `cli.py` already READ the field; nothing asks whether it
   is there.
2. **A feature past `todo` with an empty `## Proof budget` gets the same line.**
   `model.empty_section` already answers "present but empty" and already runs for
   `## Ship criterion` and `## Acceptance criteria` — one constant, one call, in the loop that
   already does this. A WARN, not a refusal: a feature whose budget is genuinely "none, this is
   docs" should say so in the section rather than be blocked.
3. **A gate named in `[checks] all` with no `gate` row in this tree is named by `verify`.**
   Nothing has ever read the roster and the ledger together, so a roster entry that never runs
   looks exactly like one that passes — and an inert roster entry is a failure this project has
   already paid for, since each pinned package refuses a gate name it does not know. The story
   decides whether the line sits inside `--plan`'s output or beside it; say which in the close.
4. All three REPORT. None changes an exit code (rule 9).
5. Nothing here duplicates `0.4.0/the-unbound-census`, `0.4.0/the-config-is-the-model` or
   `0.4.0/the-order-is-one-mechanism`. Rule 11 is a shared standard, not a bucket, and a fourth
   item that one of those owns is a finding against this story.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2 | unit | `test_pm_gate.py::ReadyIsAStampWithACheck` is a roster of exactly this kind — the handoff warning already moved its count 5 → 6 | amend: one line each plus a fixture field |
| 3 | integration | `test_verify_main.py` — a roster naming a gate with no row | new: nothing has read `[checks]` and the ledger together |
| 4 | unit | the exit code over a tree failing all three | amend the roster case |

## Out of scope

Refusing on any of the three. Anything about what `owner:` should CONTAIN — a name is the project's
business, presence is the tool's.
