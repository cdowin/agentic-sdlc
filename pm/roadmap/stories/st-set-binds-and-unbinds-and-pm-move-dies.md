---
id: st-set-binds-and-unbinds-and-pm-move-dies
feature: ft-binding-is-a-field
milestone: "ms-0.4.0"
name: milestone: and feature: are optional authoritative bindings
status: building
owner: claude
depends_on: ["st-each-kind-has-a-configured-pool"]
kind: story
---

# milestone: and feature: are optional authoritative bindings
`pm set <id> milestone <mid>` binds a feature; `pm set <id> feature <fid>` binds a story; an empty
target unbinds. Re-parenting touches ONE line and the id never changes, so there is nothing to
rewrite — and `pm move`, which existed only because position was parentage, is deleted.

`pm move` also had a defect that follows directly from what it was: it renamed the file and
rewrote three fields and **did not rewrite the refs pointing AT the moved story**, so every
`depends_on` naming it went stale, silently, at the moment of the move. That problem does not
disappear — it moves to `pm rename`, story 02, which is the one verb that needs it.

## Acceptance criteria

1. `milestone:` on a feature and `feature:` on a story are the authoritative bindings and are
   **OPTIONAL**. A grain written and not yet bound is a normal state, reported as a census line
   (`0.4.0/the-unbound-census`), never an error.
2. `pm set <id> <rel> <target>` binds; `pm set <id> <rel> ""` unbinds. Idempotent — the same
   command twice is a no-op the second time.
3. A binding naming a grain **not in the tree** is refused by name, writing nothing. That is a fact
   about the input, and it is what separates *unbound* (a plan in progress) from *broken* (drift).
4. A binding whose target is the wrong KIND is refused off `[pm.contains]`, naming both kinds — and
   both come from the ids themselves, since an id carries its kind as a prefix.
5. **`pm move` is gone**, from `cli.py`, from `--help`, from `pm-operations`'s skill text, and from
   the README; the CHANGELOG names it with its replacement. Its cases are deleted with it, not
   retargeted — a case for a verb that does not exist is a claim about nothing.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2 | unit | `test_pm_verbs.py` covers `pm set` for scalar fields | amend — a binding is a field |
| 3, 4 | unit | two refusal rows, no write | new |
| 5 | unit | the verb roster in `test_cli_surface.py`, and `Move`'s class deleted | amend |

## Out of scope

Reporting what is unbound — `0.4.0/the-unbound-census`. Sequence — `0.4.0/the-order-is-one-mechanism`.
Renaming — story 02.

done: 1236872, d1a74eb — `pm set <id> milestone <mid>` / `<id> feature <fid>` bind; an empty target
unbinds. `pm move` is DELETED — from `cli.py`, `--help`, the skill text and the README — and its
cases went with it rather than being retargeted. A binding naming a grain not in the tree is a V7
finding; naming the wrong KIND is refused off `[pm.contains]`.
Unbound is NORMAL and never an error: it is a counted `UNBOUND` line (0.4.0/the-unbound-census).
