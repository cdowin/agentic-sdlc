---
id: 0.2.0/the-belts-refuse-to-advance
milestone: "0.2.0"
name: Each belt's entry condition is a verb with an exit code
status: building
reviewed:
risk: low
size: s
phase: 3
depends_on: []
consumed_by: ["0.2.0/the-release-is-a-conveyor"]
labels: ["belts", "pm", "gates"]
---

# Each belt's entry condition is a verb with an exit code

**Split out of `the-release-is-a-conveyor` on 2026-09-05**, from
`design-the-three-belts.md` §2. Small, self-contained, and the conveyor's `review-landed` step
is a caller rather than a re-implementation.

## Why — the conditions are already derivable and nothing answers them

A belt refuses to start until the belt below it is finished. All three conditions are computable
today; what is missing is a verb that answers with an **exit code**, so a step machine can gate
on it and an operator cannot mis-read it.

| gate | question | already available from |
|---|---|---|
| story → feature | is every story at `reviewing`? | `pm status` |
| feature → milestone | is every feature `done`, each with a non-empty review record? | `check pm` D1 asserts the pointer resolves |
| milestone → tag | is every finding at a disposition other than `open`? | `verdict.parse` returns dispositions |

```
agentic-sdlc pm ready-for feature   <feature-id>
agentic-sdlc pm ready-for milestone <milestone-id>
agentic-sdlc pm ready-for tag       <milestone-id>
```

Exit `0` ready · `1` not ready · `2` usage or config.

## Exit 1 NAMES the blockers; it never counts them

> `"3 stories not at reviewing"` sends someone to `pm status` to find out which.
> `"s/foo is building, s/bar is ready"` is actionable.

**The whole point of a machine-checkable gate is that the machine already knows the answer.
Printing a tally throws it away.** This is the same rule the census lines already follow
everywhere else in this package.

## `ready-for tag` is the one that would have caught this package's own worst habit

0.24.0's release ran `make milestone` **before** the reviewer, twice, and both runs were void
the moment the review asked for fixes. The reviewer had filed M1, M2 and m1–m4 at
`disposition: open`. `ready-for tag` would have exited 1, naming all six.

It is also the cheapest of the three to build, because `verdict.parse` already returns what it
needs.

## Ship criterion

1. Three subcommands, exit `0`/`1`/`2` per the contract, each printing the **named** blockers.
2. A milestone with an open finding exits 1 from `ready-for tag` and names the finding ids — a
   test builds that tree as a fixture rather than asserting on this repo's live state.
3. A feature with no stories is `ready-for feature` **ready** — an empty set is vacuously
   satisfied, and refusing it would make the verb unusable on doc-only features. Stated in the
   docstring, because "it passed and I do not know why" is the shape of a false PASS.
4. `pm vocabulary` is unchanged: these are read verbs, not new states.
5. Refusal matrix per `SDLC.md` §5 — a nonexistent id, an id of the wrong grain kind, a
   traversal in the id.

## Risks

1. **Vacuous truth is a false PASS wearing a bow.** Criterion 3 makes the empty case a
   documented decision rather than an accident; a milestone with zero features must still be
   loud, since that one is far more likely to be a mis-typed id than a real state.
2. **`ready-for tag` reads review records**, which are prose files. A record whose verdict block
   does not parse is `UNVERIFIABLE`, never a pass — precision over reach, exactly as the gates
   already rule.
