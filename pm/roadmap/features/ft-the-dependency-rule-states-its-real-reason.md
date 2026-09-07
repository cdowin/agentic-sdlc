---
id: ft-the-dependency-rule-states-its-real-reason
kind: feature
milestone: "ms-the-rule-reaches-the-work"
name: the dependency rule states its real reason
status: planning
reviewed:
depends_on: []
consumed_by: []
---

# the dependency rule states its real reason

Hard rule 1 says *"Stdlib only, forever… A consumer's hook must never break on a transitive
dependency."* **That reason is true for one half of the package and not the other, and the rule does
not say which.** Worth an audit, because a rule defended for the wrong reason gets relaxed for the
wrong reason later.

## Where the reason holds absolutely

`tools/hooks/cc-ledger-subagent.sh` parses its payload with **bare `python3 -c`** — the consumer's
system interpreter, whatever that is, with no managed environment anywhere near it. A dependency there
would break a hook on a machine nobody controls, silently, in the telemetry path. Rule 1 is not
negotiable for the courier corpus and should say so by name.

## Where the stated reason does not hold

The PACKAGE runs through `uvx --from … agentic-sdlc` or `uv run`. Both resolve declared dependencies
into an isolated environment. A declared dep cannot reach a consumer's interpreter from there — it
would cost cold-start time and a network fetch, which are real, but they are not "a consumer's hook
breaks".

So the rule is doing correct work while giving an argument that only covers part of it.

## What actually blocks the useful libraries — and it is hard rule 3, not rule 1

Measured: **165 lines of hand-rolled frontmatter I/O** in `model.py`, `set_list_field` alone being 70
of them — and that function produced this milestone's `depends_on` scalar-vs-list defect. It is the
obvious candidate for a YAML library.

It cannot take one. **Rule 3 requires a write to preserve *every other byte, line endings included*.**
PyYAML reserialises the whole document, which would rewrite files the verb was not asked to touch and
produce enormous diffs in a PM tree that lives in git. `ruamel.yaml` round-trips comments and
formatting, which is much closer — but it guarantees semantic round-tripping, not byte-exact
preservation, and rule 3 asks for byte-exact.

The same pattern repeats for the other candidates:

    a CLI framework      blocked by rule 6 — output line shapes are contract, consumers grep
                         them, and rule 11's read side needs columns bound to help by hand
    a validation library blocked by nothing, and unnecessary: `check pm` already IS the
                         validator, and a second one is the second scoreboard this
                         milestone is named against
    a rendering library  blocked by rule 6 for the same reason as the CLI framework

**So stdlib-only is not costing much here, and not because stdlib is virtuous — because two other
hard rules independently rule out the libraries that would help.** That is a better answer than the
rule currently gives, and it is the one that will hold when somebody asks again.

## What this feature does

**Restate rule 1's reason accurately**, naming the courier corpus as the surface the constraint
protects, and naming `uvx`/`uv run` as the reason the package half is a different question. Runtime
only — test-time dependencies are already unconstrained and `pytest` plus `pytest-xdist` are declared
today.

**Record the audit as a decision**, with the rejected candidates and why each is blocked, so the next
person to ask reads the answer instead of re-deriving it. The interesting half is that the binding
constraint is rule 3.

**Name the one live trade.** If byte-exact preservation were relaxed to *semantic* preservation, a
round-tripping YAML library would delete ~165 lines and a class of shape bugs with them. That is a
genuine trade and it is rule 3's to make, not rule 1's. This feature does NOT propose taking it — it
proposes writing it down so the choice is visible.

## Ship criterion

Hard rule 1's text names the courier corpus as the surface its reason protects, and distinguishes the
package's own runtime, without changing what the rule permits. **The rule number does not move** —
roughly 600 citations across source, tests and hooks depend on the ordinals.

A decision records the audit: the candidates, and for each, the rule that blocks it. `check shell`
gains, or the courier corpus asserts, that no hook's inline interpreter imports anything outside the
stdlib — the constraint that matters most is currently held by convention.

## Proof budget

  cases: 2
  tier: pyunit
  lands in: `tests/test_boundaries.py`, beside the emit module's import allowlist — the same
    shape, asked of the hook corpus rather than of a module
  what already covers this: `test_boundaries.py` already holds an import allowlist for `emit.py`,
    written this milestone. The hook version is a row on it.

## Out of scope

Taking a dependency. This feature audits the constraint and states it correctly; it adds nothing to
`pyproject.toml`. Anyone proposing one afterwards will at least be arguing against the right rule.
