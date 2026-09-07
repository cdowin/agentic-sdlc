Append with `agentic-sdlc pm decide <grain-id>` — never by hand; the command stamps the date and the next ordinal.

# ft-the-unbound-census  — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-09-07 — pm list --unbound is a COLUMN, not a flag

**The story's criterion 3 asks for `pm list --unbound [--kind <k>]`. It ships as a
wider LISTING with the binding as a column, and hard rule 11 is why.**

Rule 11's read side is explicit: *"Existing filter flags stay — removing them breaks
consumers — and the rule governs the next one. If you cannot pipe something the missing
thing is a **column**, never a verb."* `--unbound` is the next one. It was written, and
`tests/test_cli_surface.py::test_no_filter_flag_was_added` caught it within the minute —
a guard doing precisely the job it was added for.

**What made the flag look necessary is the actual defect.** `pm list` knew two kinds,
`story` and `milestone`, so a FEATURE or a BUG could not be listed at all. There was
nothing to pipe, so a filter looked like the only way to ask. Widening the listing fixes
the cause:

    pm list --kind feature | awk -F'\t' '$3 == "-"'     # written, not yet scheduled

and that composes with every other question — by status, by name, by milestone — which a
`--unbound` flag never would. `check pm` still COUNTS what is unbound; this is the verb
that says which.

**Rejected:** shipping the flag as written. It would have been the second spelling of one
fact (the census line already reports the count), and the first filter flag added since
the rule was written — with the rule's own test failing on it.

**Rejected:** a `pm unbound` verb. Worse on the same axis: rule 11 says a missing filter
is a column, and a verb is further from a pipe than a flag is.
