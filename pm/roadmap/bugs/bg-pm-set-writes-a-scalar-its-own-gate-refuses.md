---
id: bg-pm-set-writes-a-scalar-its-own-gate-refuses
kind: bug
milestone: "ms-the-rule-reaches-the-work"
name: `pm set` writes a scalar that `check pm` then refuses
status: closed
caused_by:
---

# `pm set` writes a scalar that `check pm` then refuses

    $ agentic-sdlc pm set ms-x depends_on ms-y
    [pm] ms-x: depends_on '[]' -> 'ms-y'          exit 0

    $ agentic-sdlc check pm
    DRIFT  depends_on: 'ms-y' is not an inline list — write depends_on: ["a", "b"]

**One verb writes what another refuses, and the writing one exits 0.** Found while scaffolding this
milestone: `pm set` accepted the value, reported success, and `check pm` failed the tree on the next
run. A hand edit to `["ms-y"]` fixes it, which means the fix is known and the verb simply does not
apply it.

This is rule 4's second sin — a write that looks legitimate and is not. The operator has no signal at
the moment of the write; the signal arrives later, from a different verb, phrased as tree drift rather
than as "the thing you just ran did this".

## Why it belongs in THIS milestone

It is the same defect class the milestone is named for, one layer down. `ft-prose-that-restates-a-verb-is-rendered-or-gone` says no shipped SENTENCE may contradict what a verb does. This is a verb contradicting a GATE — the machine-readable form of the same disagreement, and the one an operator cannot argue with.

It also sat undetected through 0.5.0: the milestone's own `depends_on` carried the scalar form for
hours and `pm validate` reported VALID throughout, because validate resolves the ref and the gate
grades the shape. Two readers, two answers, neither wrong on its own terms.

## Fix

`pm set` knows which fields are list-shaped — `check pm` already holds that knowledge to grade them,
and `pm add`/`pm remove` already write `order` correctly. Route the write through the same shape
rule, so a list field is written as a list. Then a scalar in the file is drift somebody hand-wrote
rather than drift the tool produced.

If a field's shape is genuinely ambiguous, refuse at exit 2 naming the shape — a refusal the operator
can act on beats a success they cannot.

## Fixed

`validate.REF_KEYS` went public — the one answer to "is this field list-shaped" — and `pm set`
routes its value through `validate.refs_in`/`render_refs`, the gate's own parser, so there is still
one copy of the knowledge. `caused_by` gets the scalar half; `order` is refused by name at exit 2,
pointing at `pm add`/`pm remove`, because it is a BLOCK list and the scalar was a form `pm add`
already refused.

Proven in `tests/test_pm_verbs.py::FieldMutation` —
`test_a_list_shaped_field_is_written_in_the_shape_the_gate_grades` drives `set` then asserts
`check pm` exits 0, re-plants the scalar by hand and asserts it exits 1 (the probe), and asserts
the second identical `set` leaves the file byte-identical;
`test_a_value_of_the_WRONG_shape_is_refused_naming_the_shape` covers the four refusals.
