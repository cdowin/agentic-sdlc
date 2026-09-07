Append with `agentic-sdlc pm decide <grain-id>` — never by hand; the command stamps the date and the next ordinal.

# ms-the-rule-reaches-the-work  — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-09-07 — a parent does not close over unresolved children

**A grain nested in a parent must reach `done` before that parent closes.** Every kind, every level,
unconditionally. When a milestone is done, everything under it is done, recorded and durable: what
the record says it did is what is written and committed, and there is no third state where a grain
sits under a shipped release and nobody owes anything for it.

The tool is OPINIONATED here, and that is deliberate against rule 9. Rule 9 governs what a move
MEANS and what should happen next — the project declares its states and the tool reads them. This is
not that. This is what CONTAINMENT means, and containment is the one thing the tool already owns:
`[pm.contains]` is the tool's mapping, not the project's, and a parent that closes over an open child
makes its own census a lie, which is rule 4.

**Rejected: a per-grain opt-out field.** `fix_milestone:` was exactly this — a second field saying
"nested here, but not this milestone's problem". It is the reason the release gate could not fail for
four releases: the opt-out defaulted to opted-out, silently, and nothing said so. A field that
exempts a child from its parent is a second scoreboard wearing a smaller word, and 0.4.0 retired V6
for the same shape. Any future version of this idea — a `blocking: false`, a `deferred:` — is the
same rejection.

**Rejected: a parking-lot milestone.** Considered as the home for work you want to keep but not
commit to. It adds a container whose only purpose is to not be a container, and every grain in it
would need the same "does this one really gate?" question the field forced. **The pool already is
the parking lot**: bugs live in their own directory, and a bug that declares no `milestone:` is
unattached by construction.

**So the opt-out is the binding, and it is an act with a verb.** `pm remove <milestone> <bug>` clears
`milestone:`; the bug returns to the pool, gates nothing, and is COUNTED there — `N bug(s) attached
to no milestone`, silent at zero (rule 11). Declining to fix something now is a diff somebody can
read, not a field somebody has to remember to check.

The cost is a backfill: seven bugs are unresolved under `ms-0.3.0` and `ms-0.4.0`, both shipped. That
is the evidence the gap was real, and it is recorded on
`bg-a-bug-is-a-grain-nested-in-a-parent`.
