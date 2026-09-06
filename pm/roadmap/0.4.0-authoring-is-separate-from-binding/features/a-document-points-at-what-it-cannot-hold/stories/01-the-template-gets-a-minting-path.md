---
id: 0.4.0/a-document-points-at-what-it-cannot-hold/01-the-template-gets-a-minting-path
feature: 0.4.0/a-document-points-at-what-it-cannot-hold
milestone: "0.4.0"
name: The handoff template gets a minting path, and the header survives rewording
status: done
owner:
depends_on: []
---

# The handoff template gets a minting path, and the header survives rewording

`pm new handoff <milestone-id>` renders `templates/handoff.md` into the milestone, id and name
filled. It never clobbers an existing handoff, and **`pm new milestone` still does not create
one** — the absence is the signal story 02 gates on.

## What was actually wrong

Not a missed lookup. **No code path wrote that template.** `templates.scaffold()` renders a
template only for `file_slots` — for a milestone, `milestone.md` alone. Optional slots
(`handoff.md`, `decisions.md`) get the header of an EXISTING file repaired and are never created.
`decisions.md` had a minting verb (`pm decide`); `handoff.md` had none.

So `templates/handoff.md` shipped, `model.SLOT_TEMPLATE` registered it, `[grain_shape]` capped it,
and the only way to reach it was `pm templates --install`, which copies it out for a consumer to
edit. Built, registered, documented, gated — and unreachable.

## On demand, never automatic

The verb mints only when asked. Auto-minting on `pm new milestone` would put an unwritten template
in every milestone and destroy the signal `check pm` warns on, so the two halves are one design:
**absence stays meaningful because nothing creates it, and the warning's hint names the verb that
does.**

## The regression this story nearly shipped

Rewording `SLOT_HEADER['handoff.md']` broke `templates._header_wanted`, which accepted `got in
set(SLOT_HEADER.values())` — the CURRENT values. A doc written under the old wording would no
longer be recognised, so `_fill_header` would **prepend a second header above the first**, and
every consumer's existing handoff would go red on upgrade day.

Fixed by `model.RETIRED_SLOT_HEADERS` and one derived `KNOWN_SLOT_HEADERS` that the writer and the
gate both read. A retired wording is recognised, never written. **The gate caught this on its own
first run** — the finding was against this repo's own handoff.

## Acceptance criteria

1. `pm new handoff <id>` renders the template with `{id}`/`{name}` filled and the header first.
   Proven by `tests/test_pm_scaffold.py::…test_new_handoff_mints_the_template_and_never_clobbers`.
2. A second run is a no-op that reports it and leaves the author's bytes byte-identical — section
   3 is the one thing in the tree no command can regenerate. Same case.
3. `pm new milestone` mints no handoff. Proven by `…test_new_milestone_does_NOT_mint_a_handoff`,
   which exists to protect story 02's signal.
4. A doc opening with a RETIRED header passes and is never double-headed. Proven by
   `tests/test_grain_shape.py::test_a_doc_opening_with_a_RETIRED_header_still_passes`.
5. The writer and the gate read ONE known-header set. Proven by
   `test_the_writer_and_the_gate_read_ONE_known_header_set`.

## Close

done: 4 files — `cli.py` (`new handoff` + USAGE), `model.py` (reworded header,
`RETIRED_SLOT_HEADERS`, `KNOWN_SLOT_HEADERS`), `templates/handoff.md` (the orient pipeline and the
absolute-path prompt), `templates/__init__.py` (one header set).
finding: the reword would have STACKED a second header on every existing consumer doc. Caught by
the story-02 gate on its first run, against this repo's own handoff. `RETIRED_SLOT_HEADERS` is the
fix and the reason it exists.
